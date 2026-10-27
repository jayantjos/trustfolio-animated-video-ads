import importlib.util
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
mod_path=Path(__file__).resolve().parents[1]/"scripts/mix_v6_hindi_voice.py"
spec=importlib.util.spec_from_file_location("mix_v6_voice",mod_path)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def metadata(duration=54):
    return {"format":{"duration":str(duration)},"streams":[{"codec_type":"video","width":720,"height":1280}]}

class HindiVoiceMixTests(unittest.TestCase):
    def test_requires_real_voice_input(self):
        with self.assertRaises(ValueError):
            mod.mix("/nonexistent/video.mp4","/nonexistent/voice.wav","/tmp/out.mp4")
    def test_14_second_product_voice_and_story_ducking(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/"a.mp4";b=Path(td)/"b.wav";out=Path(td)/"o.mp4"
            a.write_bytes(b"test");b.write_bytes(b"test")
            with patch.object(mod,"probe",side_effect=[metadata(54),metadata(13),metadata(54)]),patch.object(mod.subprocess,"run") as runner:
                mod.mix(a,b,out)
                argv=runner.call_args.args[0]
                self.assertIn("-c:v",argv)
                self.assertEqual(argv[argv.index("-c:v")+1],"copy")
                graph=argv[argv.index("-filter_complex")+1]
                self.assertIn("between(t,31.95,46.05)",graph)
                self.assertIn("adelay=32000:all=1",graph)
                self.assertIn("loudnorm=I=-16",graph)
                runner.assert_called_once()
    def test_reject_short_speech(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/"a.mp4";b=Path(td)/"b.wav";a.touch();b.touch()
            with patch.object(mod,"probe",side_effect=[metadata(54),metadata(5)]):
                with self.assertRaises(ValueError):mod.mix(a,b,Path(td)/"out.mp4")
    def test_reject_wrong_video_dimensions(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/"a.mp4";b=Path(td)/"b.wav";a.touch();b.touch()
            bad=metadata(54);bad["streams"][0]["height"]=720
            with patch.object(mod,"probe",side_effect=[bad,metadata(13)]):
                with self.assertRaises(ValueError):mod.mix(a,b,Path(td)/"out.mp4")
if __name__=="__main__":unittest.main()
