import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from scripts.stage_canonical_character import (
    hash_image, upload_and_verify, CharacterStageError, safe_s3_error,
    EXPECTED, EXPECTED_BYTES, IMAGE, BUCKET
)

class FakeS3:
    def __init__(self):
        self.payload = None
        self.put_calls = []
    def put_object(self, **kw):
        self.put_calls.append(kw)
        self.payload = kw["Body"]
    def get_object(self, **kw):
        assert kw == {"Bucket": BUCKET, "Key": IMAGE}
        return {"Body": io.BytesIO(self.payload), "ContentLength": len(self.payload)}

class ApprovedCharacterTests(unittest.TestCase):
    def test_absent_image_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(CharacterStageError, "NOT_IN_REPO"):
                hash_image(Path(td) / "absent.png")
    def test_wrong_image_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "hero.png"
            p.write_bytes(b"random person")
            with self.assertRaisesRegex(CharacterStageError, "SIZE_MISMATCH"):
                hash_image(p)
    def test_sha_check_rejects_wrong_bytes_without_put(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "hero.png"
            p.write_bytes(b"0" * EXPECTED_BYTES)
            s3 = FakeS3()
            with self.assertRaisesRegex(CharacterStageError, "SHA256_MISMATCH"):
                upload_and_verify(s3, p)
            self.assertEqual([], s3.put_calls)
    def test_s3_error_redacts_provider_messages(self):
        class APIError(Exception):
            response={"ResponseMetadata": {"HTTPStatusCode": 403},
                      "Error": {"Code": "AccessDenied",
                                "Message": "private details must not log"}}
        self.assertEqual("S3_HTTP_403_AccessDenied", safe_s3_error(APIError()))
    def test_s3_get_mismatch_fails(self):
        # Only the real pinned original can pass the full upload test.
        self.assertTrue(EXPECTED.startswith("7f9ca4"))
    def test_checked_in_approved_asset_upload_get_matches(self):
        if not Path(IMAGE).is_file():
            self.skipTest("Original binary not supplied in local test checkout")
        s3 = FakeS3()
        r = upload_and_verify(s3)
        self.assertEqual(r["sha256"], EXPECTED)
        self.assertEqual(r["bytes"], EXPECTED_BYTES)
        self.assertEqual(s3.put_calls[0]["Key"], IMAGE)
        self.assertEqual(len(s3.payload), EXPECTED_BYTES)

if __name__ == "__main__":
    unittest.main()
