"""Offline TTS and persistent per-model photo approval tests (zero API calls)."""
import unittest
from unittest.mock import patch
from trustfolio_flow.v6_hindi_voice_tts import scripts
from trustfolio_flow.v6_photo_registry import resolve
from trustfolio_flow.live import DataBlocked

def receipt():
    p=[]
    for i in range(1,6):
        p.append({"rank":i,"id":f"{i:024x}","brand":"IFB" if i<3 else "Samsung",
         "image_url":f"https://m.media-amazon.com/images/I/test{i}.jpg",
         "specifications":{"Capacity":"8 kg","Load Type":"Top Load",
           "Energy Rating":"5 Star","Automation Type":"Fully Automatic"}})
    return {"snapshot_sha256":"a"*64,"products":p}

def photos(r):
    return {"source_receipt_sha256":r["snapshot_sha256"],"products":[
      {"rank":p["rank"],"id":p["id"],"image_url":p["image_url"],
       "image_sha256":f"{p['rank']:064x}","model_identity_ok":False,
       "product_photo_ok":False,"commercial_usage_ok":False}
        for p in r["products"]]}

def registry(r,pending):
    return {"approved_models":{p["id"]:{
      "approved":True,"source_image_url":p["image_url"],
      "image_sha256":pending["products"][i]["image_sha256"],
      "model_identifier":f"MODEL-{i+1}"}
      for i,p in enumerate(r["products"])}}

class Gates(unittest.TestCase):
    def test_real_source_voice_not_invented(self):
        with patch("trustfolio_flow.v6_hindi_voice_tts.validate_receipt"):
            data=scripts(receipt())
        self.assertEqual(len(data),5)
        self.assertIn("आई एफ बी",data[0])
        self.assertIn("टॉप लोड",data[2])
    def test_invalid_capacity_refuses_pronunciation_guess(self):
        r=receipt();r["products"][2]["specifications"]["Capacity"]="N/A"
        with patch("trustfolio_flow.v6_hindi_voice_tts.validate_receipt"):
            with self.assertRaises(ValueError):scripts(r)
    def test_first_photo_campaign_requires_review(self):
        r=receipt();p=photos(r)
        with patch("trustfolio_flow.v6_photo_registry.check_receipt"):
            with self.assertRaisesRegex(DataBlocked,"Model photo not yet approved"):
                resolve(r,p,{"approved_models":{}})
    def test_signed_registry_reuse(self):
        r=receipt();p=photos(r)
        with patch("trustfolio_flow.v6_photo_registry.check_receipt"),patch(
             "trustfolio_flow.v6_photo_registry.check_photo_approvals"):
            result=resolve(r,p,registry(r,p))
        self.assertEqual(result["status"],"APPROVED_PHOTOS_EXACT_SHA256")
        self.assertTrue(all(x["product_photo_ok"] for x in result["products"]))
    def test_source_photo_changed_fails(self):
        r=receipt();p=photos(r);reg=registry(r,p)
        p["products"][0]["image_sha256"]="f"*64
        with patch("trustfolio_flow.v6_photo_registry.check_receipt"):
            with self.assertRaisesRegex(DataBlocked,"photo changed"):
                resolve(r,p,reg)

if __name__=="__main__":unittest.main()
