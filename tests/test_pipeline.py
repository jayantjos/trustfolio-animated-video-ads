import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError

from trustfolio_video.contract import Blocked, api_url, campaign, canonical, fetch, validate
from trustfolio_video.storyboard import build, choose_template, validate_registry
from trustfolio_video.publishing import publish

NOW = datetime(2026,10,18,14,50,tzinfo=timezone.utc)


def fixture(mode='budget'):
    """Synthetic unit-test fixture. Never used in production or pilot outputs."""
    spec = campaign('washing-machines',35000,mode,'Samsung' if mode=='brand_budget' else '')
    products = [dict(id=f'{i:024x}',rank=i,title=f'TEST ONLY fixture {i}',brand='Samsung',
                     price_inr=31000+i,platform='croma',product_category='washing-machines',
                     main_image='https://media.tatacroma.com/test-only.png',is_active=True,in_stock=True,
                     specifications={'Capacity':'7 kg'},price_source='website_live_price_api',
                     live_price_status='ok',live_checked_at=NOW.isoformat()) for i in range(1,6)]
    data = dict(category=spec['category'],budget=35000,livePriceRefreshCompleted=True,
                products=products,requestedBrand=spec['brand'],fallbackApplied=False,partialBrandFill=False)
    env = dict(request=spec,source_url=api_url(spec),observed_at=NOW.isoformat(),response={'success':True,'data':data})
    rehash(env)
    return env


def rehash(env):
    env['response_sha256'] = hashlib.sha256(canonical(env['response']).encode()).hexdigest()


class ContractTests(unittest.TestCase):
    def check_mutation(self, change):
        env=fixture();change(env['response']['data']);rehash(env)
        with self.assertRaises(Blocked): validate(env,now=NOW)

    def test_three_modes_preserve_authoritative_rank(self):
        for mode in ('budget','brand_budget','comparison'):
            env=fixture(mode); valid=validate(env,now=NOW)
            self.assertEqual([p['id'] for p in valid['products']], [p['id'] for p in env['response']['data']['products']])

    def test_over_budget_rejected_without_replacement(self):
        self.check_mutation(lambda d:d['products'][0].update(price_inr=35001))

    def test_missing_price_evidence_blocks_even_with_refresh_complete(self):
        self.check_mutation(lambda d:d['products'][0].update(price_source='website_catalog',live_price_status=None))

    def test_missing_timestamp(self):
        self.check_mutation(lambda d:d['products'][0].pop('live_checked_at'))

    def test_old_price_timestamp(self):
        self.check_mutation(lambda d:d['products'][0].update(live_checked_at=(NOW-timedelta(hours=1)).isoformat()))

    def test_future_price_timestamp(self):
        self.check_mutation(lambda d:d['products'][0].update(live_checked_at=(NOW+timedelta(hours=1)).isoformat()))

    def test_reordered_ranking(self):
        self.check_mutation(lambda d:d['products'].reverse())

    def test_missing_rank(self):
        self.check_mutation(lambda d:d['products'][0].pop('rank'))

    def test_duplicate_product(self):
        self.check_mutation(lambda d:d['products'][1].update(id=d['products'][0]['id']))

    def test_insufficient_products(self):
        self.check_mutation(lambda d:d['products'].pop())

    def test_out_of_stock(self):
        self.check_mutation(lambda d:d['products'][0].update(in_stock=False))

    def test_private_network_image_rejected(self):
        self.check_mutation(lambda d:d['products'][0].update(main_image='https://127.0.0.1/private'))

    def test_image_credentials_rejected(self):
        self.check_mutation(lambda d:d['products'][0].update(main_image='https://user:pass@media.tatacroma.com/a.png'))

    def test_wrong_category(self):
        self.check_mutation(lambda d:d.update(category='smart-phones'))

    def test_invalid_numeric_values(self):
        for value in (True,False,-1,0,'NaN','Infinity',None):
            with self.subTest(value=value):
                self.check_mutation(lambda d:d['products'][0].update(price_inr=value))

    def test_brand_fallback(self):
        for change in (lambda d:d.update(fallbackApplied=True),lambda d:d['products'][2].update(brand='Other')):
            env=fixture('brand_budget');change(env['response']['data']);rehash(env)
            with self.assertRaises(Blocked):validate(env,now=NOW)

    def test_snapshot_tamper(self):
        env=fixture();env['response']['data']['products'][0]['price_inr']=1
        with self.assertRaises(Blocked):validate(env,now=NOW)

    def test_stale_snapshot(self):
        with self.assertRaises(Blocked):validate(fixture(),now=NOW+timedelta(hours=1))

    def test_source_url_tamper(self):
        env=fixture();env['source_url']='https://example.com'
        with self.assertRaises(Blocked):validate(env,now=NOW)

    def test_campaign_input_rules(self):
        for args in [('x',True),('x',10.5),('../x',100),('x',100,'brand_budget'),('x',100,'budget','Samsung')]:
            with self.assertRaises(Blocked):campaign(*args)

    def test_retry_is_bounded(self):
        opener=Mock(side_effect=HTTPError('redacted',503,'unavailable',{},None));sleep=Mock()
        with self.assertRaises(Blocked):fetch(fixture()['request'],opener=opener,sleep=sleep)
        self.assertEqual(opener.call_count,3)
        self.assertEqual(sleep.call_count,2)

    def test_auth_failure_not_retried(self):
        opener=Mock(side_effect=HTTPError('redacted',401,'unauthorized',{},None))
        with self.assertRaises(Blocked):fetch(fixture()['request'],opener=opener,sleep=Mock())
        self.assertEqual(opener.call_count,1)


class StoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads(Path('config/worlds.json').read_text())

    def test_all_thirty_slots(self):
        self.assertEqual(validate_registry(self.registry),20)
        self.assertEqual(sum(not w['enabled'] for w in self.registry['categories']),10)

    def test_twenty_worlds_three_modes_three_durations(self):
        count=0
        for world in self.registry['categories']:
            if not world['enabled']:continue
            for mode in ('budget','brand_budget','comparison'):
                for duration in (15,20,30):
                    env=fixture(mode);env['request']['category']=world['slug'];env['source_url']=api_url(env['request'])
                    env['response']['data']['category']=world['slug']
                    for p in env['response']['data']['products']:p['product_category']=world['slug']
                    rehash(env);approved=validate(env,now=NOW)
                    story=build(approved,world,duration=duration)
                    scenes=story['scenes'];self.assertEqual(scenes[0]['start'],0)
                    self.assertEqual(scenes[-1]['end'],duration)
                    for a,b in zip(scenes,scenes[1:]):self.assertAlmostEqual(a['end'],b['start'])
                    self.assertEqual([s['rank'] for s in scenes if 'rank' in s],[5,4,3,2,1])
                    self.assertEqual(story['ranked_source_ids'],[f'{i:024x}' for i in range(1,6)])
                    self.assertFalse(story['publishing_enabled']);count+=1
        self.assertEqual(count,180)

    def test_no_immediate_template_repetition(self):
        world=next(w for w in self.registry['categories'] if w['enabled']);history=[]
        for _ in range(9):
            selected=choose_template(world,history)
            self.assertNotIn(selected,history[-2:]);history.append(selected)

    def test_disabled_category_cannot_render(self):
        world=self.registry['categories'][-1]
        with self.assertRaises(Blocked):build(validate(fixture(),now=NOW),world)

    def test_publishing_is_hard_disabled(self):
        with self.assertRaises(Blocked):publish(enabled=True)


if __name__=='__main__': unittest.main()
