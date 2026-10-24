"""One-dollar GPU budget contract for the private nine-shot Wan2.2 render.

The user's Oct 24 approval is an UP-TO-USD1 limit, never a promise to finish all
nine motion clips. Network-volume subscription, Actions or taxes can incur
separate charges; the cap covers the new GPU Pod only.

This module has no provider write APIs and cannot start Pods.
"""
from decimal import Decimal, InvalidOperation
from datetime import datetime,timedelta,timezone

GPU_LIMIT_USD=Decimal("1.00")
EXTRA_BILLING_MARGIN_USD=Decimal("0.10")
MAX_RATE_USD_PER_HOUR=Decimal("1.50")
POD_PROVIDER_TTL_MINUTES=30
WORKER_WALL_SECONDS=22*60
MAX_SCENE_SECONDS=6*60
MAX_CONCURRENT_PODS=1
APPROVED_GPU="NVIDIA GeForce RTX 4090"
APPROVED_VOLUME="1bch597yrz"
APPROVED_DATACENTER="EU-RO-1"

class BudgetBlocked(ValueError):
    pass

def quote_guard(rate, *, ttl_minutes=POD_PROVIDER_TTL_MINUTES, remaining_budget=GPU_LIMIT_USD):
    """Read-only prediction. Always recheck LIVE price and actual Pod rate at create."""
    try:
        actual_rate=Decimal(str(rate))
        available=Decimal(str(remaining_budget))
    except (InvalidOperation,ValueError,TypeError):
        raise BudgetBlocked("GPU_LIVE_PRICE_MISSING") from None
    if (not actual_rate.is_finite() or actual_rate<=0
        or actual_rate>MAX_RATE_USD_PER_HOUR):
        raise BudgetBlocked("GPU_PRICE_HIGHER_THAN_ONE_DOLLAR_POLICY")
    if (not available.is_finite() or available<=0 or available>GPU_LIMIT_USD):
        raise BudgetBlocked("GPU_AVAILABLE_BUDGET_INVALID")
    if type(ttl_minutes) is not int or ttl_minutes<2 or ttl_minutes>POD_PROVIDER_TTL_MINUTES:
        raise BudgetBlocked("GPU_PROVIDER_TTL_TOO_LARGE")
    forecast=actual_rate*Decimal(ttl_minutes)/Decimal(60)
    if forecast+EXTRA_BILLING_MARGIN_USD>=available:
        raise BudgetBlocked("GPU_PROVIDER_TTL_CANNOT_FIT_ONE_DOLLAR_CAP")
    return {"live_rate_usd_per_hour":str(actual_rate),
            "max_pod_minutes":ttl_minutes,
            "predicted_upper_gpu_cost_usd":str(round(forecast,6)),
            "unspent_gpu_headroom_usd":str(round(available-forecast,6)),
            "max_gpu_budget_usd":str(GPU_LIMIT_USD),
            "total_cost_including_other_services_guaranteed":False,
            "maximum_worker_wall_seconds":WORKER_WALL_SECONDS,
            "paid_gpu_would_start":False}

def deployment_guard(target, *, quoted_rate):
    """Pre-submit require independent provider TTL as well as one-Pod scope."""
    if not isinstance(target,dict):
        raise BudgetBlocked("POD_TARGET_MISSING")
    if (target.get("gpuTypeId")!=APPROVED_GPU
        or target.get("gpuCount")!=1
        or target.get("dataCenterId")!=APPROVED_DATACENTER
        or target.get("networkVolumeId")!=APPROVED_VOLUME
        or target.get("volumeMountPath")!="/workspace"
        or target.get("cloudType")!="SECURE"):
        raise BudgetBlocked("TARGET_NOT_ON_APPROVED_ADA_GPU_AND_VOLUME")
    if target.get("startJupyter") is not False or target.get("startSsh") is not False:
        raise BudgetBlocked("UNEXPECTED_PUBLIC_GPU_PORTS")
    try:
        end=datetime.fromisoformat(target["terminateAfter"].replace("Z","+00:00"))
    except (AttributeError,KeyError,ValueError,TypeError):
        raise BudgetBlocked("PROVIDER_AUTO_TERMINATION_REQUIRED") from None
    if end.tzinfo is None:
        raise BudgetBlocked("PROVIDER_TTL_WITHOUT_TIMEZONE")
    now=datetime.now(timezone.utc)
    requested_minutes=(end-now).total_seconds()/60
    if not 0<requested_minutes<=POD_PROVIDER_TTL_MINUTES+0.25:
        raise BudgetBlocked("PROVIDER_TTL_OUTSIDE_30_MINUTE_HARD_LIMIT")
    return quote_guard(quoted_rate)

def require_clean_gpu_inputs(*, all_nine_plates_clean, image_identity_qa,
                             independent_reaper_recent_success, source_digest_pinned):
    for ok,code in (
        (all_nine_plates_clean,"NINE_BRANDED_CANDIDATE_IMAGES_MUST_BE_CLEANED"),
        (image_identity_qa,"CHARACTER_IDENTITY_VISUAL_QA_PENDING"),
        (independent_reaper_recent_success,"INDEPENDENT_POD_REAPER_NOT_READY"),
        (source_digest_pinned,"IMAGE_SHA_AND_GPU_WORKER_DIGEST_NOT_PINNED")):
        if ok is not True:
            raise BudgetBlocked(code)
    return True
