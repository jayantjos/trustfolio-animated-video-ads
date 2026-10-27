"""Deterministic, no-network tests for image cutout and source safety."""
import unittest
from PIL import Image,ImageDraw
from trustfolio_flow.v6_product_images import make_cutout

class ImageCutoutTests(unittest.TestCase):
    def test_white_border_conservative_mask(self):
        im=Image.new("RGBA",(450,500),(255,255,255,255))
        ImageDraw.Draw(im).rectangle((130,40,325,480),fill=(46,43,50,255))
        cut,yes=make_cutout(im)
        self.assertTrue(yes)
        self.assertEqual(cut.getpixel((0,0))[3],0)
        self.assertEqual(cut.getpixel((250,250))[3],255)
    def test_patterned_background_does_not_guess_silhouette(self):
        im=Image.new("RGBA",(450,500),(65,80,112,255))
        cut,yes=make_cutout(im)
        self.assertFalse(yes)
        self.assertEqual(cut.getchannel("A").getextrema(),(255,255))
    def test_already_transparent_preserved(self):
        im=Image.new("RGBA",(450,500),(0,0,0,0))
        ImageDraw.Draw(im).ellipse((120,90,350,455),fill=(52,58,59,255))
        cut,yes=make_cutout(im)
        self.assertFalse(yes)
        self.assertEqual(cut.getpixel((0,0))[3],0)
        self.assertEqual(cut.getpixel((200,200))[3],255)

if __name__=="__main__":unittest.main()
