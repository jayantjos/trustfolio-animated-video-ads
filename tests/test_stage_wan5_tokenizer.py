import io
import json
import unittest
from unittest.mock import patch
from scripts import stage_wan5_tokenizer as t

class DummyResponse:
    def __init__(self,data): self.stream=io.BytesIO(data)
    def __enter__(self):return self
    def __exit__(self,*args):self.stream.close()
    def read(self,n):return self.stream.read(n)

class FakeS3:
    def __init__(self): self.data={};self.writes=[]
    def get_object(self,*,Bucket,Key):
        if Key not in self.data:
            e=Exception("NotFound");e.response={"Error":{"Code":"NoSuchKey"}};raise e
        b=self.data[Key]
        return {"ContentLength":len(b),"Body":io.BytesIO(b)}
    def put_object(self,*,Bucket,Key,Body,ContentType):
        self.data[Key]=Body;self.writes.append(Key)

class Tests(unittest.TestCase):
    def test_only_allow_four_official_files(self):
        self.assertEqual(set(t.TOKENIZER),{
            "spiece.model","tokenizer.json",
            "special_tokens_map.json","tokenizer_config.json"})
        self.assertIn("921dbaf3f1674a56f47e83fb80a34bac8a8f203e",t.MODEL_PREFIX)
        self.assertEqual(t.BUCKET,"1bch597yrz")
    def test_unknown_file_refused_before_network(self):
        with self.assertRaisesRegex(ValueError,"UNAPPROVED"):
            t.download_verified("../trick",1024,None)
    def test_sha256_rejects_mutation(self):
        with patch.object(t,"urlopen",return_value=DummyResponse(b"wrong")):
            with self.assertRaisesRegex(RuntimeError,"SHA256_MISMATCH"):
                t.download_verified("spiece.model",50,"a"*64)
    def test_valid_json_requires_dictionary(self):
        with patch.object(t,"urlopen",return_value=DummyResponse(b"[]")):
            with self.assertRaisesRegex(RuntimeError,"BAD_TOKENIZER_JSON"):
                t.download_verified("tokenizer_config.json",100,None)
    def test_stage_verifies_readback_without_network_or_gpu(self):
        fake=FakeS3()
        test_values={
            "spiece.model":b"testsp",
            "tokenizer.json":b'{"version":"1"}',
            "special_tokens_map.json":b'{"tokens":[]}',
            "tokenizer_config.json":b'{"a":1}'}
        def get(name,limit,sha):return test_values[name],"a"*64
        with patch.object(t,"download_verified",side_effect=get):
            result=t.stage(fake)
            self.assertEqual(len(result),4)
            self.assertEqual(len(fake.writes),4)
            self.assertEqual(t.stage(fake)[0]["status"],"PRESENT_VERIFIED")
    def test_rejects_existing_mismatch_without_overwrite(self):
        fake=FakeS3()
        fake.data[t.MODEL_PREFIX+"tokenizer.json"]=b"different"
        with patch.object(t,"download_verified",return_value=(b"approved","0"*64)):
            with self.assertRaisesRegex(RuntimeError,"REFUSE_OVERWRITE"):
                t.stage(fake)
        self.assertEqual(fake.writes,[])
if __name__=="__main__":unittest.main()
