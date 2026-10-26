"""Tests: website Top5 parity is a NONPUBLISHABLE preview, never live verification."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from trustfolio_flow.live import DataBlocked, campaign, check_receipt, sha
from trustfolio_flow.site_display import (
    SOURCE, normalize_website_display, fetch_website_display,
    check_site_display, check_flow_receipt
)
from trustfolio_flow.flow_prompts import prompt_for, write_prompts

NOW = datetime.now(timezone.utc)


def website_fixture():
    rows = []
    for rank, (brand, platform, price) in enumerate([
        ("IFB", "flipkart", 23500),
        ("IFB", "croma", 24994),
        ("Samsung", "amazon", 20990),
        ("Bosch", "flipkart", 23290),
        ("Whirlpool", "amazon", 23090),
    ], 1):
        rows.append({
            "id": f"{rank:024x}", "rank": rank, "product_category": "washing-machines",
            "title": f"{brand} {rank} kg Fixture Washing Machine",
            "brand": brand, "platform": platform, "price_inr": price,
            "specifications": {"Capacity": "8 kg"}, "is_active": True, "in_stock": True,
            "main_image": f"https://m.media-amazon.com/images/demo{rank}.jpg",
        })
    return {"category": "washing-machines", "budget": 25000, "products": rows}


def fixture_receipt():
    return normalize_website_display(
        website_fixture(), spec=campaign("washing-machines", 25000), now=NOW
    )


class SiteDisplayTests(unittest.TestCase):
    def test_website_prices_preserve_rank_not_live(self):
        result = check_site_display(fixture_receipt(), now=NOW)
        self.assertEqual([p["brand"] for p in result["products"]],
                         ["IFB", "IFB", "Samsung", "Bosch", "Whirlpool"])
        self.assertEqual([p["price_inr"] for p in result["products"]],
                         ["23500", "24994", "20990", "23290", "23090"])
        self.assertEqual(result["pricing_verification"], "WEBSITE_LISTED_ONLY")
        self.assertFalse(result["publishable"])
        self.assertTrue(all(p["live_price_status"] == "not_verified_for_video"
                            for p in result["products"]))

    def test_one_GET_no_live_price_POST(self):
        calls = []
        class Response:
            status = 200
            headers = {"Content-Type": "application/json"}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, n): return json.dumps({"success": True, "data": website_fixture()}).encode()
        def opener(req, timeout=40):
            calls.append((req.get_method(), req.full_url, req.data))
            return Response()
        result = fetch_website_display("washing-machines", 25000, opener=opener, now=NOW)
        self.assertEqual([x[0] for x in calls], ["GET"])
        self.assertIn("budget=25000", calls[0][1])
        self.assertEqual(result["api_evidence"]["live_price_post_calls"], 0)

    def test_existing_strict_checker_blocks_website_price(self):
        with self.assertRaises(DataBlocked):
            check_receipt(fixture_receipt(), now=NOW)

    def test_prompts_keep_premium_and_no_live_badge(self):
        receipt = fixture_receipt()
        p = prompt_for(8, receipt)
        self.assertIn("WEBSITE-LISTED PRICE (NOT LIVE VERIFIED)", p)
        self.assertIn("Bosch", p)
        self.assertIn("₹23,290", p)
        self.assertIn("PREVIEW ONLY, NEVER PUBLISH", p)
        self.assertNotIn("Rank #1 ACTUAL VERIFIED PRICE", prompt_for(7, receipt))
        self.assertIn("TrustFolio.in", prompt_for(10, receipt))

    def test_six_flow_prompts_preview_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = write_prompts(fixture_receipt(), td)
            self.assertFalse(manifest["publishable"])
            self.assertEqual(manifest["pricing_verification"], "WEBSITE_LISTED_ONLY")
            self.assertEqual(len(list((Path(td) / "prompts").glob("*.txt"))), 6)

    def test_snapshot_price_tamper_rejected(self):
        data = fixture_receipt()
        data["products"][0]["price_inr"] = "1"
        with self.assertRaises(DataBlocked): check_site_display(data, now=NOW)

    def test_different_rank_rejected(self):
        data = website_fixture()
        data["products"][3]["rank"] = 5
        with self.assertRaises(DataBlocked):
            normalize_website_display(data, spec=campaign("washing-machines", 25000), now=NOW)

    def test_out_of_stock_rejected(self):
        data = website_fixture()
        data["products"][2]["in_stock"] = False
        with self.assertRaises(DataBlocked):
            normalize_website_display(data, spec=campaign("washing-machines", 25000), now=NOW)

    def test_over_budget_rejected(self):
        data = website_fixture()
        data["products"][3]["price_inr"] = 30000
        with self.assertRaises(DataBlocked):
            normalize_website_display(data, spec=campaign("washing-machines", 25000), now=NOW)

    def test_invalid_image_rejected(self):
        data = website_fixture()
        data["products"][1]["main_image"] = "https://127.0.0.1/a.jpg"
        with self.assertRaises(DataBlocked):
            normalize_website_display(data, spec=campaign("washing-machines", 25000), now=NOW)

    def test_wrong_brand_rejected(self):
        data = website_fixture()
        data["fallbackApplied"] = True
        with self.assertRaises(DataBlocked):
            normalize_website_display(data, spec=campaign("washing-machines", 25000, "brand_budget", "IFB"), now=NOW)

    def test_stale_receipt_rejected(self):
        with self.assertRaises(DataBlocked):
            check_site_display(fixture_receipt(), now=NOW + timedelta(hours=1))

    def test_false_live_claim_rejected(self):
        data = fixture_receipt()
        data["products"][0]["live_price_status"] = "ok"
        spec = campaign("washing-machines", 25000)
        data["snapshot_sha256"] = sha({"spec": spec, "products": data["products"]})
        with self.assertRaises(DataBlocked):
            check_site_display(data, now=NOW)

    def test_missing_id_rejected(self):
        data = website_fixture()
        data["products"][3]["id"] = ""
        with self.assertRaises(DataBlocked):
            normalize_website_display(data, spec=campaign("washing-machines", 25000), now=NOW)

    def test_validated_dispatch(self):
        self.assertEqual(check_flow_receipt(fixture_receipt(), now=NOW)["source"], SOURCE)


if __name__ == "__main__":
    unittest.main()
