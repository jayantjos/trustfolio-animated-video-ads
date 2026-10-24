"""Reference-identity lock for nine live data-independent animation prompts.

Static tests cannot prove actual visual identity; human image/video QA remains mandatory.
"""
import unittest
from trustfolio_video.wan5_nineshot import SCENE_MOTIONS,NO_TEXT_SUFFIX,TIMES,EXPECTED_RANK

class FixedAnimatedWorldFidelity(unittest.TestCase):
    def test_nine_original_character_expression_patterns_and_camera_world(self):
        required={
           1:("pink embroidered kurta","wicker basket","palms press her head"),
           2:("FIVE","walking together","bougainvillea"),
           3:("SUNGLASSES","THUMBS-UP","CHARCOAL"),
           4:("WINKING","pointing","heart"),
           5:("water splashes","soap foam","bubbles"),
           6:("metallic SILVER","round chrome door","thumbs-up"),
           7:("CROWN","cape","triumphant"),
           8:("FIVE","podium","crown-and-cape"),
           9:("EXACT SAME","smartphone","BLANK WHITE SCREEN")
        }
        self.assertEqual(9,len(SCENE_MOTIONS))
        self.assertEqual([5,4,3,2,1],list(EXPECTED_RANK[2:7]))
        self.assertEqual(30,TIMES[-1][1])
        for i,terms in required.items():
            with self.subTest(scene=i):
                prompt=SCENE_MOTIONS[i-1]
                for term in terms:
                    self.assertIn(term.casefold(),prompt.casefold())
                self.assertTrue(80<len(prompt+NO_TEXT_SUFFIX)<1600)
        # The lead MUST be the exact same person across the emotional hook and CTA.
        self.assertIn("pink embroidered kurta",SCENE_MOTIONS[0])
        self.assertIn("pink embroidered kurta",SCENE_MOTIONS[8])
        # No hallucinated price or accidental concrete brand fixed into the motion.
        for scene in SCENE_MOTIONS:
            self.assertNotIn("₹",scene)
            self.assertNotIn("28,990",scene)
            self.assertNotIn("Samsung",scene)
            self.assertNotIn("LG!",scene)
            self.assertNotIn("Haier",scene)
            self.assertNotIn("Bosch",scene)
            self.assertNotIn("IFB",scene)
    def test_text_prices_remain_post_rendered_layers(self):
        for phrase in ("no logos","no price labels","no rank numbers",
                       "no morphing"):
            self.assertIn(phrase,NO_TEXT_SUFFIX)
if __name__=="__main__": unittest.main()
