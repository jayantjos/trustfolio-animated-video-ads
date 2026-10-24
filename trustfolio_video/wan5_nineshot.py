"""WAN2.2 multi-scene rendering contract: plan only, never starts a paid GPU.

All text and product photos are downstream verified compositing layers, not
in-model generations. Reference storyboard PNGs contain obsolete SAMPLE
brands/prices and must never be supplied as live factual end frames.
"""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib,json,re
from pathlib import Path

from .contract import Blocked

TIMES=((0,3),(3,6),(6,10),(10,14),(14,18),(18,22),(22,26),(26,28),(28,30))
KINDS=("hook","intro","product","product","product","product","product","ranking","cta")
EXPECTED_RANK=(None,None,5,4,3,2,1,None,None)
SCENE_MOTIONS=(
    "Animate the same approved woman in pink kurta as she reacts to a huge pile of laundry. Eyebrows rise, eyes widen, hands go to head, hair and clothing subtly sway. Match the initial approved character identity precisely.",
    "Five happy anonymous washing-machine mascots bounce into a tropical courtyard. They have arms, faces and feet, with natural staggered entrance and subtle camera tracking. Keep them UNBRANDED.",
    "A cheerful neutral washing machine mascot makes a confident thumbs-up and laughs gently. Smooth cartoon expression, subtle body sway, steady product silhouette.",
    "A cute washing machine mascot winks, blinks, smiles and gestures to a laundry basket. Continuous natural acting and stable machine body.",
    "A cheerful washing-machine mascot waves with a sudsy bubble effect. Gentle bubble motion, eye movement and consistent panel geometry.",
    "A confident washing-machine mascot smiles and turns slightly, with a thumbs-up gesture and polished metallic reflections.",
    "A triumphant washing-machine mascot celebrates with a floating crown and tiny cape motion. Eyes brighten and arms lift while body stays consistent.",
    "Five anonymous neutral washing-machine mascots cheer on numbered podiums. Gentle movement, mild parallax, no brand or price lettering.",
    "Animate the same approved pink-kurta woman as she smiles, lifts a phone toward camera, points at a blank clean phone screen and looks confidently at viewers."
)
NO_TEXT_SUFFIX=(" No legible text, no logos, no price labels, no rank numbers,"
                " no watermark, no new people or fingers, no morphing,"
                " do not invent product features. Keep live product photographs"
                " and all factual information OUTSIDE the generated moving layer.")

def verified_plan(story, *, photo_mode="separate_unaltered", skip_reused_hook=False):
    if story.get("schema_version")!=2 or story.get("category")!="washing-machines":
        raise Blocked("Washing-machine approved v2 contract required")
    if story.get("duration_seconds")!=30 or story.get("fps")!=24 or story.get("size")!=[1080,1920]:
        raise Blocked("Video duration, fps or geometry wrong")
    if (story.get("publishing_enabled") is not False
        or story.get("runpod_gpu_launch_approved") is not False
        or story.get("live_price_api_completed") is not True):
        raise Blocked("Rendering cannot bypass source or publication gate")
    if photo_mode!="separate_unaltered":
        raise Blocked("Never bake altered factual product photos into AI animation")
    if not isinstance(story.get("scenes"),list) or len(story["scenes"])!=9:
        raise Blocked("Nine dynamic scenes mandatory")
    if not re.fullmatch("[0-9a-f]{64}",str(story.get("campaign_id",""))):
        raise Blocked("Source campaign digest missing")
    if not re.fullmatch("[0-9a-f]{64}",str(story.get("source_sha256",""))):
        raise Blocked("Source snapshot hash missing")
    try:
        observed=datetime.fromisoformat(story["data_observed_at"].replace("Z","+00:00"))
        now=datetime.now(timezone.utc)
        if observed.tzinfo is None or not -60 <= (now-observed).total_seconds() <= 900:
            raise ValueError()
    except (KeyError,ValueError,TypeError):
        raise Blocked("Price snapshot stale; rerun backend Top5 and POST live-prices") from None
    shots=[]
    for idx,(times,kind,rank) in enumerate(zip(TIMES,KINDS,EXPECTED_RANK)):
        scene=story["scenes"][idx]
        if (scene.get("scene")!=f"scene{idx+1:02d}"
            or (scene.get("start"),scene.get("end"))!=times
            or scene.get("kind")!=kind
            or scene.get("reference_only") is not True
            or scene.get("must_erase_all_baked_text_and_products") is not True):
            raise Blocked("Story and verified source artwork differ at "+str(idx+1))
        if not re.fullmatch("[a-f0-9]{64}",str(scene.get("reference_sha256",""))):
            raise Blocked("Storyboard image hash invalid")
        shot={"scene_id":scene["scene"],"start":times[0],"end":times[1],
              "seconds":times[1]-times[0],"generated_base_seconds":5,
              "source_storyboard_sha256":scene["reference_sha256"],
              "image_source_policy":"CLEAN_CHARACTER_PLATE_ONLY_NO_BAKED_REFERENCE_TEXT",
              "motion_prompt":SCENE_MOTIONS[idx]+NO_TEXT_SUFFIX,
              "post_render_overlay_policy":"UNALTERED_SOURCE_PHOTO_AND_VERIFIED_CURRENT_PRICES",
              "audio_policy":"SYNTH_HINDI_NEEDS_HUMAN_LISTENING_QA",
              "face_lipsync_status":"NOT_VERIFIED",
              "expected_clip_name":scene["scene"]+".motion.mp4",
              "gpu_output_verified":False}
        if rank is not None:
            d=scene.get("dynamic",{})
            if d.get("rank")!=rank or d.get("price_source") not in ("website_live_price_api","website_catalog"):
                raise Blocked("Rank source missing in scene "+str(idx+1))
            if not d.get("unaltered_photo_url") or not d.get("source_product_id"):
                raise Blocked("Product original photo missing")
            if d.get("price_source")=="website_catalog" and not str(d.get("price_label","")).startswith("Catalog fallback"):
                raise Blocked("Catalog price must be explicitly disclosed")
            shot["dynamic_overlay_source_id"]=d["source_product_id"]
            shot["dynamic_rank"]=rank
            shot["dynamic_price_source"]=d["price_source"]
        if kind=="cta" and scene.get("url")!="https://www.trustfolio.in":
            raise Blocked("Required CTA not present")
        shots.append(shot)
    # Motion is intentionally DATA-INDEPENDENT: scene personas and expressions
    # can be reused when budget, brand, actual product ID or prices change.
    # Never make GPU re-render a story because a seller changed a price.
    visual_core=[{key:shot[key] for key in ("scene_id","start","end","seconds",
                   "generated_base_seconds","source_storyboard_sha256",
                   "motion_prompt","image_source_policy","post_render_overlay_policy")}
                 for shot in shots]
    digest=hashlib.sha256(json.dumps({"model":"Wan2.2-TI2V-5B",
        "visual_core":visual_core},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return {"version":1,"kind":"RUNPOD_GPU_RENDER_PLAN_ONLY",
            "campaign_id":story["campaign_id"],
            "source_sha256":story["source_sha256"],
            "input_live_snapshot_observed_at":story["data_observed_at"],
            "motion_job_hash":digest,"total_seconds":30,
            "shots":shots,"gpu_segments_required":9,
            "new_paid_gpu_authorized":False,"gpu_pods_created":0,
            "published":False,"complete_motion_video_exists":False,
            "requirements":["Nine genuine GPU-verified motion clips with receipts",
                            "Human-reviewed Hindi dialogue for all nine scenes",
                            "Independent female lead lip-sync visual QA",
                            "Compose source-accurate dynamic overlays only after I2V",
                            "Fresh real price recheck before publication",
                            "Current GPU price and explicit new spending cap",
                            "Provider TTL independent reaper and pod deletion receipt"]}
