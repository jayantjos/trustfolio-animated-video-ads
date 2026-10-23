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
    # Read-only audio check before a GPU is ever considered; this does NOT
    # claim human listening approval or write approval manifests to S3.
    candidate=json.loads(Path('config/wan5_exact_audio_candidate.json').read_text())
    if candidate.get('text')!=w.DIALOGUE:
        raise RuntimeError('HINDI_CANDIDATE_DIALOGUE_CHANGED_NO_GPU')
    audio=c.get_object(s3,candidate['s3_key'],5*1024*1024)
    if not audio or hashlib.sha256(audio).hexdigest()!=candidate['sha256']:
        raise RuntimeError('HINDI_AUDIO_CANDIDATE_SHA256_MISMATCH_NO_GPU')
    (out/'hindi_candidate_sha256_verified.mp3').write_bytes(audio)
    technical_audio={'sha256_verified':True,'codec_decode':'PENDING_OFFLINE_DOCKER_CPU',
                     'listening_qa_passed':candidate.get('listening_qa_passed') is True}
    try:
        quote=c.check_cost_and_availability(os.environ['RUNPOD_API_KEY'])
        launch_eligible=True
    except c.PilotError as exc:
        if str(exc)!="SUPPORTED_ADA_GPU_NOT_ADVERTISED_NO_POD_CREATE":
            raise
        # A stock shortfall must block paid launch, not break model/audio
        # integrity QA. This is evidence-only: no Pod mutations.
        quote={'status':'SUPPORTED_GPU_UNAVAILABLE','reason':str(exc)}
        launch_eligible=False
        print('WAN5_APPROVED_GPU_STOCK=UNAVAILABLE_NO_GPU_CREATED',flush=True)
    pods=c.find_owned_pods(os.environ['RUNPOD_POD_WRITE_KEY'])
    if pods:raise RuntimeError('EXISTING_PILOT_POD_REQUIRES_REVIEW')
    report={'models':models,'tokenizer_readback':True,'character_sha256':w.IMAGE_SHA,
            'quote':quote,'hindi_audio_candidate':technical_audio,
            'owned_pods':0,'gpu_created':False,'published':False,
            'gpu_launch_eligible':launch_eligible}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
if __name__=='__main__':main()
