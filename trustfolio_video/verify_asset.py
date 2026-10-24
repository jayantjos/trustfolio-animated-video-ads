"""Reject wrong/altered canonical character art before GPU spending."""
import argparse
import json
from pathlib import Path
from .fixed_pilot import verify_hero

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--image",required=True)
    p.add_argument("--pilot",required=True)
    a=p.parse_args()
    wanted=json.loads(Path(a.pilot).read_text())["canonical_image_sha256"]
    verify_hero(a.image,wanted)
    print("CANONICAL_HERO_SHA256_VERIFIED")
if __name__=="__main__":
    main()
