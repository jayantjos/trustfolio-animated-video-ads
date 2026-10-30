"""Summarize readiness without faking media, approvals, or platform receipts."""
import argparse,json
from pathlib import Path
def report(folder):
    folder=Path(folder)
    result={"live_fetch":"MISSING","images":"MISSING","dynamic_voice":"MISSING","lip_sync":"MISSING","render":"MISSING","facebook":"NOT_PUBLISHED","instagram":"NOT_PUBLISHED","publish_allowed":False}
    live=folder/"live.json"
    campaign=folder/"campaign.json"
    approval=folder/"photo_approved.json"
    qa=folder/"release_qa.json"
    if live.is_file():
        data=json.loads(live.read_text())
        result["live_fetch"]="RECEIPT_PRESENT" if data.get("source")=="trustfolio_live_api" and len(data.get("products",[]))==5 else "INVALID_RECEIPT"
    if campaign.is_file() and json.loads(campaign.read_text()).get("status")=="DATA_READY_NOT_PUBLISHABLE":
        result["live_fetch"]="DATA_CONTRACT_PASS"
    if approval.is_file():
        a=json.loads(approval.read_text())
        result["images"]="APPROVED" if a.get("publication_approved") is True and len(a.get("products",[]))==5 else "NOT_APPROVED"
    if qa.is_file():
        a=json.loads(qa.read_text())
        for key,target in (("dynamic_voice","voice_qa_pass"),("lip_sync","lip_sync_qa_pass"),("render","frame_qa_pass")):
            result[key]="PASS" if a.get(target) is True else "NOT_APPROVED"
    result["blockers"]=[x for x in ("live_fetch","images","dynamic_voice","lip_sync","render") if result[x] not in ("DATA_CONTRACT_PASS","APPROVED","PASS")]
    return result
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--folder",default="handoff")
    a=p.parse_args()
    out=report(a.folder)
    path=Path(a.folder)/"preflight_report.json";path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2))
if __name__=="__main__":main()
