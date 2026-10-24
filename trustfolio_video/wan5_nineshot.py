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
    # 1 / 00:00-00:03. Character exactness outranks stylistic improvisation.
    "Animate the SAME premium 3D cartoon Indian woman with very long wavy dark brown hair, pink embroidered kurta and gold hoop earrings in the SAME sunny Indian tropical laundry-street courtyard. Camera medium-wide: she stays LEFT, huge wicker basket piled with blue yellow red and white clothes stays RIGHT. Both palms press her head, eyes widen and dart to laundry, eyebrows arch with alarm, jaw opens, a natural startled blink and tiny hair sway. Keep the exact face, textile details, camera angle and floral pastel buildings stable. No redesign, no extra fingers.",
    # 2 / 00:03-00:06. Five characters in precisely the same shared world.
    "Animate five friendly anthropomorphic 3D washing machine mascots walking together through the SAME warm golden cobblestone neighborhood with lush pink bougainvillea and palm trees. Exactly FIVE machines arranged horizontally across the street; dark cool one on LEFT, white winker, dark mid model, metallic-silver round-door model, white expressive winner on RIGHT. Each has two small gloved arms, short sneakered legs, smiling cartoon mouth and bright expressive eyes. Staggered gentle synchronized entrance, body bouncing and natural eye blinking. Preserve each silhouette and relative position. Neutral identity: avoid physical company logos.",
    # 3 / 00:06-00:10. Original sunglasses character.
    "Animate the SAME cool DARK CHARCOAL anthropomorphic top-load-style washing machine in the floral courtyard. Preserve oversized shiny BLACK SUNGLASSES, broad open-mouth grin, sneakered feet, both black-gloved hands giving a THUMBS-UP, and the same glossy black control-panel silhouette. Tiny swaggering dance, gentle mouth acting, thumbs wobble, golden glints. Camera portrait full-body, center-left subject and open empty graphic space to the right. Do not add new facial features.",
    # 4 / 00:10-00:14. Original wink and pointing character.
    "Animate the SAME friendly WHITE washing-machine cartoon mascot, large amber left eye, RIGHT EYE WINKING, rosy cheeks and broad smile, gloved hand pointing playfully RIGHT and other hand giving a small thumbs-up. Left foreground blue overflowing clothes basket; vivid pink flowers, pastel ochre street buildings, warm midday sunlight. Cute small heart shapes float softly, gentle pointing arm movement and smiling mouth motion. Preserve face and exact machine shape; leave clean right-side space for editable bubble and dynamic overlay.",
    # 5 / 00:14-00:18. Original machine, splash + soap.
    "Animate the SAME dark graphite smiling cartoon washing-machine mascot winking ONE eye, holding soft soap foam in one glove, opposite hand raised in a happy thumbs-up. SAME golden floral laundry lane. Translucent brilliant cyan water splashes curl dynamically around its sneakers, bubbles rise, body hops mildly without deformation and mouth reacts happily. Keep stable body panel, cartoon iris, limbs and facial proportions. Open space at right for separately composed factual overlays.",
    # 6 / 00:18-00:22. Original silver machine and confidence.
    "Animate the SAME premium metallic SILVER front-load washing machine mascot with a large round chrome door, big lively eyes over the door, broad happy smile, left arm slightly lifted and right white-gloved hand giving a thumbs-up. Bright pink flowers, pastel Indian neighborhood lane and warm sun, metal glints shift gently as body rocks. Keep exact front-load drum proportions and sneakers consistent; no national flags or brand-origin claims because actual brand is dynamic. Leave right-side clear graphical space.",
    # 7 / 00:22-00:26. Crown + cape champion.
    "Animate the SAME bright WHITE expressive front-load washer mascot with two bright amber cartoon eyes, huge enthusiastic smiling mouth, both white-gloved hands giving thumbs-up, a glittering GOLD CROWN overhead and red flowing superhero cape. Hero runs lightly in place down the SAME sunny floral alley; gentle cape flutter, crown sparkle, natural eye/mouth acting and tiny triumphant bounce. Preserve circular drum, sneakers and exact costume and machine identity, with clear right-side space for dynamic live number-one product overlays.",
    # 8 / 00:26-00:28. Group podium order 5-4-3-2-1.
    "Animate FIVE identical-to-prior-scene mascots together on the SAME sunny courtyard podium, in this LEFT-TO-RIGHT CHARACTER ORDER: dark sunglasses character, white winking character, dark bubbly mascot, silver round-door mascot, white crown-and-cape winner. All lightly cheer, wave and bounce while shoes stay grounded on distinct fixed-height pedestals rising to the right. Clear front faces of podiums for CLEAN numbers applied later, and an empty top zone for separately rendered speech bubble. Stable camera, no character swaps.",
    # 9 / 00:28-00:30. Must match same woman as scene 1.
    "Animate the EXACT SAME pink embroidered kurta woman from the opening, identical round expressive face, large warm brown eyes, long flowing dark wavy hair and gold hoop earrings in the SAME bougainvillea-filled warm Indian laundry street. She stands on the LEFT smiling confidently, holding a real-shaped upright smartphone in one hand facing the camera, pointing at its BLANK WHITE SCREEN with the other index finger. Natural blink and joyful smile, subtle phone tilt and finger point; keep face, fingers and phone steady. Leave RIGHT HALF open for TrustFolio purple-yellow graphic and legible URL to be composited AFTER generation.",
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
