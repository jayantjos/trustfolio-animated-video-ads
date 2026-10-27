"""No-network V6 release QA tests; never marks first campaign approved by default."""
import hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from trustfolio_flow.v6_release_qa import assess

def packet():
    p=[]
    for n in range(1,6):
        p.append({"rank":n,"id":f"{n:024x}","brand":"IFB","title":f"IFB 8kg Automatic #{n}",
                 "price_inr":"22000","image_url":f"https://m.media-amazon.com/images/I/item{n}.jpg",
                 "specifications":{"Capacity":"8 kg","Load Type":"Top Load",
                    "Energy Rating":"5 Star","Automation Type":"Fully Automatic"}})
    receipt={"category":"washing-machines","mode":"budget","brand":"","budget_inr":25000,
             "snapshot_sha256":"a"*64,"products":p}
    photos={"source_receipt_sha256":"a"*64,"products":[]}
    render={"source_snapshot_sha256":"a"*64,"rendered_product_ids":[x["id"] for x in p],
            "rendered_prices_inr":[x["price_inr"] for x in p]}
    voice={"source_snapshot_sha256":"a"*64,"lines":[
        "पहली पसंद, आई एफ बी, आठ किलो टॉप लोड।",
        "दूसरी पसंद, आई एफ बी, आठ किलो टॉप लोड।",
        "तीसरी पसंद, आई एफ बी, आठ किलो टॉप लोड।",
        "चौथी पसंद, आई एफ बी, आठ किलो टॉप लोड।",
        "पाँचवीं पसंद, आई एफ बी, आठ किलो टॉप लोड।"]}
    return receipt,photos,render,voice

class ReleaseQA(unittest.TestCase):
    def setup_patches(self):
        return [
            patch("trustfolio_flow.v6_release_qa.validate_receipt"),
            patch("trustfolio_flow.v6_hindi_voice_tts.validate_receipt"),
            patch("trustfolio_flow.v6_release_qa.check_photo_approvals"),
            patch("trustfolio_flow.v6_release_qa.caption_for",return_value={"caption":"actual caption"}),
            patch("trustfolio_flow.v6_release_qa.probe",return_value={
                "format":{"duration":"54.0"},"streams":[
                    {"codec_type":"video","width":720,"height":1280,"codec_name":"h264"},
                    {"codec_type":"audio","codec_name":"aac","sample_rate":"48000"}]}),
            patch("trustfolio_flow.v6_release_qa.loudness",return_value={"integrated_lufs":-16.0,"true_peak_dbfs":-1.5})
        ]
    def test_first_review_disabled_by_default(self):
        r,p,m,v=packet()
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/"v.mp4";file.write_bytes(b"synthetic bytes")
            ctx=self.setup_patches()
            with ctx[0],ctx[1],ctx[2],ctx[3],ctx[4],ctx[5]:
                result=assess(r,p,m,file,"actual caption",v,environ={})
            self.assertFalse(result["human_release_approved"])
            self.assertFalse(result["hindi_voice_qa_pass"])
            self.assertFalse(result["public_media_sha256_pass"])
            self.assertFalse(result["post_allowed"])
    def test_signed_template_and_voice_allows_later_gate_but_not_hosted(self):
        r,p,m,v=packet()
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/"v.mp4";file.write_bytes(b"synthetic bytes")
            ctx=self.setup_patches()
            with ctx[0],ctx[1],ctx[2],ctx[3],ctx[4],ctx[5]:
                result=assess(r,p,m,file,"actual caption",v,environ={
                  "TF_VIDEO_FIRST_REEL_QA_APPROVED":"true",
                  "TF_VIDEO_HINDI_VOICE_TEMPLATE_APPROVED":"true"})
            self.assertTrue(result["human_release_approved"])
            self.assertTrue(result["hindi_voice_qa_pass"])
            self.assertFalse(result["public_media_sha256_pass"])
            self.assertFalse(result["post_allowed"])
    def test_wrong_voice_receipt_rejected(self):
        r,p,m,v=packet();v["source_snapshot_sha256"]="b"*64
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/"v.mp4";file.write_bytes(b"x")
            ctx=self.setup_patches()
            with ctx[0],ctx[1],ctx[2],ctx[3],ctx[4],ctx[5]:
                with self.assertRaisesRegex(RuntimeError,"Hindi voice"):
                    assess(r,p,m,file,"actual caption",v,environ={})

if __name__=="__main__":unittest.main()
