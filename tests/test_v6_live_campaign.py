"""Offline safety tests for V6 product data, audio and publish gates."""
import copy
import unittest
from datetime import datetime,timezone
from trustfolio_flow.live import normalize_live,campaign,DataBlocked
from trustfolio_flow.v6_live_campaign import (
    handoff,caption_for,source_specs,check_photo_approvals,prepublish_hard_gate,
    V6_APPROVED_VISUAL_SHA256)

NOW=datetime.now(timezone.utc)
def example():
    get={"category":"washing-machines","products":[]}
    live=[]
    for i in range(1,6):
        pid=f"{i:024x}"
        p={"rank":i,"id":pid,"title":f"Verified Washing Machine {i} 8 kg Top Load",
           "brand":f"Brand{i}","platform":"amazon","price_inr":21000+i,
           "main_image":f"https://m.media-amazon.com/images/I/mock{i}.jpg",
           "specifications":{"Capacity":"8 kg","Load Type":"Top Load",
             "Energy Rating":"5 Star","Automation Type":"Fully Automatic"},
           "is_active":True,"in_stock":True}
        get["products"].append(p)
        live.append({"id":pid,"deleted":False,"live":{"status":"ok","price_inr":21000+i,
              "checked_at":NOW.isoformat()}})
    r=normalize_live(get,live,spec=campaign("washing-machines",25000),now=NOW)
    images={"products":[{"rank":p["rank"],"id":p["id"],"image_url":p["image_url"],
          "image_sha256":f"{p['rank']:064x}","model_identity_ok":True,
          "product_photo_ok":True,"commercial_usage_ok":True} for p in r["products"]]}
    return r,images

class V6LiveGates(unittest.TestCase):
    def test_valid_five_live_prices_and_four_specs(self):
        r,images=example()
        x=handoff(r,images,now=NOW)
        self.assertEqual(len(x["four_spec_rows_by_rank"]),5)
        self.assertEqual(len(x["four_spec_rows_by_rank"]["1"]),4)
        self.assertFalse(x["post_allowed"])
        self.assertIn("budget=25000",x["landing_url"])
    def test_any_catalog_fallback_rejected(self):
        r,photos=example()
        r["source"]="trustfolio_website_display"
        with self.assertRaises(DataBlocked):handoff(r,photos,now=NOW)
    def test_missing_fourth_spec_rejected(self):
        r,photos=example()
        del r["products"][0]["specifications"]["Energy Rating"]
        with self.assertRaises(DataBlocked):handoff(r,photos,now=NOW)
    def test_wrong_photo_source_rejected(self):
        r,photos=example()
        photos["products"][2]["image_url"]="https://m.media-amazon.com/images/I/fake.jpg"
        with self.assertRaises(DataBlocked):handoff(r,photos,now=NOW)
    def test_missing_commercial_photo_approval_rejected(self):
        r,photos=example()
        photos["products"][3]["commercial_usage_ok"]=False
        with self.assertRaises(DataBlocked):handoff(r,photos,now=NOW)
    def test_duplicate_cross_brand_photo_sha_rejected(self):
        r,photos=example()
        photos["products"][2]["image_sha256"]=photos["products"][0]["image_sha256"]
        with self.assertRaises(DataBlocked):handoff(r,photos,now=NOW)
    def test_historical_video_never_published(self):
        r,photos=example()
        manifest={"source_snapshot_sha256":r["snapshot_sha256"],
           "video_sha256":V6_APPROVED_VISUAL_SHA256,
           "rendered_product_ids":[p["id"] for p in r["products"]],
           "rendered_prices_inr":[p["price_inr"] for p in r["products"]]}
        with self.assertRaises(DataBlocked):
            prepublish_hard_gate(manifest,r,r,now=NOW)
    def test_price_change_blocks_release(self):
        r,photos=example()
        future=copy.deepcopy(r)
        future["products"][0]["price_inr"]="18000"
        # Even before tamper hash recalculation this must fail via receipt validation
        with self.assertRaises(DataBlocked):
            prepublish_hard_gate({},r,future,now=NOW)
    def test_missing_hindi_voice_gate_blocks_release(self):
        r,photos=example()
        rec={"source_snapshot_sha256":r["snapshot_sha256"],
            "video_sha256":"a"*64,
            "rendered_product_ids":[p["id"] for p in r["products"]],
            "rendered_prices_inr":[p["price_inr"] for p in r["products"]],
            "frame_text_qa_pass":True,"product_model_qa_pass":True,
            "four_specs_qa_pass":True,"hindi_voice_qa_pass":False,
            "audio_loudness_qa_pass":True,"video_duration_qa_pass":True,
            "caption_qa_pass":True,"public_media_sha256_pass":True,
            "human_release_approved":True,"published":False}
        with self.assertRaisesRegex(DataBlocked,"hindi_voice"):
            prepublish_hard_gate(rec,r,r,now=NOW)
    def test_no_false_live_claim_for_historical_listings(self):
        r,_=example()
        c=caption_for(r)["caption"]
        self.assertIn("Washing Machines",c)
        self.assertIn("https://trustfolio.in/category/washing-machines/products?budget=25000",c)
        self.assertEqual(sum(x.startswith("#") and x[1].isdigit() for x in c.splitlines()),5)

if __name__=="__main__":unittest.main()
