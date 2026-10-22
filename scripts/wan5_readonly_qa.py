"""No Pod mutations: validate remote inputs and preserve evidence for CPU QA."""
import hashlib
import json
import os
from pathlib import Path
from scripts import wan5_first_paid_controller as c
from scripts import wan5_gpu_worker as w
from scripts.wan_storage_readiness import check_remote
from scripts.stage_wan5_tokenizer import TOKENIZER, MODEL_PREFIX

def main():
    out=Path('output/wan5-readonly');out.mkdir(parents=True,exist_ok=True)
    s3=c.make_s3()
    models=check_remote(json.loads(Path('config/wan_verified_model_manifest.json').read_text()),s3)
    c.verify_hero(s3)
    for name,(cap,digest) in TOKENIZER.items():
        data=c.get_object(s3,MODEL_PREFIX+name,cap)
        if not data or (digest and hashlib.sha256(data).hexdigest()!=digest):
            raise RuntimeError('TOKENIZER_READBACK_FAILED')
        dest=out/'tokenizer'/Path(name).name
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    quote=c.check_cost_and_availability(os.environ['RUNPOD_API_KEY'])
    pods=c.find_owned_pods(os.environ['RUNPOD_POD_WRITE_KEY'])
    if pods:raise RuntimeError('EXISTING_PILOT_POD_REQUIRES_REVIEW')
    report={'models':models,'tokenizer_readback':True,'character_sha256':w.IMAGE_SHA,
            'quote':quote,'owned_pods':0,'gpu_created':False,'published':False}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
if __name__=='__main__':main()
