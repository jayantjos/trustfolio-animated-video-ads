"""Website GET Top5 + POST exact IDs parity tests with synthetic fixtures (not ad data)."""
from datetime import datetime,timezone
import io
import json
import unittest

from trustfolio_video.contract import Blocked
from trustfolio_video.website_parity30 import build_verified_two_api
from trustfolio_video.washing30 import build30,verify_reference_images

class Response:
    status=200
    headers={"Content-Type":"application/json"}
    def __init__(self,body):self.body=json.dumps(body).encode()
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n):return self.body[:n]

def source():
    ps=[]
    for rank in range(1,6):
        ps.append({"rank":rank,"id":f"{rank:024x}","product_category":"washing-machines",
                   "title":f"Fixture Washer {rank}","brand":f"Brand{rank}",
                   "platform":"Fixture Shop","is_active":True,"in_stock":True,
                   "main_image":"https://m.media-amazon.com/images/I/test.jpg",
                   "price_inr":35000-rank*1000,"specifications":{"capacity":f"{rank+5} kg"}})
    return {"response":{"success":True,"data":{"category":"washing-machines","budget":40000,"products":ps}},
            "response_sha256":"a"*64}

def price_rows():
    rows=[]
    for rank in range(1,6):
        live={"status":"ok","price_inr":35000-rank*1000,"checked_at":datetime.now(timezone.utc).isoformat()} if rank in (1,2) else {"status":"unavailable"}
        rows.append({"id":f"{rank:024x}","live":live})
    return {"success":True,"data":rows}

class WebsitePriceParityTest(unittest.TestCase):
    def fetcher(self,spec):
        self.assertEqual(spec["budget"],40000)
        return source()
    def post(self,body):
        def opener(request,timeout):
            self.assertEqual(request.method,"POST")
            self.assertEqual(request.full_url,"https://api.trustfolio.in/api/live-prices")
            self.assertEqual(json.loads(request.data),{"ids":[f"{i:024x}" for i in range(1,6)]})
            return Response(body)
        return opener
    def run_pipeline(self,body=None):
        approved=build_verified_two_api({"category":"washing-machines","budget":40000,"mode":"budget","brand":""},
            get_fetcher=self.fetcher,post_opener=self.post(body or price_rows()))
        return approved,build30(approved,references=verify_reference_images())
    def test_mixed_website_live_and_catalog_fallback_disclosed(self):
        snapshot,story=self.run_pipeline()
        self.assertEqual(snapshot["live_price_count"],2)
        self.assertEqual(snapshot["catalog_fallback_count"],3)
        products=story["scenes"][2:7]
        self.assertEqual([s["dynamic"]["rank"] for s in products],[5,4,3,2,1])
        self.assertTrue(all("verify retailer" in s["dynamic"]["price_label"] for s in products))
        self.assertEqual(products[0]["dynamic"]["price_source"],"website_catalog")
        self.assertEqual(products[-1]["dynamic"]["price_source"],"website_live_price_api")
        self.assertFalse(story["publishing_enabled"])
    def test_changed_id_refuses_without_substitution(self):
        rows=price_rows();rows["data"][0]["id"]="fff"*8
        with self.assertRaises(Blocked):self.run_pipeline(rows)
    def test_live_outside_budget_refuses(self):
        rows=price_rows();rows["data"][0]["live"]["price_inr"]=45000
        with self.assertRaises(Blocked):self.run_pipeline(rows)
    def test_missing_rows_refuses(self):
        rows=price_rows();rows["data"].pop()
        with self.assertRaises(Blocked):self.run_pipeline(rows)
    def test_explicit_out_of_stock_refuses(self):
        rows=price_rows();rows["data"][2]["live"]={"status":"out_of_stock"}
        with self.assertRaises(Blocked):self.run_pipeline(rows)

if __name__=="__main__":
    unittest.main()
