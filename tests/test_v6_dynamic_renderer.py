"""Offline V6 dynamic compositing validation; no marketplace API/Meta writes."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from trustfolio_flow.v6_dynamic_renderer import (
    fit,photo_png,make_assets,make_spotlights,price
)

def fixture(td):
    folder=Path(td);(folder/"photos").mkdir()
    products=[];reviews=[]
    for i in range(1,6):
        im=Image.new("RGBA",(500,500),(0,0,0,0))
        ImageDraw.Draw(im).rounded_rectangle((110,40,392,478),fill=(40+i*25,35,80,255))
        path=folder/"photos"/f"rank_{i:02d}.png";im.save(path)
        products.append({"rank":i,"id":f"{i:024x}","brand":f"Brand{i}","platform":"amazon",
            "title":f"Brand{i} Long Detailed Fully Automatic 8 kg Test Washing Machine Model {i}",
            "price_inr":str(22000+i),
            "specifications":{"Capacity":"8 kg","Load Type":"Top Load",
              "Energy Rating":"5 Star","Automation Type":"Fully Automatic"}})
        reviews.append({"rank":i,"id":f"{i:024x}","image_sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    return {"budget_inr":25000,"products":products},{"products":reviews}

class V6RenderTests(unittest.TestCase):
    def test_prices_come_from_source(self):
        self.assertEqual(price({"price_inr":"22990"}),"₹22,990")
    def test_long_titles_fit(self):
        lines=fit("IFB Very Long Washing Machine Fully Automatic AI Technology with Heat and Smart System",350,27,2)
        self.assertLessEqual(len(lines),2)
    def test_reject_photo_sha_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"a.png"
            Image.new("RGBA",(500,500),(0,0,0,0)).save(path)
            with self.assertRaises(ValueError):
                photo_png(path,"0"*64)
    def test_reject_opaque_model_image(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"a.png"
            Image.new("RGBA",(500,500),(255,255,255,255)).save(path)
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,"transparent"):
                photo_png(path,digest)
    def test_all_five_dynamic_stage_positions_and_four_specs(self):
        with tempfile.TemporaryDirectory() as td:
            r,p=fixture(td)
            layers,cutouts,stage_path=make_assets(r,p,td)
            self.assertEqual(set(layers),{"spec_a","spec_b","budget","top3","top5","compare"})
            self.assertEqual(len(cutouts),5)
            self.assertIsNotNone(layers["spec_b"].getbbox())
            Image.new("RGB",(720,1280),(34,18,70)).save(stage_path)
            imgs=make_spotlights(r,cutouts,stage_path,td)
            self.assertEqual(len(imgs),5)
            self.assertTrue(all(x.is_file() for x in imgs))
    def test_different_price_appears_in_dynamic_frame(self):
        with tempfile.TemporaryDirectory() as td:
            r,p=fixture(td)
            base,_,_=make_assets(r,p,td)
            r["products"][0]["price_inr"]="19999"
            changed,_,_=make_assets(r,p,td)
            self.assertNotEqual(base["top3"].tobytes(),changed["top3"].tobytes())

if __name__=="__main__":unittest.main()
