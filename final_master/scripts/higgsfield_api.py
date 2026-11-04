"""Server-only Higgsfield API request client for TrustFolio video pipeline.

Provisional transport per user's Higgsfield API setup instructions.
Model-specific path and Input JSON Schema MUST be independently verified before paid use.
Never commit keys; Authorization: Key <complete-key> is server-only.
"""
from __future__ import annotations
import json,os,re,urllib.request,urllib.error
from dataclasses import dataclass
from typing import Any

BASE="https://api.higgsfield.ai"
TERMINAL=frozenset({"completed","failed","nsfw","canceled"})
ID=re.compile(r"^[A-Za-z0-9_-]{6,180}$")

@dataclass(frozen=True)
class HFClient:
    key: str
    base: str=BASE

    def __post_init__(self):
        if not self.key or self.key.startswith("Key ") or any(c.isspace() for c in self.key):
            raise ValueError("Set complete copied HF_API_KEY without Key prefix or whitespace")
        if self.base!=BASE:raise ValueError("Only official Higgsfield API host supported")

    @classmethod
    def from_env(cls):
        return cls(os.environ.get("HF_API_KEY",""))

    def _call(self,method:str,path:str,payload:dict[str,Any]|None=None)->dict[str,Any]:
        if not path.startswith("/") or "//" in path or "?" in path or ".." in path:
            raise ValueError("Unsafe API path")
        data=None if payload is None else json.dumps(payload).encode("utf-8")
        req=urllib.request.Request(self.base+path,method=method,data=data,headers={
            "Authorization":"Key "+self.key,"Content-Type":"application/json",
            "Accept":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=30) as response:
                body=json.loads(response.read(2_000_000))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Higgsfield HTTP {exc.code}; inspect provider logs, do not retry paid submit blindly") from None
        if not isinstance(body,dict):raise RuntimeError("Non-object API response")
        return body

    def status(self,request_id:str)->dict[str,Any]:
        if not ID.fullmatch(request_id):raise ValueError("Invalid request ID")
        response=self._call("GET",f"/requests/{request_id}/status")
        return response

    def cancel(self,request_id:str)->dict[str,Any]:
        if not ID.fullmatch(request_id):raise ValueError("Invalid request ID")
        return self._call("POST",f"/requests/{request_id}/cancel",{})

    def submit_model(self,verified_model_path:str,payload:dict[str,Any],*,schema_verified:bool=False)->dict[str,Any]:
        # Fail-closed: caller must document model-specific schema before billable request.
        if not schema_verified:raise ValueError("Model-specific schema not verified: no submission")
        if not re.fullmatch(r"/[a-zA-Z0-9._/-]{3,180}",verified_model_path) or ".." in verified_model_path or "//" in verified_model_path:
            raise ValueError("Invalid model endpoint")
        if not isinstance(payload,dict) or not payload:raise ValueError("Missing validated model input")
        result=self._call("POST",verified_model_path,payload)
        if not isinstance(result.get("request_id"),str):raise RuntimeError("Missing request_id")
        return result

    def upload_url(self,content_type:str)->dict[str,Any]:
        if content_type not in {"audio/wav","audio/mpeg","image/png","image/jpeg","video/mp4"}:
            raise ValueError("Unsupported content type")
        result=self._call("POST","/files/generate-upload-url",{"content_type":content_type})
        if not all(isinstance(result.get(k),str) for k in ("upload_url","public_url")):
            raise RuntimeError("Upload authorization response incomplete")
        # Storage PUT must omit API key, and use all provider-returned upload headers.
        return result
