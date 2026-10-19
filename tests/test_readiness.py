"""Safety regression: creative and rendering success never imply permission to publish."""
import json
from pathlib import Path
import unittest
from trustfolio_video.demo import approve_historical_demo
from trustfolio_video.educational import build_educational_story
from trustfolio_video.readiness import release_report, source_audit, video_audit, EXTERNAL_RECEIPTS

ROOT=Path(__file__).resolve().parents[1]
def source():
    return json.loads((ROOT/'evidence/washing-machines-snapshot.json').read_text('utf-8'))

class ReleaseReadinessTests(unittest.TestCase):
    def test_historical_source_blocked_even_if_backend_says_refresh_complete(self):
        env=source()
        self.assertTrue(env['response']['data']['livePriceRefreshCompleted'])
        audit=source_audit(env)
        self.assertEqual(audit['state'],'BLOCKED')
        self.assertFalse(audit['individual_fresh_prices_verified'])
    def test_real_ranked_education_passes_identity_but_does_not_approve_price(self):
        env=source()
        story=build_educational_story(approve_historical_demo(env))
        report=release_report(env,story)
        self.assertEqual(report['story']['state'],'IDENTITY_ONLY_PASSED')
        self.assertEqual(report['source']['state'],'BLOCKED')
        self.assertFalse(report['publishing_enabled'])
        self.assertFalse(report['production_ready'])
        self.assertIn('individual_price_freshness_proof',report['critical_blockers'])
    def test_all_external_receipts_cannot_enable_publish(self):
        env=source()
        story=build_educational_story(approve_historical_demo(env))
        receipts={k:{'status':'externally_verified','evidence_id':'test-receipt-123'} for k in EXTERNAL_RECEIPTS}
        qa={'status':'PRIVATE_HISTORICAL_PREMIUM_VIDEO_TECHNICAL_QA_PASSED',
            'video_sha256':'a'*64,'publishing_enabled':False}
        report=release_report(env,story,qa,receipts)
        self.assertFalse(report['publishing_enabled'])
        self.assertFalse(report['production_ready'])
        self.assertIn('official_social_publish_adapter_and_idempotency_not_approved',report['critical_blockers'])
    def test_tampered_story_source_ids_block_review(self):
        env=source()
        story=build_educational_story(approve_historical_demo(env))
        story['ranked_source_ids'].reverse()
        report=release_report(env,story)
        self.assertEqual(report['story']['state'],'MISSING_OR_SOURCE_MISMATCH')
        self.assertIn('authoritative_ranked_storyboard',report['critical_blockers'])
    def test_wrong_media_publish_flag_blocked(self):
        audit=video_audit({'status':'PRIVATE_HISTORICAL_PREMIUM_VIDEO_TECHNICAL_QA_PASSED',
                           'publish_enabled':True,'video_sha256':'b'*64})
        self.assertEqual(audit['state'],'UNVERIFIED_OR_UNSAFE')
        self.assertTrue(audit['publishing_enabled'])
    def test_never_mark_any_social_provider_enabled(self):
        report=release_report(source())
        self.assertEqual(set(report['social'].values()),{'OFF'})
        self.assertEqual(report['receipts']['received'],0)
        self.assertEqual(len(report['receipts']['missing_or_unverified']),len(EXTERNAL_RECEIPTS))

if __name__=='__main__':
    unittest.main()
