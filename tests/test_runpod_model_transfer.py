import hashlib, io, json, unittest
from types import SimpleNamespace
from unittest.mock import patch
from scripts.runpod_model_transfer import HashReader, upload, select_file, Blocked, REPO, REV, PREFIX, BUCKET

class FakeInfo:
    sha=REV
    siblings=[
        SimpleNamespace(rfilename="config.json",size=7,lfs=None),
        SimpleNamespace(rfilename="a.safetensors",size=7,
                        lfs={"sha256":hashlib.sha256(b"content").hexdigest()})
    ]

class FakeResponse:
    def __init__(self,data):self.raw=io.BytesIO(data)
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def raise_for_status(self):pass

class FakeSession:
    def __init__(self,data):self.data=data
    def get(self,url,**kwargs):
        assert url.startswith("https://huggingface.co/")
        assert kwargs["stream"] is True
        return FakeResponse(self.data)

class FakeClient:
    def __init__(self):self.files={}
    def upload_fileobj(self,reader,bucket,key,Config=None):
        assert bucket==BUCKET
        self.files[key]=reader.read()
    def head_object(self,Bucket,Key):
        from botocore.exceptions import ClientError
        if Key not in self.files:
            raise ClientError({"Error":{"Code":"404","Message":"missing"}},"HeadObject")
        return {"ContentLength":len(self.files[Key])}
    def get_object(self,Bucket,Key):
        return {"ContentLength":len(self.files[Key]),"Body":io.BytesIO(self.files[Key])}

class StreamingTests(unittest.TestCase):
    def test_reject_invalid_files(self):
        for name in ("../evil.pth","images/image.png","README;.md"):
            with self.assertRaises(Blocked):select_file(FakeInfo,name)
    def test_pin_hash_for_weight(self):
        selected=select_file(FakeInfo,"a.safetensors")
        self.assertEqual(selected["lfs_sha256"],hashlib.sha256(b"content").hexdigest())
    def test_hashreader_streams_in_bytes(self):
        reader=HashReader(io.BytesIO(b"content"))
        self.assertEqual(reader.read(2),b"co")
        self.assertEqual(reader.read(10),b"ntent")
        self.assertEqual(reader.count,7)
        self.assertEqual(reader.sha.hexdigest(),hashlib.sha256(b"content").hexdigest())
    def test_upload_and_resume_without_overwrite(self):
        import boto3
        from botocore.exceptions import ClientError
        client=FakeClient()
        meta=select_file(FakeInfo,"a.safetensors")
        with patch("huggingface_hub.hf_hub_url",
            return_value="https://huggingface.co/"+REPO+"/resolve/"+REV+"/a.safetensors"):
            a=upload(meta,client,FakeSession(b"content"))
            self.assertEqual(a["status"],"UPLOADED_AND_VERIFIED")
            b=upload(meta,client,FakeSession(b"not used"))
            self.assertEqual(b["status"],"ALREADY_PRESENT_VERIFIED")
    def test_reject_wrong_source_checksum(self):
        client=FakeClient()
        meta=select_file(FakeInfo,"a.safetensors")
        with patch("huggingface_hub.hf_hub_url",
            return_value="https://huggingface.co/"+REPO+"/resolve/"+REV+"/a.safetensors"):
            with self.assertRaisesRegex(Blocked,"SOURCE_SHA256"):
                upload(meta,client,FakeSession(b"changed"))
    def test_reject_changed_revision(self):
        info=SimpleNamespace(sha="0"*40,siblings=FakeInfo.siblings)
        with self.assertRaises(Blocked):select_file(info,"config.json")

if __name__=="__main__":unittest.main()
