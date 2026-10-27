"""Persistent source-photo approval registry for unattended V6 campaigns.

When the product image URL/bytes or model changes, previous approvals do NOT carry over.
Never create auto-approvals from API title alone. This enables later budgets
to reuse explicitly reviewed photographic assets without repetitive review.
"""
import json
from pathlib import Path
from .live import check_receipt,DataBlocked
from .v6_live_campaign import check_photo_approvals

def resolve(receipt,pending,registry,*,now=None):
    check_receipt(receipt,now=now)
    if pending.get("source_receipt_sha256")!=receipt["snapshot_sha256"]:
        raise DataBlocked("Pending photo receipt mismatch")
    approved=dict(pending)
    entries=registry.get("approved_models") if isinstance(registry,dict) else None
    if not isinstance(entries,dict):raise DataBlocked("No approved photo source registry")
    rows=[]
    for product,p in zip(receipt["products"],pending["products"]):
        ref=entries.get(product["id"])
        if not isinstance(ref,dict) or ref.get("approved") is not True:
            raise DataBlocked("Model photo not yet approved: "+product["brand"]+" rank "+str(product["rank"]))
        if ref.get("source_image_url")!=product["image_url"] or (
                ref.get("image_sha256")!=p.get("image_sha256")):
            raise DataBlocked("Previously approved product photo changed; re-review rank "+str(product["rank"]))
        if not isinstance(ref.get("model_identifier"),str) or len(ref["model_identifier"])<3:
            raise DataBlocked("Approved product needs confirmed model identifier")
        row=dict(p)
        row["model_identity_ok"]=True
        row["product_photo_ok"]=True
        row["commercial_usage_ok"]=True
        row["approved_model_identifier"]=ref["model_identifier"]
        row["human_reviewed_evidence"]=ref.get("review_evidence_url","")
        rows.append(row)
    approved["products"]=rows
    approved["status"]="APPROVED_PHOTOS_EXACT_SHA256"
    approved["publication_approved"]=True
    check_photo_approvals(receipt,approved)
    return approved

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--receipt",required=True)
    p.add_argument("--pending",required=True)
    p.add_argument("--registry",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    read=lambda s:json.loads(Path(s).read_text(encoding="utf-8"))
    output=resolve(read(a.receipt),read(a.pending),read(a.registry))
    Path(a.output).write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("ALL_FIVE_EXACT_MODEL_PHOTOS_IN_APPROVED_SHA_REGISTRY=YES")
    print("CURRENT_LIVE_RECEIPT_REQUIRED=YES; META_POSTING_NOT_ATTEMPTED=YES")

if __name__=="__main__":main()
