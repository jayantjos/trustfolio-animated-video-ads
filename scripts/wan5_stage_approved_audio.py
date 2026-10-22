"""Stage only a human-reviewed exact dialogue receipt, before GPU creation."""
import hashlib
import json
from pathlib import Path
from scripts import wan5_first_paid_controller as c
from scripts.wan5_gpu_worker import DIALOGUE

def main():
    meta=json.loads(Path('config/wan5_exact_audio_candidate.json').read_text())
    if meta.get('text')!=DIALOGUE or meta.get('listening_qa_passed') is not True:
        raise RuntimeError('HINDI_LISTENING_QA_NOT_APPROVED_NO_GPU')
    s3=c.make_s3()
    data=c.get_object(s3,meta['s3_key'],5*1024*1024)
    if not data or hashlib.sha256(data).hexdigest()!=meta['sha256']:
        raise RuntimeError('HINDI_AUDIO_READBACK_FAILED_NO_GPU')
    key='assets/audio/washing-machines/wan5-exact-dialogue.json'
    body=(json.dumps(meta,ensure_ascii=False,indent=2)+'\n').encode()
    s3.put_object(Bucket=c.VOLUME,Key=key,Body=body,ContentType='application/json')
    if c.get_object(s3,key,8192)!=body:
        raise RuntimeError('AUDIO_MANIFEST_READBACK_FAILED_NO_GPU')
    c.verify_hindi_inputs(s3)
    print('APPROVED_EXACT_HINDI_AUDIO_READBACK_VERIFIED_NO_GPU')
if __name__=='__main__':main()
