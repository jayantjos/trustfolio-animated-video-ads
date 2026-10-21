"""Tests of no-cost, fail-closed GPU input bundle packaging."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from scripts.package_gpu_job import BundleError, prepare, make_bundle

class TestGPUJobPackage(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.images = [
            "assets/characters/washing-machines/hero.png",
            "assets/locations/washing-machines/scene02.png",
            "assets/locations/washing-machines/showroom.png",
            "assets/locations/washing-machines/cta.png"]
        self.pilot = {
            "category": "washing-machines", "production_publishing": False,
            "canonical_image": self.images[0],
            "character_id": "trustfolio-washing-machines-lead-v1",
            "canonical_image_sha256": hashlib.sha256(b"hero fixture").hexdigest(),
            "total_seconds": 30,
            "video_model": {"code_repository": "https://github.com/Wan-Video/Wan2.2",
                            "model_repository": "https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B",
                            "required_gpu_vram_gb": 24},
            "scene_blueprint": [
                {"seconds": 5, "image_asset": self.images[0]},
                {"seconds": 4, "image_asset": self.images[1]},
                {"seconds": 15, "image_asset": self.images[2],
                 "kind": "five_authoritative_products", "rank_order": [5,4,3,2,1]},
                {"seconds": 6, "image_asset": self.images[3]}]}
        self.spec = self.root / "pilot.json"
        self.spec.write_text(json.dumps(self.pilot), encoding="utf-8")

    def test_missing_assets_plan_is_safe(self):
        _, manifest = prepare(self.spec, self.root)
        self.assertEqual(manifest["status"], "INPUTS_PENDING")
        self.assertEqual(len(manifest["missing_required_inputs"]), 5)
        self.assertFalse(manifest["publishing_enabled"])
        self.assertFalse(manifest["gpu_provisioned"])

    def test_bundle_blocks_missing_inputs(self):
        with self.assertRaises(BundleError):
            make_bundle(self.spec, self.root, None, self.root / "result.zip")

    def test_bundle_contains_images_audio_and_checksums(self):
        for path in self.images:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"hero fixture" if path == self.images[0] else b"scene fixture")
        audio = self.root / "hindi.mp3"
        audio.write_bytes(b"mp3 fixture")
        destination = self.root / "result.zip"
        manifest = make_bundle(self.spec, self.root, audio, destination)
        self.assertEqual(manifest["status"], "INPUTS_VERIFIED_NO_GPU_RENDER")
        with ZipFile(destination) as archive:
            self.assertEqual(set(archive.namelist()),
                             {"pilot.json", "job.json", "audio/hi-IN.mp3", *self.images})
            for entry in manifest["assets"]:
                self.assertEqual(hashlib.sha256(archive.read(entry["path"])).hexdigest(), entry["sha256"])
            self.assertFalse(json.loads(archive.read("job.json"))["publishing_enabled"])

    def test_wrong_hero_is_blocked(self):
        hero = self.root / self.images[0]
        hero.parent.mkdir(parents=True, exist_ok=True)
        hero.write_bytes(b"wrong master")
        with self.assertRaisesRegex(BundleError, "SHA256"):
            prepare(self.spec, self.root)

    def test_path_traversal_is_blocked(self):
        self.pilot["scene_blueprint"][1]["image_asset"] = "assets/../secrets.env"
        self.spec.write_text(json.dumps(self.pilot), encoding="utf-8")
        with self.assertRaisesRegex(BundleError, "Unsafe"):
            prepare(self.spec, self.root)

if __name__ == "__main__":
    unittest.main()
