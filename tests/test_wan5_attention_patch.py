"""CPU tests for strict source patch; no GPU/pod/network required."""
import unittest
from gpu.patch_wan_attention import patched_source

class AttnPatchTests(unittest.TestCase):
    def test_only_exact_upstream_anchor_is_accepted(self):
        original = "import torch\n\ndef flash_attention(\n    q):\n    if True:\n        pass\n    else:\n        assert FLASH_ATTN_2_AVAILABLE\n"
        modified = patched_source(original)
        self.assertIn("def _trustfolio_fused_sdpa_fallback(", modified)
        self.assertIn("SDPBackend.FLASH_ATTENTION", modified)
        self.assertIn("if not FLASH_ATTN_2_AVAILABLE:", modified)
        self.assertIn("raise RuntimeError(\"WAN_SDPA_VARLEN_SHAPE_INVALID\")", modified)
        self.assertNotIn("        assert FLASH_ATTN_2_AVAILABLE\n", modified)
    def test_refuse_already_patched_or_missing_anchor(self):
        with self.assertRaises(ValueError):
            patched_source("def flash_attention(\n    pass\n")
        with self.assertRaises(ValueError):
            patched_source(patched_source("def flash_attention(\n    q):\n    if True:\n        pass\n    else:\n        assert FLASH_ATTN_2_AVAILABLE\n"))
    def test_refuse_ambiguous_upstream_mutation(self):
        with self.assertRaises(ValueError):
            patched_source("def flash_attention(\n        assert FLASH_ATTN_2_AVAILABLE\n        assert FLASH_ATTN_2_AVAILABLE\n")
if __name__ == "__main__":
    unittest.main()
