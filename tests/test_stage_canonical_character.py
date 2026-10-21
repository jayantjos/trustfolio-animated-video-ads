import tempfile,unittest
from pathlib import Path
from scripts.stage_canonical_character import hash_image
class ApprovedCharacterTests(unittest.TestCase):
    def test_absent_image_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,"NOT_IN_REPO"):hash_image(Path(td)/"absent.png")
    def test_wrong_image_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"hero.png";p.write_bytes(b"random person")
            with self.assertRaisesRegex(ValueError,"SIZE_MISMATCH"):hash_image(p)
if __name__=="__main__":unittest.main()
