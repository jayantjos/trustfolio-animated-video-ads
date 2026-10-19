"""Original render-ready scenery props for 20 supported backend categories only."""
import json
from pathlib import Path
import re
import unittest
from trustfolio_video.educational import load_master,validate_master

ROOT=Path(__file__).resolve().parents[1]

class WorldMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master=load_master()
        cls.supported=validate_master(cls.master)
        cls.motion=json.loads((ROOT/'config/world_motion_20.json').read_text('utf-8'))
    def test_exactly_twenty_renderable_preset_ids(self):
        self.assertEqual(len(self.motion['enabled_worlds']),20)
        self.assertEqual(self.motion['unverified_future_slots'],10)
        self.assertFalse(self.motion['production_approved'])
        self.assertEqual({x['slug'] for x in self.motion['enabled_worlds']},
                         set(self.supported))
    def test_unique_world_kinds_with_valid_palettes(self):
        items=self.motion['enabled_worlds']
        self.assertEqual(len({x['kind'] for x in items}),20)
        for x in items:
            with self.subTest(slug=x['slug']):
                self.assertEqual(x['render_eligibility'],'BACKGROUND_QA_ONLY_NO_PRODUCTS')
                self.assertTrue(x['landmark'] and x['particles'] and x['character_action'])
                self.assertGreaterEqual(len(x['parallax']),3)
                for v in x['colors'].values():
                    self.assertRegex(v,r'^#[0-9a-fA-F]{6}$')
                self.assertEqual(x['asset_rights'].split(';')[0],
                                 'original-generated vector geometry')
    def test_premise_no_fabricated_product_data(self):
        for item in self.motion['enabled_worlds']:
            self.assertNotIn('product_id',item)
            self.assertNotIn('price_inr',item)
            self.assertEqual(len(item['visual_notes']),3)

if __name__=='__main__':
    unittest.main()
