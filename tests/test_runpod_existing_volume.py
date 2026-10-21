import hashlib, json, tempfile, unittest
from pathlib import Path
from urllib.error import HTTPError
from scripts.runpod_existing_volume import verify, VolumeError
from scripts.runpod_s3_smoke import check_s3

class Response:
    status=200
    def __init__(self,payload):self.payload=payload
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,n=-1):return json.dumps(self.payload).encode()

class ExistingStorageTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/"test.json"
        self.cfg={"id":"1bch597yrz","name":"trustfolio-wan-models-v1",
          "size_gb":100,"datacenter":"EU-RO-1","tier":"STANDARD"}
        self.path.write_text(json.dumps(self.cfg))
    def test_verified_volume_is_get_only(self):
        def get(req,timeout):
            self.assertEqual(req.get_method(),"GET")
            self.assertTrue(req.full_url.endswith("/1bch597yrz"))
            return Response({"id":"1bch597yrz","name":"trustfolio-wan-models-v1",
                 "size":100,"dataCenter":"EU-RO-1","type":"STANDARD"})
        out=verify(self.path,"fake-key",opener=get)
        self.assertEqual(out["status"],"VERIFIED_EXISTING_VOLUME")
        self.assertFalse(out["new_volume_created"])
    def test_wrong_volume_size_blocks(self):
        def get(req,timeout):
            return Response({"id":"1bch597yrz","name":"trustfolio-wan-models-v1",
                 "size":200,"dataCenter":"EU-RO-1","type":"STANDARD"})
        with self.assertRaisesRegex(VolumeError,"SIZE"):
            verify(self.path,"fake-key",opener=get)
    def test_missing_key_never_networks(self):
        with self.assertRaises(VolumeError):
            verify(self.path,"",opener=lambda *a,**k:self.fail("network"))
    def test_s3_without_keys_is_not_connected(self):
        self.assertEqual(check_s3("1bch597yrz","https://s3api-eu-ro-1.runpod.io","",""),
                         "S3_NOT_CONFIGURED")
    def test_s3_uses_list_only(self):
        class Client:
            def list_objects_v2(self,**kwargs):
                self.call=kwargs
                return {"ResponseMetadata":{"HTTPStatusCode":200},"KeyCount":0}
        c=Client()
        status=check_s3("1bch597yrz","https://s3api-eu-ro-1.runpod.io",
                        "fake","fake",client_factory=lambda:c)
        self.assertEqual(status,"S3_CONNECTED_READ_ONLY")
        self.assertEqual(c.call,{"Bucket":"1bch597yrz","MaxKeys":1})

if __name__=="__main__":unittest.main()
