import copy,hashlib,unittest
from datetime import datetime,timezone,timedelta
from trustfolio_video.contract import canonical,campaign,api_url,Blocked
from trustfolio_video.cron_video_job import build_video_job

NOW=datetime(2026,10,21,12,30,tzinfo=timezone.utc)
def fresh_payload(category="washing-machines",mode="budget",budget=35000,brand=""):
    desired=campaign(category,budget,mode,brand)
    at=NOW.isoformat()
    products=[]
    for rank in range(1,6):
        products.append({
            "id":f"{rank:024x}", "rank":rank,"product_category":category,
            "title":"Source Verified Product "+str(rank),
            "brand":brand if brand else "Verified Brand "+str(rank),
            "price_inr":1000+rank*200,"platform":"ApprovedRetailer",
            "is_active":True,"in_stock":True,
            "main_image":"https://m.media-amazon.com/images/I/test-model.jpg",
            "price_source":"website_live_price_api","live_price_status":"ok",
            "live_checked_at":at,
        })
    response={"success":True,"data":{"category":category,"budget":budget,
             "livePriceRefreshCompleted":True,"products":products}}
    if mode=="brand_budget":
        response["data"]["requestedBrand"]=brand
        response["data"]["fallbackApplied"]=False
        response["data"]["partialBrandFill"]=False
    envelope={"request":desired,"source_url":api_url(desired),"observed_at":at,
              "response":response,"response_sha256":hashlib.sha256(canonical(response).encode()).hexdigest()}
    return {"schema_version":1,"producer":"trustfolio-vps-cron",
            "job_id":"washing-20261021-001","requested_at":at,
            "campaign":desired,"snapshot":envelope}
def resign(payload):
    response=payload["snapshot"]["response"]
    payload["snapshot"]["response_sha256"]=hashlib.sha256(canonical(response).encode()).hexdigest()
class VPSCronJobTests(unittest.TestCase):
    def test_story_matches_reference_timeline_and_dynamic_rank(self):
        payload=fresh_payload()
        job=build_video_job(payload,now=NOW)
        self.assertEqual(job["rank_reveal_order"],[5,4,3,2,1])
        self.assertEqual(len(job["scene_timeline"]),9)
        self.assertEqual([s["product"]["rank"] for s in job["scene_timeline"] if "product" in s],[5,4,3,2,1])
        self.assertEqual(job["scene_timeline"][2]["product"]["source_id"],f"{5:024x}")
        self.assertFalse(job["paid_gpu_authorized"])
        self.assertFalse(job["social_publishing_enabled"])
        self.assertEqual(job["render_eligibility"],"VALIDATED_LIVE_DATA_ART_QA_PENDING")
        self.assertEqual(job["idempotency_sha256"],build_video_job(payload,now=NOW)["idempotency_sha256"])
    def test_budget_breach_blocks(self):
        data=fresh_payload(budget=2000)
        data["snapshot"]["response"]["data"]["products"][0]["price_inr"]=2001
        resign(data)
        with self.assertRaises(Blocked):build_video_job(data,now=NOW)
    def test_catalog_fallback_or_stale_price_blocks(self):
        data=fresh_payload()
        data["snapshot"]["response"]["data"]["products"][0]["live_price_status"]="fallback"
        resign(data)
        with self.assertRaises(Blocked):build_video_job(data,now=NOW)
        data=fresh_payload()
        data["snapshot"]["response"]["data"]["products"][0]["live_checked_at"]=(NOW-timedelta(hours=2)).isoformat()
        resign(data)
        with self.assertRaises(Blocked):build_video_job(data,now=NOW)
    def test_inconsistent_snapshot_request_blocks(self):
        data=fresh_payload()
        data["campaign"]["budget"]=40000
        with self.assertRaises(Blocked):build_video_job(data,now=NOW)
    def test_expired_job_blocks(self):
        data=fresh_payload()
        data["requested_at"]=(NOW-timedelta(hours=2)).isoformat()
        with self.assertRaises(Blocked):build_video_job(data,now=NOW)
    def test_other_supported_category_awaits_approved_theme_art(self):
        data=fresh_payload(category="smart-phones",budget=35000)
        job=build_video_job(data,now=NOW)
        self.assertEqual(job["render_eligibility"],"CATEGORY_SCENE_ART_NOT_APPROVED")
        self.assertEqual(job["scene_timeline"],[])
    def test_brand_budget_preserves_brand_filter(self):
        data=fresh_payload(mode="brand_budget",brand="Samsung")
        job=build_video_job(data,now=NOW)
        self.assertEqual(job["campaign"]["brand"],"Samsung")
    def test_no_unverified_product_claims(self):
        job=build_video_job(fresh_payload(),now=NOW)
        joined=str(job["scene_timeline"])
        self.assertNotIn("Steam Wash",joined)
        self.assertNotIn("AI Wash",joined)
        self.assertNotIn("₹28,990",joined)
if __name__=="__main__":unittest.main()
