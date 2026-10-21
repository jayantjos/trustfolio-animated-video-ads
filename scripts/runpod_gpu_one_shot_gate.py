#!/usr/bin/env python3
"""No-spend validation of RunPod GPU lifecycle safety prerequisites."""
import json,sys
from pathlib import Path
POLICY="config/runpod_gpu_one_shot_policy.json"
class Unsafe(Exception):pass
def require_safe(p):
    if p["network_volume_id"]!="1bch597yrz" or p["region"]!="EU-RO-1":
        raise Unsafe("WRONG_PERSISTENT_NETWORK_VOLUME")
    if p["max_concurrent_pods"]!=1 or p["max_gpu_lifetime_minutes"]>60:
        raise Unsafe("ONE_POD_ONE_HOUR_CAP_REQUIRED")
    for k in ("must_provider_auto_terminate","must_independent_reaper",
              "must_always_terminate_in_finally","must_confirm_pod_deleted_after_render",
              "must_confirm_video_mp4_s3_hash_before_delete","keep_s3_volume_after_delete"):
        if p[k] is not True:raise Unsafe("MISSING_GUARD_"+k)
    if p["publishing_enabled"] is not False:raise Unsafe("PUBLISHING_MUST_BE_DISABLED")
    if (p["paid_gpu_instance_provisioning_enabled"] is not True or
        p["gpu_hourly_price_verified"] is not True or
        p["pod_api_write_key_connected"] is not True or
        p["gpu_spending_approved_usd"]<=0 or
        p["separate_cron_vps_deploy_completed"] is not True):
        raise Unsafe("GPU_SPEND_AND_OR_AUTODESTROY_NOT_READY")
    return True
def main():
    cfg=json.loads(Path(POLICY).read_text())
    try:
        require_safe(cfg)
    except Unsafe as exc:
        print("GPU_ONE_SHOT=BLOCKED_"+str(exc))
        print("RUNPOD_CHARGED_POD_CREATED=false")
        return 0
    print("GPU_ONE_SHOT=APPROVED_FOR_SEPARATE_OPERATOR_FINAL_REVIEW")
    return 0
if __name__=="__main__":sys.exit(main())
