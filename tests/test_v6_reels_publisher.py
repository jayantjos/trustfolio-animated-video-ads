"""V6 Reels fail-closed publishing tests. No real Meta or GitHub post requests."""
import copy
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from trustfolio_flow.v6_meta_reels import (
    read_config,ReelBlocked,verify_public_media,record_path,reserve,
    preflight_account,PAGE_ID,REPO)
from trustfolio_flow.v6_live_campaign import stable_product_fingerprint

class ReelSafetyTests(unittest.TestCase):
    def test_default_off(self):
        with self.assertRaisesRegex(ReelBlocked,"OFF"):
            read_config({})
    def test_first_qa_required_even_with_valid_token(self):
        with self.assertRaisesRegex(ReelBlocked,"QA"):
            read_config({"TF_VIDEO_REELS_PUBLISH_ENABLED":"true"})
    def test_wrong_page_blocked(self):
        with self.assertRaisesRegex(ReelBlocked,"Wrong Facebook"):
            read_config({"TF_VIDEO_REELS_PUBLISH_ENABLED":"true",
                "TF_VIDEO_FIRST_REEL_QA_APPROVED":"true","TF_META_PAGE_ID":"123"})
    def test_account_token_without_ledger_never_passes(self):
        with self.assertRaises(ReelBlocked):
            read_config({"TF_VIDEO_REELS_PUBLISH_ENABLED":"true",
                "TF_VIDEO_FIRST_REEL_QA_APPROVED":"true",
                "GITHUB_REPOSITORY":REPO,"TF_META_PAGE_ACCESS_TOKEN":"x"*40})
    def test_media_url_only_approved_https_path(self):
        for url in ("https://127.0.0.1/abc.mp4",
            "https://media.trustfolio.in.evil.com/trustfolio-videos/z.mp4",
            "http://media.trustfolio.in/trustfolio-videos/test.mp4",
            "https://media.trustfolio.in/other/test.mp4",
            "https://media.trustfolio.in/trustfolio-videos/real.mp4?token=x"):
            with self.subTest(url=url):
                with self.assertRaises(ReelBlocked):
                    verify_public_media(url,"0"*64)
    def test_ledger_key_one_per_network_mode_day(self):
        cfg={"today":"2026-10-28"}
        self.assertEqual(record_path(cfg,"instagram","budget"),
           "video-publication-ledger/2026-10-28/washing-machines-budget-instagram.json")
        with self.assertRaises(ReelBlocked):record_path(cfg,"youtube","budget")
    def test_github_reservation_blocks_retry_on_api_error(self):
        cfg={"today":"2026-10-28"}
        with patch("trustfolio_flow.v6_meta_reels.ledger_branch"),patch(
          "trustfolio_flow.v6_meta_reels.github",side_effect=ReelBlocked("HTTP 409")):
            with self.assertRaisesRegex(ReelBlocked,"Existing or ambiguous"):
                reserve(cfg,"instagram","budget","a"*64,"b"*64)
    def test_account_page_identity_mismatch_before_publish(self):
        cfg={"token":"x"*40,"page":PAGE_ID}
        with patch("trustfolio_flow.v6_meta_reels.json_request",return_value={"id":"000"}) as f:
            with self.assertRaisesRegex(ReelBlocked,"FB Page token"):
                preflight_account(cfg)
            self.assertEqual(f.call_count,1)
    def test_stable_fingerprint_ignores_new_price_timestamp(self):
        doc={"category":"washing-machines","budget_inr":25000,"mode":"budget","brand":"",
             "products":[{"rank":1,"id":"a"*24,"brand":"IFB","title":"A",
              "price_inr":"23000","live_checked_at":"2026-10-28T00:01:00Z",
              "specifications":{"Capacity":"8 kg"}}]}
        same=copy.deepcopy(doc);same["products"][0]["live_checked_at"]="2026-10-28T00:02:00Z"
        self.assertEqual(stable_product_fingerprint(doc),stable_product_fingerprint(same))
        same["products"][0]["price_inr"]="23001"
        self.assertNotEqual(stable_product_fingerprint(doc),stable_product_fingerprint(same))

if __name__=="__main__":unittest.main()
