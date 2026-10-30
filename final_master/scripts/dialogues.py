"""Dynamic Hindi dialogue from verified live receipt only.
Does not fake original character identity, speech or lipsync.
"""
import argparse,json,re
from pathlib import Path
from trustfolio_flow.live import check_receipt
from trustfolio_flow.v6_live_campaign import source_specs

ORD=("पहली","दूसरी","तीसरी","चौथी","पाँचवीं")
LABEL={"Capacity":"क्षमता","Load Type":"लोड प्रकार","Energy Rating":"ऊर्जा रेटिंग","Spin Speed":"स्पिन स्पीड",
       "Automation Type":"ऑटोमेशन","Washing Machine Type":"वॉशिंग मशीन प्रकार",
       "Wash Programs":"वॉश प्रोग्राम","In-built Heater":"इन-बिल्ट हीटर",
       "Motor Type":"मोटर","Water Rating":"पानी की रेटिंग"}
def speech_value(v):
    v=str(v).strip()
    v=re.sub(r"\bkg\b","किलो",v,flags=re.I)
    v=re.sub(r"\brpm\b","आर पी एम",v,flags=re.I)
    v=re.sub(r"\bstar\b","स्टार",v,flags=re.I)
    return v
def build(receipt):
    check_receipt(receipt)
    lines=[]
    for p in receipt["products"]:
        specs=source_specs(p)
        reason="। ".join(LABEL[x["label"]]+" "+speech_value(x["value"]) for x in specs)
        brand=str(p["brand"]).strip()
        lines.append({"rank":p["rank"],"product_id":p["id"],
          "text":f"{ORD[p['rank']-1]} पसंद {brand}। {reason}।",
          "specifications":specs,"voice_identity":"UNVERIFIED_CHARACTER_REFERENCE",
          "audio_generated":False,"lipsync_generated":False})
    return {"snapshot_sha256":receipt["snapshot_sha256"],"category":receipt["category"],
      "mode":receipt["mode"],"budget_inr":receipt["budget_inr"],"brand":receipt["brand"],
      "product_lines":lines,"original_scene_audio_preserve":True,"release_authorized":False}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--receipt",required=True);p.add_argument("--out",required=True)
    a=p.parse_args()
    payload=build(json.loads(Path(a.receipt).read_text(encoding="utf8")))
    dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("DYNAMIC_FIVE_SOURCE_BACKED_DIALOGUES_READY; VOICE_AND_LIPSYNC_NOT_GENERATED")
if __name__=="__main__":main()
