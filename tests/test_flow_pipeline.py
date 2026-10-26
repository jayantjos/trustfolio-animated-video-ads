import unittest
import copy
import io
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import json
from unittest.mock import Mock

from trustfolio_flow.live import DataBlocked, campaign, normalize_live, check_receipt, fetch_live, sha
from trustfolio_flow.flow_prompts import prompt_for, write_prompts, DYNAMIC
from trustfolio_flow.clip_ops import probe, check_master, assemble

NOW=datetime.now(timezone.utc)


def input_fixture(brand=''):
    data={'category':'washing-machines','products':[
        {'id':f'{i:024x}','title':f'FIXTURE ONLY Washing Machine {i}',
         'brand':('ExampleBrand' if brand else f'FixtureBrand{i}'),
         'platform':'amazon','price_inr':25000+i,'rank':i,
         'specifications':{'Capacity':f'{6+i} kg','Programs':'5'},
         'main_image':f'https://m.media-amazon.com/images/test{i}.jpg',
         'is_active':True,'in_stock':True} for i in range(1,6)]}
    rows=[{'id':p['id'],'deleted':False,'live':{'status':'ok',
           'price_inr':p['price_inr'],'checked_at':NOW.isoformat()}} for p in data['products']]
    spec=campaign('washing-machines',35000,'brand_budget' if brand else 'budget',brand)
    return data,rows,spec


def receipt():
    d,r,s=input_fixture()
    return normalize_live(d,r,spec=s,now=NOW)


class ValidationTests(unittest.TestCase):
    def test_real_response_contract(self):
        doc=receipt();self.assertEqual(len(check_receipt(doc,now=NOW)['products']),5)
        self.assertEqual(doc['products'][0]['price_source'],'website_live_price_api')
    def test_croma_catalog_missing_live_is_blocked(self):
        d,r,s=input_fixture();r[1]['live']={'status':'not_available'}
        with self.assertRaises(DataBlocked):normalize_live(d,r,spec=s,now=NOW)
    def test_deleted_is_blocked(self):
        d,r,s=input_fixture();r[0]['deleted']=True
        with self.assertRaises(DataBlocked):normalize_live(d,r,spec=s,now=NOW)
    def test_over_budget_blocked(self):
        d,r,s=input_fixture();r[0]['live']['price_inr']=40000
        with self.assertRaises(DataBlocked):normalize_live(d,r,spec=s,now=NOW)
    def test_bad_rank_blocked(self):
        d,r,s=input_fixture();d['products'][0]['rank']=2
        with self.assertRaises(DataBlocked):normalize_live(d,r,spec=s,now=NOW)
    def test_mismatched_post_ids_blocked(self):
        d,r,s=input_fixture();r[0]['id']='abcdef123456abcdef123456'
        with self.assertRaises(DataBlocked):normalize_live(d,r,spec=s,now=NOW)
    def test_brand_fallback_blocked(self):
        d,r,s=input_fixture('ExampleBrand');d['fallbackApplied']=True
        with self.assertRaises(DataBlocked):normalize_live(d,r,spec=s,now=NOW)
    def test_wrong_brand_blocked(self):
        d,r,s=input_fixture('ExampleBrand');d['products'][1]['brand']='Another'
        with self.assertRaises(DataBlocked):normalize_live(d,r,spec=s,now=NOW)
    def test_snapshot_tamper_blocked(self):
        doc=receipt();doc['products'][0]['price_inr']='1'
        with self.assertRaises(DataBlocked):check_receipt(doc,now=NOW)
    def test_stale_product_blocked(self):
        doc=receipt();doc['checked_at']='2026-10-25T00:00:00+00:00'
        with self.assertRaises(DataBlocked):check_receipt(doc,now=NOW)
    def test_url_ssrf_blocked(self):
        d,r,s=input_fixture();d['products'][0]['main_image']='https://127.0.0.1/image.jpg'
        with self.assertRaises(DataBlocked):normalize_live(d,r,spec=s,now=NOW)
    def test_noninteger_budget(self):
        with self.assertRaises(DataBlocked):campaign('washing-machines',35000.5)
    def test_no_brand_in_budget_mode(self):
        with self.assertRaises(DataBlocked):campaign('washing-machines',35000,'budget','Brand')
    def test_no_unknown_modes(self):
        with self.assertRaises(DataBlocked):campaign('washing-machines',35000,'other')
    def test_api_get_post_correct_ids(self):
        d,r,s=input_fixture()
        requests=[]
        class Response:
            def __init__(self,obj):self.status=200;self.headers={'Content-Type':'application/json'};self.obj=obj
            def __enter__(self):return self
            def __exit__(self,*x):return False
            def read(self,n):return json.dumps(self.obj).encode('utf-8')
        def open_req(req,timeout=40):
            requests.append((req.full_url,req.get_method(),req.data))
            return Response({'success':True,'data':r if req.get_method()=='POST' else d})
        x=fetch_live('washing-machines',35000,opener=open_req,now=NOW)
        self.assertEqual(requests[0][1],'GET')
        self.assertEqual(requests[1][1],'POST')
        self.assertEqual(json.loads(requests[1][2])['ids'],[p['id'] for p in d['products']])
        self.assertEqual(len(x['products']),5)
    def test_only_one_post_no_retry(self):
        d,r,s=input_fixture();opened=[]
        def opener(req,timeout=40):
            opened.append(req.get_method());raise OSError('failure')
        with self.assertRaises(DataBlocked):fetch_live('washing-machines',35000,opener=opener,now=NOW)
        self.assertEqual(opened,['GET'])


class PromptTests(unittest.TestCase):
    def test_six_prompts_all_fact_grounded(self):
        doc=receipt()
        for scene in DYNAMIC:
            p=prompt_for(scene,doc)
            self.assertIn('EDIT THE ATTACHED',p)
            self.assertIn(doc['snapshot_sha256'],p)
            self.assertIn('premium',p.lower())
        self.assertIn('product_01.png',prompt_for(8,doc))
        self.assertIn('product_05.png',prompt_for(8,doc))
        self.assertIn('TrustFolio.in',prompt_for(10,doc))
        self.assertNotIn('FIXTURE ONLY',prompt_for(10,doc))
    def test_real_receipt_required(self):
        doc=receipt();doc['source']='synthetic_test_only'
        with self.assertRaises(DataBlocked):write_prompts(doc,tempfile.mkdtemp())
    def test_prompts_and_handoff_files(self):
        doc=receipt()
        with tempfile.TemporaryDirectory() as d:
            manifest=write_prompts(doc,d,allow_demo=True)  # Synthetic records still have test timestamps
            self.assertEqual(len(list((Path(d)/'prompts').glob('*.txt'))),6)
            self.assertEqual(manifest['verified_receipt_sha256'],doc['snapshot_sha256'])
    def test_replacement_requires_actual_approved_clips(self):
        import os
        master=Path(os.environ.get('TRUSTFOLIO_TEST_MASTER', '/nonexistent_trustfolio_40s_master.mp4'))
        if not master.is_file():self.skipTest('local-only integration master')
        self.assertEqual(check_master(master)['width'],360)
        with tempfile.TemporaryDirectory() as d:
            bundle=Path(d)
            (bundle/'data').mkdir()
            doc=receipt()
            # This synthetic snapshot is only for checking that missing approvals fail.
            doc['checked_at']=NOW.isoformat()
            (bundle/'data'/'verified_receipt.json').write_text(json.dumps(doc))
            (bundle/'data'/'flow_handoff_manifest.json').write_text(json.dumps({'verified_receipt_sha256':doc['snapshot_sha256']}))
            approvals=bundle/'approvals.json';approvals.write_text('{"scenes":{}}')
            with self.assertRaises(DataBlocked):assemble(master,bundle,bundle,approvals,bundle/'final.mp4')

if __name__=='__main__':unittest.main()
