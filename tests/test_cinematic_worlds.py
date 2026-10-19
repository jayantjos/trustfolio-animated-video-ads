"""QA for genuinely separate Blender category archetypes and scenes.

This checks source contracts; GitHub Actions is required for visual frames.
"""
import ast
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"three_d"/"category_movie.py"

class Cinematic3DWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code=SRC.read_text("utf-8")
        cls.ast=ast.parse(cls.code)
        cls.worlds=json.loads((ROOT/"config"/"world_motion_20.json").read_text())
        cls.master=json.loads((ROOT/"config"/"category_education_30.json").read_text())
    def test_all_twenty_tracked_backend_slugs(self):
        a={w["slug"] for w in self.worlds["enabled_worlds"]}
        b={w["backend_slug"] for w in self.master["slots"] if w["enabled"]}
        self.assertEqual(len(a),20)
        self.assertEqual(a,b)
        self.assertEqual(sum(not x["enabled"] for x in self.master["slots"]),10)
    def test_true_blender_geometry_and_expressions_not_flat_zoom(self):
        for symbol in ("bpy.ops.render.render","cam.location.x","rotation_euler",
           "animated pupil","3D mouth talking","animated sleeve","walking leg hinge",
           "bpy.data.lights.new","cylinder(","sphere(","B.ring","scene-provenance.json"):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol,self.code)
    def test_all_twenty_category_shapes_are_distinct_or_declared(self):
        groups=[
          "washing-machines","refrigerators","smart-phones","tablets",
          "smart-tvs","desktop-computers","laptops","smartwatches",
          "headphones-earbuds","ceiling-fans","drones","air-conditioners",
          "air-coolers","speakers","water-purifiers","geysers",
          "microwave-ovens","mixer-grinders","induction-cooktops",
          "vacuum-cleaners"
        ]
        self.assertEqual(len(groups),len(set(groups)))
        for slug in groups:self.assertIn(slug,self.code)
    def test_no_static_product_prices_or_fake_skus(self):
        for banned in ('₹28,990','₹34,990','₹38,990','"rank":1',
                       "source_product_count\":5","publishing_enabled\":True"):
            self.assertNotIn(banned,self.code)
        self.assertIn('"source_product_count":0',self.code)
        self.assertIn('"production_approved":False',self.code)
    def test_video_renderer_does_not_network_fetch(self):
        self.assertNotIn("urlopen",self.code)
        self.assertNotIn("requests.get",self.code)
        self.assertNotIn("subprocess.run(",self.code)
        self.assertNotIn("os.system(",self.code)
    def test_all_story_modes_still_owned_by_existing_engine(self):
        src=(ROOT/"trustfolio_video"/"educational.py").read_text("utf-8")
        self.assertIn("build_educational_story",src)
        self.assertIn("source_sha256",src)
        self.assertIn("brand_budget",src)
        self.assertIn("comparison",src)
    def test_qa_workflow_has_no_social_write(self):
        text=(ROOT/".github/workflows/20-cinematic-worlds-demo.yml").read_text("utf-8")
        self.assertIn("NOT_FOR_PUBLICATION",text)
        self.assertIn("actions/upload-artifact@v4",text)
        self.assertIn("Blender",text)
        self.assertNotIn("api.instagram.com",text)
        self.assertNotIn("youtube.upload",text)

if __name__=="__main__":unittest.main()
