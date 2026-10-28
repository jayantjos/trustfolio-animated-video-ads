"""Offline QA: specs never shake, provider voice ID fixed and all speech unsped."""
import base64,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from trustfolio_flow import v10_fixed_voice as voice
from trustfolio_flow import v10_stable_specs as layer

PROFILE={"provider":"inworld","model_id":"inworld-tts-2","voice_id":"Ashley",
         "language":"hi","approved_for_hindi_narration":False}

def receipt():
    titles=["IFB 8 kg Top Load In-built Heater","Samsung 8 kg Wi-Fi Inverter",
            "Bosch 7 kg Top Load 680 RPM","IFB 8 kg AI DeepClean","LG 9 kg Steam Heater"]
    brands=["IFB","Samsung","Bosch","IFB","LG"]
    p=[]
    for i,(brand,title) in enumerate(zip(brands,titles),1):
        kg="7" if i==3 else "9" if i==5 else "8"
        p.append({"id":f"{i:024x}","rank":i,"brand":brand,"title":title,
           "price_inr":str(20000+i),"specifications":{
               "Capacity":kg+" kg","Load Type":"Top Load","Energy Rating":"5 Star",
               "Automation Type":"Fully Automatic",**({"Spin Speed":"680 RPM"} if i==3 else {})}})
    return {"category":"washing-machines","mode":"budget","budget_inr":25000,
            "snapshot_sha256":"a"*64,"products":p}

class V10(unittest.TestCase):
    def test_voice_model_profile_fixed(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/"voice.json";f.write_text(json.dumps(PROFILE))
            self.assertEqual(voice.load_profile(f)["voice_id"],"Ashley")
    def test_unknown_model_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/"voice.json";f.write_text(json.dumps({**PROFILE,"provider":"other"}))
            with self.assertRaises(ValueError):voice.load_profile(f)
    def test_unapproved_voice_prevents_paid_call(self):
        with self.assertRaisesRegex(RuntimeError,"not been approved"):
            voice.request_mp3("पाँच स्टार",PROFILE,"some-secret",
                opener=lambda *a,**kw:None)
    def test_missing_api_key_prevents_call(self):
        with self.assertRaisesRegex(RuntimeError,"missing"):
            voice.request_mp3("पाँच स्टार",{**PROFILE,"approved_for_hindi_narration":True},"")
    def test_real_model_and_voice_id_sent_once_without_secret_in_payload(self):
        class Fake:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):return None
            def read(self,limit):return json.dumps({"audioContent":base64.b64encode(b"ID3"+b"\0"*5000).decode()}).encode()
        calls=[]
        def opener(req,timeout):
            calls.append(json.loads(req.data.decode()))
            return Fake()
        audio=voice.request_mp3("सैमसंग आठ किलो",
               {**PROFILE,"approved_for_hindi_narration":True},"protected-secret",opener=opener)
        self.assertTrue(audio.startswith(b"ID3"))
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0]["voiceId"],"Ashley")
        self.assertEqual(calls[0]["modelId"],"inworld-tts-2")
        self.assertNotIn("protected-secret",json.dumps(calls[0]))
    def test_five_dynamic_product_reasons(self):
        with patch.object(voice,"validate_receipt"):
            lines=voice.voice_lines(receipt())
        self.assertEqual(len(lines),5)
        for word,i in [("हीटर",0),("वाई-फ़ाई",1),("स्पिन स्पीड",2),
                       ("डीप क्लीन",3),("स्टीम",4)]:
            self.assertIn(word,lines[i])
    def test_missing_spec_cannot_generate_fake_claim(self):
        data=receipt();data["products"][2]["specifications"]["Capacity"]="unknown"
        with patch.object(voice,"validate_receipt"):
            with self.assertRaises(ValueError):voice.voice_lines(data)
    def test_stable_layers_five_real_source_fields(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(layer,"validate_receipt"):
                files=layer.make_layers(receipt(),td)
            self.assertEqual(len(files),3)
            for path in files:
                self.assertEqual(Image.open(path).size,(720,1280))
            self.assertGreater(Image.open(files[1]).getchannel("A").getbbox()[3],500)
    def test_no_oscillating_crop_code(self):
        import inspect
        src=inspect.getsource(layer.encode_still_without_shake)
        self.assertNotIn("sin(",src)
        self.assertNotIn("cos(",src)
        self.assertNotIn("crop=",src)
        self.assertNotIn("zoompan=",src)
    def test_invalid_still_duration_refused(self):
        with self.assertRaises(ValueError):
            layer.encode_still_without_shake("fake.png",7,"out.mp4")
    def test_mixing_never_speedup_narration(self):
        import inspect
        self.assertNotIn("atempo=",inspect.getsource(voice.mix))
        with patch.object(voice,"duration",side_effect=[80,50]):
            with self.assertRaises(RuntimeError):
                voice.mix("old.mp4","50s.wav","out.mp4")

if __name__=="__main__":unittest.main()
