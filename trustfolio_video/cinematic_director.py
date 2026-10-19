"""Camera-and-acting shot plans for twenty different TrustFolio cartoon worlds.

These are precise DIRECTOR INSTRUCTIONS (not completed videos). They bind
each line, source-priced product and evidence field to an authoritative
ranked product ID. A render must later satisfy the separate premium visual
contract and human artistic/voice QA. This module cannot publish or rerank.

One 30s film has: hook, arrival, 5 speaking/reacting product shots, ranking
lineup, CTA. Product claims derive only from the existing strict educational
storyboard and never from illustrative 3D category mascots.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from .contract import Blocked, canonical
from .educational import build_educational_story, load_master

ROOT=Path(__file__).resolve().parents[1]
REFERENCE=ROOT/"config/approved_premium_3d_visual_contract.json"

# Category-specific choreography, props and exact camera direction.
# These are fictional actions only, NEVER evidence of product performance.
WORLD_ACTION={
 "washing-machines":("lost_sock_chase","soap_bubble_throw","sock_reunion","dolly_along_sunny_laundry_street"),
 "refrigerators":("fruit_stuck_outside_ice_palace","ice_gate_open","fruit_returns_to_cold_room","orbit_around_frozen_castle"),
 "smart-phones":("lost_notification_in_neon_alley","phone_passes_message","team_receives_message","tracking_shot_neon_city"),
 "headphones-earbuds":("missing_beat_at_concert","dance_call_response","rhythm_returns","concert_low_angle_dolly"),
 "smartwatches":("running_late_to_fitness_race","wrist_clock_reaction","finish_line_high_five","track_side_tracking_camera"),
 "laptops":("missing_class_project_file","cursor_teamwork","presentation_saved","classroom_dolly_to_blackboard"),
 "smart-tvs":("movie_remote_disappeared","popcorn_team_search","cinema_premiere","theater_camera_pan"),
 "speakers":("party_music_pauses","speaker_duet","dancefloor_celebration","crane_music_stage"),
 "air-conditioners":("heatwave_room_melting","cold_breeze_teamwork","cool_room_reunion","warm_to_cool_color_dolly"),
 "air-coolers":("dry_desert_party_no_breeze","water_cart_challenge","breezy_desert_carnival","follow_the_water_cart"),
 "water-purifiers":("lost_water_drop","filter_gate_team","droplet_reunion","water_channel_tracking_camera"),
 "geysers":("cold_morning_shower","warm_towel_rescue","winter_lodge_comfort","heater_lodge_dolly"),
 "microwave-ovens":("popcorn_missed_movie","timer_conversation","snack_premiere","snack_counter_closeups"),
 "mixer-grinders":("chutney_melody_stops","masala_drum_session","spice_ensemble","spice_studio_swoop"),
 "induction-cooktops":("space_kitchen_timer_fails","compatible_pan_challenge","space_cafe_meal_ready","kitchen_planet_orbit"),
 "tablets":("drawing_island_bridge_missing","sketch_team_draws","bridge_appears","follow_pen_over_island"),
 "vacuum-cleaners":("dust_cloud_hiding_under_sofa","detective_team_tracks_dust","dust_case_solved","low_camera_under_sofa"),
 "ceiling-fans":("racing_banner_stuck","fan_wind_ribbon_exchange","finish_line_banner","racing_stadium_track"),
 "desktop-computers":("office_deadline_approaches","data_team_transfer","file_delivery","pixel_office_dolly"),
 "drones":("postcard_lost_in_clouds","flying_mail_delivery","cloud_post_office_reunion","aerial_flythrough"),
}
EMOTIONS=("confused","playful","surprised","hopeful","competitive","heroic","relieved")
MOVES=("dolly_in","orbit_low","dolly_side","over_shoulder","push_in_closeup","hero_crane","wide_reveal")
SFX={
 "washing-machines":"bubble_pop",
 "headphones-earbuds":"beat_drop",
 "drones":"propeller_whoosh",
 "refrigerators":"ice_chime",
 "smart-phones":"notification_ping",
}

def _interval(start,end):
    return {"start_sec":round(start,3),"end_sec":round(end,3)}

def cinematic_plan(approved, *, master=None):
    master=load_master() if master is None else master
    education=build_educational_story(approved,master,duration=30,language="hinglish")
    spec=approved["campaign"]
    slug=spec["category"]
    if slug not in WORLD_ACTION:
        raise Blocked("Unsupported 3D category: "+slug)
    refs=json.loads(REFERENCE.read_text("utf-8"))
    if slug not in refs["category_order"]:
        raise Blocked("Category missing from user-approved visual reference")
    world=next(s for s in master["slots"] if s.get("backend_slug")==slug)
    motif=world["creative"]
    env=world["environment"]
    product_events=[s for s in education["scenes"] if s.get("product_id")]
    if len(product_events)!=5 or [s["rank"] for s in product_events]!=[5,4,3,2,1]:
        raise Blocked("Cinematic product scene positions must follow genuine 5 to 1 backend rank")
    original_ids=[p["id"] for p in approved["products"]]
    if education["ranked_source_ids"]!=original_ids:
        raise Blocked("Storyboard source identity mismatched")
    action,interaction,resolution,camera=WORLD_ACTION[slug]
    shots=[
      {**_interval(0,3),"shot":"human_problem_hook",
       "camera":"wide_to_close_reaction","setting":env["location"],
       "story_action":action,"emotion":"worried_but_playful",
       "dialogue":education["scenes"][0]["text"],
       "product_ids":[],"spec_claims":[],"render_layer":"licensed_human_or_scene_prop"},
      {**_interval(3,6),"shot":"five_friend_entrance",
       "camera":camera,"setting":env["location"],
       "story_action":interaction,
       "dialogue":"पाँच दोस्त आए, पर कोई अकेला हीरो नहीं!",
       "product_ids":original_ids,"spec_claims":[],
       "character_motion":["walk_or_fly","turn","wave","physical_reaction"],
       "render_layer":"five_independently_rigged_characters"},
    ]
    for idx,event in enumerate(product_events):
        start=6+idx*3.2
        end=start+3.2
        rank=event["rank"]
        partner_id=event["partner_product_id"]
        if partner_id not in original_ids:
            raise Blocked("Partner interaction not in source five ranked products")
        fact=event.get("evidence")
        if fact and fact.get("source_product_id")!=event["product_id"]:
            raise Blocked("Feature evidence belongs to another ranked product")
        # All scenes require two or more independent characters to REACT,
        # not repeated static solo posters.
        shots.append({**_interval(start,end),"shot":"character_feature_and_reaction",
          "camera":MOVES[idx%len(MOVES)],"setting":env["location"],
          "story_action":interaction,
          "product_id":event["product_id"],"partner_product_id":partner_id,
          "rank":rank,"price_inr":event["price_inr"],
          "price_is_historical":event["price_is_historical"],
          "dialogue":event["text"],"verified_feature":fact,
          "spec_claims":[fact] if fact else [],
          "character_motion":["gesturing_speech","mouth_voice_envelope","blink","partner_responds"],
          "emotion":EMOTIONS[idx%len(EMOTIONS)],
          "render_layer":"genuine_original_product_identity_plus_cartoon_limb_rig",
          "footage_rights":"NOT_VERIFIED_AS_COMMERCIAL_AD",
        })
    shots.append({**_interval(22,26),"shot":"all_five_authoritative_ranking",
      "camera":"crane_back_to_reveal","setting":env["location"],
      "story_action":resolution,
      "product_ids":original_ids,"rank_order":[5,4,3,2,1],
      "dialogue":"ये हैं ट्रस्टफ़ोलियो के दर्ज किए गए टॉप पाँच!",
      "spec_claims":[],"render_layer":"five_rigged_characters_on_numbered_platforms",
      "rank_score_explanation":"No scoring factors supplied; rank shown as backend fact only",
    })
    shots.append({**_interval(26,30),"shot":"trustfolio_branded_cta",
      "camera":"hero_dolly_out","setting":env["location"],
      "story_action":"present_comparison_not_fake_guarantees",
      "product_ids":original_ids,
      "dialogue":education["scenes"][-1]["text"],
      "caption":"Compare current offers at trustfolio.in; prices may change",
      "spec_claims":[],"render_layer":"licensed_logo_and_branded_cta",
    })
    if len(shots)!=9:
        raise Blocked("9 cinematic story beats required")
    if any(shots[i]["end_sec"]>shots[i+1]["start_sec"]+.001 for i in range(8)):
        raise Blocked("Cinematic story scenes must not overlap")
    demo_only=bool(approved.get("demo_only"))
    return {
      "version":1,"status":"DIRECTOR_SHOT_PLAN_NOT_A_RENDERED_MOVIE",
      "category":slug,"category_world":world["theme"],"category_action":action,
      "category_story_resolution":resolution,"camera_language":camera,
      "campaign":spec,
      "id_sha256":hashlib.sha256(canonical({
         "ref":refs["id"],"source_sha256":education["source_sha256"],
         "campaign":spec,"film_version":1
      }).encode("utf-8")).hexdigest(),
      "reference_lock_id":refs["id"],
      "source_sha256":education["source_sha256"],
      "ranked_source_ids":original_ids,"shots":shots,
      "format":{"width":1080,"height":1920,"fps":24,"seconds":30,"shot_count":9},
      "source_status":"HISTORICAL_QA_ONLY" if demo_only else "PENDING_MANUAL_RELEASE_GATES",
      "requires":["source price/stock validation","product photo advertising rights",
                  "official TrustFolio brand assets","natural Hindi voice QA",
                  "premium visual reference human approval","phoneme/voice mouth-sync check"],
      "voice_and_animation_generated":False,
      "video_created":False,"production_approved":False,
      "publishing_enabled":False,
      "watermark":"DEMO - NOT FOR PUBLICATION" if demo_only else "QA PREVIEW - NO PUBLICATION",
    }
