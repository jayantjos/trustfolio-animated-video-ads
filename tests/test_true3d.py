"""Isolated 3D proof renderer audit, no publication or invented SKU meshes."""
import ast
import json
from pathlib import Path
import unittest

from trustfolio_video.demo import approve_historical_demo
from trustfolio_video.educational import build_educational_story

ROOT=Path(__file__).resolve().parents[1]
SCENE=ROOT/"three_d"/"tropical_laundry.py"

class Genuine3DPilotTests(unittest.TestCase):
    def test_blender_scene_is_3d_geometry_not_still_image(self):
        content=SCENE.read_text(encoding="utf8")
        ast.parse(content)
        for required in ("primitive_uv_sphere_add","primitive_cube_add",
                         "primitive_torus_add","primitive_cylinder_add",
                         "area(","sun.energy","camera_data.type=",
                         "keyframe_insert","sourceSha256",
                         "NOT FOR PUBLICATION","brand","image_mat",
                         "actual rank brand","original"):
            with self.subTest(token=required):
                self.assertIn(required,content)
    def test_real_five_products_locked_to_source(self):
        env=json.loads((ROOT/"evidence/washing-machines-snapshot.json").read_text())
        data=approve_historical_demo(env)
        self.assertTrue(data["demo_only"])
        self.assertFalse(data["publishing_enabled"])
        story=build_educational_story(data)
        self.assertEqual(story["ranked_source_ids"],[p["id"] for p in data["products"]])
        self.assertEqual([p["rank"] for p in data["products"]],[1,2,3,4,5])
    def test_3d_workflow_is_dedicated_private_qa(self):
        text=(ROOT/".github/workflows/true-3d-tropical-qa.yml").read_text(encoding="utf8")
        self.assertIn("blender",text)
        self.assertIn("premium/prepare.py",text)
        self.assertIn("premium/tts_kokoro.py",text)
        self.assertIn("NOT_FOR_PUBLICATION",text)
        self.assertNotIn("publish-instagram",text)
        self.assertNotIn("deploy-prod",text)

if __name__=="__main__":
    unittest.main()
