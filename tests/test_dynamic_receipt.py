"""Offline fail-closed regression checks, no live API or GPU activity."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import unittest

from trustfolio_dynamic.receipt import InvalidReceipt, validate
from trustfolio_dynamic.render import make_cards

ROOT=Path(__file__).resolve().parents[1]

def sample():return json.loads((ROOT/'demo/sample_receipt.json').read_text())

class ReceiptTests(unittest.TestCase):
    def fails(self, change):
        data=sample();change(data)
        with self.assertRaises(InvalidReceipt):validate(data,demo=True)
    def test_good_fixture(self):self.assertEqual(len(validate(sample(),demo=True)),5)
    def test_no_demo_source_in_real_mode(self):
        with self.assertRaises(InvalidReceipt):validate(sample(),demo=False)
    def test_requires_five(self):self.fails(lambda d:d['products'].pop())
    def test_duplicate_id(self):self.fails(lambda d:d['products'][1].update(id=d['products'][0]['id']))
    def test_wrong_rank(self):self.fails(lambda d:d['products'][0].update(rank=2))
    def test_wrong_category(self):self.fails(lambda d:d['products'][0].update(category='smart-phones'))
    def test_over_budget(self):self.fails(lambda d:d['products'][0].update(price_inr=d['budget_inr']+1))
    def test_price_nan(self):self.fails(lambda d:d['products'][0].update(price_inr='NaN'))
    def test_price_bool(self):self.fails(lambda d:d['products'][0].update(price_inr=True))
    def test_missing_stock(self):self.fails(lambda d:d['products'][0].update(in_stock=False))
    def test_unverified_price(self):self.fails(lambda d:d['products'][0].update(live_price_status='not_available'))
    def test_catalog_price(self):self.fails(lambda d:d['products'][0].update(price_source='website_catalog'))
    def test_brand_fallback(self):
        self.fails(lambda d:(d.update(mode='brand_budget',brand='SAMPLE'),d['products'][2].update(brand='OTHER')))
    def test_empty_brand(self):self.fails(lambda d:d.update(mode='brand_budget'))
    def test_freshness(self):
        d=sample();d['source']='trustfolio_live_api'; now=datetime.now(timezone.utc)
        d['checked_at']=now.isoformat()
        for p in d['products']:p['live_checked_at']=now.isoformat()
        validate(d,now=now)
        d['products'][0]['live_checked_at']=(now-timedelta(hours=1)).isoformat()
        with self.assertRaises(InvalidReceipt):validate(d,now=now)
    def test_graphics_layers(self):
        self.assertEqual(set(make_cards(sample(),demo=True)),{'features','budget','top5','compare','cta'})

if __name__=='__main__':unittest.main()
