"""Offline tests for source-image candidate auditing; no marketplace calls."""
import json,unittest
from trustfolio_flow.image_audit import image_candidates,audit_top5,fetch_image_audit
from trustfolio_flow.live import DataBlocked

def fixture():
    brands=["IFB","IFB","Bosch","Samsung","Whirlpool"]; rows=[]
    for n,brand in enumerate(brands,1):
        main=f"https://m.media-amazon.com/images/I/{n}.jpg"
        if n==3: main="https://m.media-amazon.com/images/I/1.jpg"
        rows.append({"id":f"{n:024x}","rank":n,"brand":brand,"title":f"{brand} Model {n}",
         "platform":"amazon","price_inr":20000+n,"main_image":main,
         "images":[main,f"https://m.media-amazon.com/images/I/alternate{n}.jpg"]})
    return {"category":"washing-machines","budget":25000,"products":rows}

class ImageAuditTests(unittest.TestCase):
    def test_cross_brand_primary_duplicate(self):
        r=audit_top5(fixture())
        self.assertEqual(r["status"],"BLOCKED_CROSS_BRAND_PRIMARY_IMAGE")
        self.assertEqual((r["cross_brand_primary_conflicts"][0]["rank_a"],r["cross_brand_primary_conflicts"][0]["rank_b"]),(1,3))
        self.assertEqual(r["products"][2]["candidate_count"],2)
        self.assertFalse(r["publishable"])
    def test_alt_candidates_are_not_approved(self):
        r=audit_top5(fixture())
        self.assertFalse(r["products"][2]["model_image_accuracy_verified"])
    def test_bad_network_urls_rejected(self):
        self.assertEqual(image_candidates({"images":["https://127.0.0.1/private","http://m.media-amazon.com/u.jpg","https://m.media-amazon.com/images/I/good.jpg","https://user:pw@m.media-amazon.com/x.jpg"]}),
          ["https://m.media-amazon.com/images/I/good.jpg"])
    def test_one_get_zero_post(self):
        calls=[]
        class Reply:
            status=200
            headers={"Content-Type":"application/json"}
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n): return json.dumps({"success":True,"data":fixture()}).encode()
        def opener(req,timeout=40): calls.append(req.get_method());return Reply()
        report=fetch_image_audit(opener=opener)
        self.assertEqual(calls,["GET"])
        self.assertEqual(report["live_price_post_calls"],0)
    def test_duplicate_ids_rejected(self):
        d=fixture();d["products"][1]["id"]=d["products"][0]["id"]
        with self.assertRaises(DataBlocked):audit_top5(d)
    def test_over_budget_rejected(self):
        d=fixture();d["products"][1]["price_inr"]=25001
        with self.assertRaises(DataBlocked):audit_top5(d)
if __name__=="__main__":unittest.main()
