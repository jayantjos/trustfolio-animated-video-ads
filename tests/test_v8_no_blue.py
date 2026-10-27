"""No API cost: unit tests for deterministic V8 no-blue stage recolor."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

file=Path(__file__).resolve().parents[1]/"scripts/grade_v8_no_blue.py"
spec=importlib.util.spec_from_file_location("grade_v8_no_blue",file)
v8=importlib.util.module_from_spec(spec);spec.loader.exec_module(v8)

class NoBlueV8(unittest.TestCase):
    def test_blue_hue_becomes_warm_copper(self):
        r,g,b=v8.warm_pixel(.08,.19,.79)
        self.assertGreater(r,b)
        self.assertGreater(r,g)
    def test_purple_stage_becomes_warm_bronze(self):
        r,g,b=v8.warm_pixel(.25,.10,.50)
        self.assertGreater(r,b)
        self.assertGreater(r,g)
    def test_gold_and_skin_unchanged(self):
        for color in [(0.88,.67,.41),(.91,.74,.61),(.73,.41,.31)]:
            self.assertTrue(all(abs(a-b)<1e-5 for a,b in zip(v8.warm_pixel(*color),color)))
    def test_white_and_black_unchanged(self):
        self.assertEqual(v8.warm_pixel(1,1,1),(1,1,1))
        self.assertEqual(v8.warm_pixel(0,0,0),(0,0,0))
    def test_lut_reusable_49_cube(self):
        with tempfile.TemporaryDirectory() as td:
            p=v8.write_lut(Path(td)/"v8.cube",49)
            lines=p.read_text().splitlines()
            self.assertEqual(lines[1],"LUT_3D_SIZE 49")
            self.assertEqual(len(lines),4+49**3)
    def test_invalid_lut_or_missing_video_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):v8.write_lut(Path(td)/"bad",size=8)
            with self.assertRaises(ValueError):
                v8.grade(Path(td)/"missing.mp4",Path(td)/"out.mp4")
if __name__=="__main__":unittest.main()
