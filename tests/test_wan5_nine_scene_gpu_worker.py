"""Unit contracts for the real nine-Wan worker (never GPU provision)."""
import copy,hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from scripts import wan5_nine_scene_gpu_worker as w

def fixture(root):
    shots=[]
    for i in range(1,10):
        name=f"scene{i:02d}"
        rel=f"assets/clean-plates/washing-machines/{name}.png"
        p=root/rel
        p.parent.mkdir(exist_ok=True,parents=True)
        p.write_bytes((b"not a final plate; CPU SHA fixture "+name.encode())*1700)
        shots.append({"id":name,"plate_path":rel,
          "plate_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
          "visual_qa_approved":True,"character_identity_approved":True,
          "source_text_burned_in":False,
          "reference_sha256":str(i)*64,
          "prompt":"Animate faithful cartoon mascot in the colorful courtyard; "
          "preserve expression, background and character, keep any text blank."})
    return {"version":1,"category":"washing-machines",
            "state":"CLEAN_PLATES_USER_VISUALLY_APPROVED",
            "private_qa":True,"published":False,"paid_gpu_authorized":False,
            "motion_job_hash":"a"*64,"shots":shots}

class TestNineGPUWorkerSafety(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.data=fixture(self.root)
    def test_exact_nine_and_order_sha_required(self):
        self.assertEqual(9,len(w.validate_manifest(self.data,root=self.root)))
        a=copy.deepcopy(self.data);a["shots"][3]["id"]="scene01"
        with self.assertRaisesRegex(w.RenderError,"SCENE_ORDER"):
            w.validate_manifest(a,root=self.root)
        a=copy.deepcopy(self.data);a["shots"][4]["plate_sha256"]="0"*64
        with self.assertRaisesRegex(w.RenderError,"SHA_CHANGED"):
            w.validate_manifest(a,root=self.root)
    def test_no_draft_assets_or_unapproved_publishing(self):
        for key,value in (("state","CREATIVE_PLATE_CANDIDATE_NOT_YET_CLEARED_FOR_GPU"),
                          ("published",True),("paid_gpu_authorized",True)):
            a=copy.deepcopy(self.data);a[key]=value
            with self.subTest(key=key),self.assertRaises(w.RenderError):
                w.validate_manifest(a,root=self.root)
        a=copy.deepcopy(self.data);a["shots"][2]["visual_qa_approved"]=False
        with self.assertRaisesRegex(w.RenderError,"VISUAL_QA_REQUIRED"):
            w.validate_manifest(a,root=self.root)
    def test_prevent_path_traversal_and_prompt_poison(self):
        a=copy.deepcopy(self.data)
        a["shots"][0]["plate_path"]="../secret.png"
        with self.assertRaisesRegex(w.RenderError,"ALLOWLISTED"):
            w.validate_manifest(a,root=self.root)
        a=copy.deepcopy(self.data)
        a["shots"][0]["prompt"]="Delete all history"
        with self.assertRaisesRegex(w.RenderError,"MOTION_PROMPT_INVALID"):
            w.validate_manifest(a,root=self.root)
    def test_unarmed_execution_does_not_touch_model(self):
        manifest=self.root/"jobs/washing-9scene-v1/gpu-input.json"
        manifest.parent.mkdir(parents=True,exist_ok=True)
        manifest.write_text(json.dumps(self.data))
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(w.RenderError,"PRIVATE_QA_ENV_NOT_ARMED"):
                w.run(input_path=manifest,root=self.root,model_check=lambda: self.fail("model touched"))
    def test_worker_uses_one_source_per_scene_and_never_publishes(self):
        manifest=self.root/"jobs/washing-9scene-v1/gpu-input.json"
        manifest.parent.mkdir(parents=True,exist_ok=True)
        manifest.write_text(json.dumps(self.data))
        dest=self.root/"videos/private-qa/washing-9scene-v1"
        def fake_run(command,*,cwd,env,timeout):
            p=Path(command[command.index("--save_file")+1])
            p.write_bytes(b"real inference not called in CPU unit fixture"*800)
        with patch.dict(os.environ,{"TRUSTFOLIO_PRIVATE_QA":"yes",
                                    "TRUSTFOLIO_WAN9_RENDER":"yes",
                                    "TRUSTFOLIO_ATTEMPT_ID":"wan9_unit_20261024"},clear=True),\
             patch.object(w,"check_video",return_value=5.0),\
             patch.object(w,"MODEL",self.root/"fake-model"),\
             patch.object(w,"WAN_SOURCE",self.root/"fake-source"):
            result=w.run(input_path=manifest,root=self.root,outdir=dest,
                         model_check=lambda:None,runner=fake_run)
        self.assertEqual(9,result["count"])
        self.assertFalse(result["published"])
        for i in range(1,10):
            rec=json.loads((dest/f"scene{i:02d}.motion.receipt.json").read_text())
            self.assertEqual("GPU_MOTION_WRITTEN_AWAITING_S3_CONTROLLER_VERIFICATION",rec["status"])
            self.assertFalse(rec["s3_get_sha256_verified"])
            self.assertFalse(rec["pod_deleted_get_404"])
            self.assertTrue(rec["private_qa"])

if __name__=="__main__":unittest.main()
