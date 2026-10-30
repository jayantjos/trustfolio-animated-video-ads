import unittest,tempfile,zipfile
from unittest.mock import patch
from pathlib import Path
from final_master.scripts.campaign import plan
class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.kit=Path(self.tmp.name)/"kit.zip"
        with zipfile.ZipFile(self.kit,"w") as z:
            for n in ("assets/video/08_green_boy_clean_master.mp4","assets/video/09_premium_girl_cta.mp4","assets/audio/original/08_green_boy_clean_master.wav"):z.writestr(n,"sample")
        self.receipt={"source":"trustfolio_live_api","category":"washing-machines","mode":"budget","brand":"","budget_inr":25000,"snapshot_sha256":"a"*64,"products":[{"rank":i,"id":str(i),"brand":"IFB","title":"Example","price_inr":12000,"platform":"amazon","image_url":"https://example.org/x.jpg","live_price_status":"ok","specifications":{"Capacity":"8kg","Load Type":"Front","Energy Rating":"5 star","Spin Speed":"1200 rpm"}} for i in range(1,6)]}
    def tearDown(self):self.tmp.cleanup()
    def checked_plan(self):
        with patch("final_master.scripts.campaign.check_receipt",return_value=self.receipt):
            return plan(self.receipt,self.kit)
    def test_valid_contract(self):self.assertFalse(self.checked_plan()["publish_allowed"])
    def test_overbudget_rejected(self):
        self.receipt["products"][0]["price_inr"]=27000
        with self.assertRaises(ValueError):self.checked_plan()
    def test_brand_mismatch_rejected(self):
        self.receipt.update(mode="brand_budget",brand="Samsung")
        with self.assertRaises(ValueError):self.checked_plan()
    def test_missing_specs_rejected(self):
        self.receipt["products"][0]["specifications"]={}
        with self.assertRaises(ValueError):self.checked_plan()
if __name__=="__main__":unittest.main()
