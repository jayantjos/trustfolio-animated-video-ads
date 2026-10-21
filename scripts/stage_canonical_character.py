"""Upload bytewise approved PNG to the existing RunPod S3 volume; NO GPU.

The GitHub copy is the SHA256-pinned immutable master. Upload intentionally uses
PUT instead of preflight HEAD: some S3-compatible providers return 403 for HEAD
on absent keys even when authenticated PUT/GET are allowed. Remote GET digest
provides end-to-end integrity, not a potentially spoofed user-defined metadata
header.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

IMAGE = "assets/characters/shared/pink_kurta_lady_v1.png"
EXPECTED = "7f9ca4e47803ff9df57ff389ede1bba15eb6cb761c2fe4521edfe4036bc20ac6"
BUCKET = "1bch597yrz"
EXPECTED_BYTES = 2484010
ENDPOINT = "https://s3api-eu-ro-1.runpod.io"

class CharacterStageError(RuntimeError):
    pass

def hash_image(path=IMAGE):
    path = Path(path)
    if not path.is_file():
        raise CharacterStageError("ORIGINAL_APPROVED_PNG_NOT_IN_REPO")
    if path.stat().st_size != EXPECTED_BYTES:
        raise CharacterStageError("APPROVED_IMAGE_SIZE_MISMATCH")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != EXPECTED:
        raise CharacterStageError("APPROVED_IMAGE_SHA256_MISMATCH")
    return digest

def safe_s3_error(exc):
    # No provider message or request URL is logged. Do not emit key material.
    status = str(getattr(exc, "response", {}).get("ResponseMetadata", {}).get("HTTPStatusCode", "unknown"))
    code = str(getattr(exc, "response", {}).get("Error", {}).get("Code", "unknown"))
    if status not in ("400", "401", "403", "404", "405", "408", "409", "429", "500", "502", "503", "504"):
        status = "unknown"
    if code not in ("AccessDenied", "SignatureDoesNotMatch", "InvalidAccessKeyId",
                    "NoSuchBucket", "NoSuchKey", "NotImplemented", "InvalidRequest",
                    "RequestTimeout", "InternalError", "SlowDown", "unknown"):
        code = "unknown"
    return "S3_HTTP_" + status + "_" + code

def upload_and_verify(s3, path=IMAGE):
    # Only an exact-length, exact-hash approved original is ever sent.
    digest = hash_image(path)
    data = Path(path).read_bytes()
    try:
        s3.put_object(Bucket=BUCKET, Key=IMAGE, Body=data, ContentType="image/png",
                      Metadata={"sha256": digest,
                                "asset-role": "approved-pink-kurta-lead"})
    except Exception as exc:
        raise CharacterStageError("S3_PUT_FAILED_" + safe_s3_error(exc)) from None
    try:
        response = s3.get_object(Bucket=BUCKET, Key=IMAGE)
    except Exception as exc:
        raise CharacterStageError("S3_GET_VERIFY_FAILED_" + safe_s3_error(exc)) from None
    body = response.get("Body")
    if not body:
        raise CharacterStageError("S3_GET_BODY_MISSING")
    try:
        if int(response.get("ContentLength", -1)) != EXPECTED_BYTES:
            raise CharacterStageError("S3_GET_LENGTH_MISMATCH")
        remote_hash = hashlib.sha256()
        total = 0
        while True:
            b = body.read(1024 * 1024)
            if not b:
                break
            total += len(b)
            if total > EXPECTED_BYTES:
                raise CharacterStageError("S3_GET_EXCEEDS_APPROVED_BYTES")
            remote_hash.update(b)
        if total != EXPECTED_BYTES or remote_hash.hexdigest() != digest:
            raise CharacterStageError("S3_REMOTE_SHA256_MISMATCH")
    finally:
        body.close()
    return {"status": "APPROVED_SHARED_LEAD_UPLOADED_AND_S3_GET_SHA_VERIFIED",
            "s3_key": IMAGE, "bucket": BUCKET, "bytes": total,
            "sha256": digest, "gpu_started": False, "publishing_enabled": False}

def main():
    try:
        hash_image()
        a = os.environ.get("RUNPOD_S3_ACCESS_KEY_ID", "")
        b = os.environ.get("RUNPOD_S3_SECRET_ACCESS_KEY", "")
        if not a or not b:
            raise CharacterStageError("S3_SECRETS_MISSING")
        import boto3
        from botocore.config import Config
        s3 = boto3.client(
            "s3", region_name="eu-ro-1", endpoint_url=ENDPOINT,
            aws_access_key_id=a, aws_secret_access_key=b,
            config=Config(signature_version="s3v4",
                          s3={"addressing_style": "path"},
                          connect_timeout=25, read_timeout=120,
                          retries={"max_attempts": 3, "mode": "standard"}))
        report = upload_and_verify(s3)
        Path("output").mkdir(exist_ok=True)
        Path("output/approved-character-upload.json").write_text(
            json.dumps(report, indent=2) + "\n")
        print("TRUSTFOLIO_SHARED_CHARACTER=" + report["status"])
        print("APPROVED_CHARACTER_SHA256=" + report["sha256"])
        print("APPROVED_CHARACTER_S3_KEY=" + report["s3_key"])
        print("GPU_CREATED=false")
        return 0
    except CharacterStageError as exc:
        print("TRUSTFOLIO_SHARED_CHARACTER=BLOCKED_" + str(exc))
        return 1
    except Exception:
        print("TRUSTFOLIO_SHARED_CHARACTER=BLOCKED_UNEXPECTED_S3_SDK_ERROR")
        return 1

if __name__ == "__main__":
    sys.exit(main())
