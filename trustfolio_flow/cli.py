"""Build premium Google Flow editable clip pack and assemble ONLY approved edits."""
import argparse
import json
from pathlib import Path
from .live import fetch_live, check_receipt, DataBlocked
from .clip_ops import extract_originals, assemble
from .flow_prompts import write_prompts
from .images import fetch_ingredients


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    f=sub.add_parser('fetch-live',help='GET Top5 then POST live-prices once; no retries, no publishing')
    f.add_argument('--category',default='washing-machines')
    f.add_argument('--budget',required=True,type=int)
    f.add_argument('--mode',choices=['budget','brand_budget','comparison'],default='budget')
    f.add_argument('--brand',default='')
    f.add_argument('--output',required=True)
    h=sub.add_parser('prepare',help='Generate Flow prompts/images from a verified fresh receipt and master')
    h.add_argument('--receipt',required=True);h.add_argument('--master',required=True)
    h.add_argument('--output',required=True);h.add_argument('--download-images',action='store_true')
    a=sub.add_parser('assemble',help='Replace SHA256-approved Flow edits and concatenate 40s MP4')
    for key in ('master','handoff','replacements','approvals','output'):
        a.add_argument('--'+key.replace('_','-'),required=True)
    a.add_argument('--allow-partial',action='store_true',help='For local preview only, never a final creative')
    args=p.parse_args()
    try:
        if args.command=='fetch-live':
            receipt=fetch_live(args.category,args.budget,args.mode,args.brand)
            file=Path(args.output);file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print('TRUSTFOLIO_LIVE_RECEIPT_VERIFIED=YES')
            print('FIVE_VERIFIED_PRODUCTS=5')
            print('NO_AUTOMATIC_PUBLISH=YES')
        elif args.command=='prepare':
            receipt=json.loads(Path(args.receipt).read_text(encoding='utf-8'))
            check_receipt(receipt)
            write_prompts(receipt,args.output)
            extract_originals(args.master,args.output)
            if args.download_images:
                fetch_ingredients(receipt,Path(args.output)/'product_images')
            print('FLOW_EDIT_PROMPTS_PREPARED=6')
            print('ORIGINAL_4S_CLIPS_EXTRACTED=10')
            print('FLOW_GENERATION_NOT_AUTOMATED=YES')
        else:
            result=assemble(args.master,args.handoff,args.replacements,args.approvals,args.output,require_all=not args.allow_partial)
            print(json.dumps(result,indent=2))
    except (DataBlocked,ValueError,OSError) as e:
        p.error(str(e))

if __name__=='__main__':main()
