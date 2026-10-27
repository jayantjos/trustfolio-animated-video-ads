"""Strict direct Meta Instagram+Facebook REELS publishing, NEVER ordinary poster posts.

Off unless explicit TF_VIDEO_REELS_PUBLISH_ENABLED=true and complete signed QA.
Uses separate GitHub video-ledger reservations to prevent double posting.
Facebook's 3-stage Reels upload and IG's async REELS media container differ
from JPEG publication and must not use the old poster API.
"""
import argparse,base64,hashlib,json,os,re,subprocess,time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode,urlsplit
from urllib.request import Request,build_opener
from urllib.error import HTTPError,URLError
from zoneinfo import ZoneInfo
from .live import fetch_live,DataBlocked
from .v6_live_campaign import prepublish_hard_gate,caption_for

REPO="jayantjos/trustfolio-animated-video-ads"
PAGE_ID="619193294620746"
EXPECTED_IG="trustfolio3"
GRAPH_VERSION="v25.0"
MAX_VIDEO_BYTES=60_000_000
PUBLIC_HOST="media.trustfolio.in"
LEDGER_BRANCH="trustfolio-v6-reels-publication-ledger"
IST=ZoneInfo("Asia/Kolkata")

class ReelBlocked(ValueError):pass

def demand(condition,reason):
    if not condition:raise ReelBlocked(reason)

def json_request(url,*,method="GET",token="",data=None,headers=None,requester=None):
    # Never put tokens in URL or print provider error bodies.
    h={"Accept":"application/json","User-Agent":"TrustFolioV6Reels/1.0"}
    h.update(headers or {})
    if token:h["Authorization"]="Bearer "+token
    if data is not None and not isinstance(data,bytes):
        data=urlencode(data).encode()
        h["Content-Type"]="application/x-www-form-urlencoded"
    req=Request(url,data=data,method=method,headers=h)
    try:
        opener=requester or build_opener().open
        with opener(req,timeout=45) as r:
            raw=r.read(512000)
            demand(r.status in (200,201),"Social API HTTP unexpected status")
            return json.loads(raw)
    except (HTTPError,URLError,TimeoutError,ValueError) as e:
        raise ReelBlocked("Social/GitHub API request failed: "+type(e).__name__) from None

def graph(path,token,*,data=None,requester=None):
    demand(bool(re.fullmatch(r"[A-Za-z0-9_./-]+",path)),"Unsafe Graph path")
    return json_request(f"https://graph.facebook.com/{GRAPH_VERSION}/{path}",
                        token=token,data=data,method="POST" if data is not None else "GET",
                        requester=requester)

def read_config(environ=None):
    env=os.environ if environ is None else environ
    demand(env.get("TF_VIDEO_REELS_PUBLISH_ENABLED")=="true",
           "Reels publishing kill switch OFF")
    demand(env.get("TF_VIDEO_FIRST_REEL_QA_APPROVED")=="true",
           "First end-to-end video/audio/source QA not yet authorized")
    demand(env.get("TF_META_PAGE_ID",PAGE_ID)==PAGE_ID,"Wrong Facebook Page ID")
    demand(env.get("GITHUB_REPOSITORY")==REPO,"Wrong publishing repository")
    token=env.get("TF_META_PAGE_ACCESS_TOKEN","")
    gh=env.get("GITHUB_TOKEN","")
    demand(len(token)>20 and len(gh)>20,"Missing video-publisher Page token or GitHub ledger token")
    return {"token":token,"gh":gh,"page":PAGE_ID,"today":datetime.now(IST).date().isoformat()}

def preflight_account(cfg,*,requester=None):
    token=cfg["token"]
    me=graph("me?fields=id,name",token,requester=requester) if False else None
    # Query fields through an escaped suffix only, never user-supplied.
    me=json_request(f"https://graph.facebook.com/{GRAPH_VERSION}/me?fields=id,name",
                    token=token,requester=requester)
    demand(str(me.get("id"))==PAGE_ID,"Provided token is not verified FB Page token")
    page=json_request(f"https://graph.facebook.com/{GRAPH_VERSION}/{PAGE_ID}?"
                      "fields=id,instagram_business_account",token=token,requester=requester)
    demand(str(page.get("id"))==PAGE_ID,"Meta page identity mismatch")
    ig=str((page.get("instagram_business_account") or {}).get("id") or "")
    demand(re.fullmatch(r"[0-9]+",ig) is not None,"Instagram Professional account not linked")
    who=json_request(f"https://graph.facebook.com/{GRAPH_VERSION}/{ig}?fields=id,username",
                     token=token,requester=requester)
    demand(who.get("username")==EXPECTED_IG and str(who.get("id"))==ig,
           "Wrong connected Instagram account")
    quota=json_request(f"https://graph.facebook.com/{GRAPH_VERSION}/{ig}/content_publishing_limit"
                       "?fields=quota_usage,config",token=token,requester=requester)
    try:
        value=quota["data"][0]
        demand(int(value["quota_usage"])<int(value["config"]["quota_total"]),
               "Instagram rolling quota exhausted")
    except (KeyError,TypeError,IndexError,ValueError):
        raise ReelBlocked("Instagram current publishing quota unavailable")
    return ig

def inspect_mp4(path):
    path=Path(path)
    demand(path.is_file() and 100000<path.stat().st_size<=MAX_VIDEO_BYTES,
           "MP4 unavailable or unsafe file size")
    raw=subprocess.check_output(["ffprobe","-v","error","-show_entries",
         "format=duration:stream=codec_type,codec_name,width,height,sample_rate",
         "-of","json",str(path)],text=True)
    md=json.loads(raw)
    v=next((s for s in md.get("streams",[]) if s.get("codec_type")=="video"),{})
    a=next((s for s in md.get("streams",[]) if s.get("codec_type")=="audio"),{})
    duration=float(md["format"]["duration"])
    demand(53.7<=duration<=54.3 and v.get("width")==720 and v.get("height")==1280
           and v.get("codec_name")=="h264" and a.get("codec_name")=="aac"
           and a.get("sample_rate")=="48000","Wrong duration/aspect/codec/audio format")
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify_public_media(url,digest,*,opener=None):
    u=urlsplit(url)
    demand(u.scheme=="https" and u.hostname==PUBLIC_HOST and
        u.port in (None,443) and not u.username and not u.password and
        u.path.startswith("/trustfolio-videos/") and u.path.endswith(".mp4") and
        not u.query and not u.fragment,"Video must be hosted on exact trusted HTTPS host/path")
    # The default opener here does not follow untrusted redirects.
    from .live import NoRedirect
    fetcher=opener or build_opener(NoRedirect()).open
    h=hashlib.sha256();total=0
    req=Request(url,headers={"Accept":"video/mp4","User-Agent":"TrustFolioReelsMediaIntegrity/1.0"})
    try:
        with fetcher(req,timeout=45) as r:
            demand(r.status==200 and "video/" in r.headers.get("Content-Type","").lower(),
                   "Public MP4 source inaccessible")
            while True:
                chunk=r.read(131072)
                if not chunk:break
                total+=len(chunk)
                demand(total<=MAX_VIDEO_BYTES,"Video host size exceeds limit")
                h.update(chunk)
    except (HTTPError,URLError,TimeoutError,OSError) as exc:
        raise ReelBlocked("Public HTTPS video unavailable") from None
    demand(h.hexdigest()==digest,"Public MP4 differs from audited uploaded bytes")
    return True

def github(cfg,route,*,method="GET",data=None):
    url="https://api.github.com/repos/"+REPO+"/"+route
    h={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
    if data is not None:data=json.dumps(data).encode("utf8");h["Content-Type"]="application/json"
    return json_request(url,token=cfg["gh"],method=method,data=data,headers=h)

def ledger_branch(cfg):
    try:github(cfg,"git/ref/heads/"+LEDGER_BRANCH)
    except ReelBlocked:
        head=github(cfg,"git/ref/heads/main")
        oid=head.get("object",{}).get("sha","")
        demand(bool(re.fullmatch("[a-f0-9]{40}",oid)),"Cannot safely initialize video ledger")
        github(cfg,"git/refs",method="POST",data={"ref":"refs/heads/"+LEDGER_BRANCH,"sha":oid})

def record_path(cfg,network,mode):
    demand(network in ("instagram","facebook"),"Unknown network")
    demand(mode in ("budget","brand_budget","comparison"),"Unknown campaign mode")
    return f"video-publication-ledger/{cfg['today']}/washing-machines-{mode}-{network}.json"

def reserve(cfg,network,mode,source_sha,video_sha):
    """One create-only GitHub PUT; existing unknown state blocks ALL repeats."""
    ledger_branch(cfg)
    path=record_path(cfg,network,mode)
    doc={"network":network,"mode":mode,"source_sha256":source_sha,
         "video_sha256":video_sha,"status":"RESERVED_NO_AUTORETRY",
         "reserved_at":datetime.now(IST).isoformat()}
    b=base64.b64encode((json.dumps(doc,sort_keys=True)+"\n").encode()).decode()
    try:
        r=github(cfg,"contents/"+path,method="PUT",
               data={"message":"Reserve one V6 Reel "+cfg["today"]+" "+network+" "+mode,
                     "branch":LEDGER_BRANCH,"content":b})
    except ReelBlocked as e:
        raise ReelBlocked("Existing or ambiguous Reel reservation; reconcile Meta+ledger before retry") from None
    digest=r.get("content",{}).get("sha")
    demand(isinstance(digest,str) and re.fullmatch(r"[a-f0-9]{40}",digest),
           "Missing durable reservation SHA; do not contact Meta")
    return path,digest

def ledger_update(cfg,path,sha,doc):
    value=base64.b64encode((json.dumps(doc,sort_keys=True,indent=2)+"\n").encode()).decode()
    return github(cfg,"contents/"+path,method="PUT",
       data={"message":"Update verified V6 Reel publication status","branch":LEDGER_BRANCH,
             "sha":sha,"content":value})

def instagram(cfg,igid,video_url,caption):
    container=graph(igid+"/media",cfg["token"],data={
        "media_type":"REELS","video_url":video_url,"caption":caption,"share_to_feed":"true"})
    cid=str(container.get("id") or "")
    demand(bool(re.fullmatch("[0-9]+",cid)),"Instagram returned no Reel container")
    for attempt in range(15):
        state=json_request(f"https://graph.facebook.com/{GRAPH_VERSION}/{cid}?fields=status_code",
                           token=cfg["token"]).get("status_code")
        if state=="FINISHED":break
        demand(state not in ("ERROR","EXPIRED","PUBLISHED"),"Instagram container processing failed")
        time.sleep(5)
    else:raise ReelBlocked("Instagram Reel container did not finish; no public post submitted")
    created=graph(igid+"/media_publish",cfg["token"],data={"creation_id":cid})
    media_id=str(created.get("id") or "")
    demand(bool(re.fullmatch("[0-9]+",media_id)),
           "Instagram media_publish returned unknown/ambiguous public state")
    post=json_request(f"https://graph.facebook.com/{GRAPH_VERSION}/{media_id}?fields=id,permalink",
                     token=cfg["token"])
    demand(str(post.get("id"))==media_id and str(post.get("permalink") or "").startswith("https://"),
           "Instagram public permalink not confirmed; do not claim success")
    return {"status":"INSTAGRAM_PUBLISHED_VERIFIED","media_id":media_id,
            "permalink":post["permalink"]}

def facebook(cfg,local_mp4,caption):
    start=graph(cfg["page"]+"/video_reels",cfg["token"],data={"upload_phase":"start"})
    uid=str(start.get("video_id") or "")
    url=start.get("upload_url") or ""
    u=urlsplit(url)
    demand(re.fullmatch(r"[0-9]+",uid) is not None and u.scheme=="https"
           and u.hostname=="rupload.facebook.com" and u.port in (None,443)
           and not u.username and not u.password,"Untrusted Facebook Reel upload URL")
    body=Path(local_mp4).read_bytes()
    request=Request(url,method="POST",data=body,headers={
        "Authorization":"OAuth "+cfg["token"],"offset":"0","file_size":str(len(body)),
        "Content-Type":"application/octet-stream"})
    try:
        with build_opener().open(request,timeout=180) as result:
            response=json.loads(result.read(65536))
            demand(result.status in (200,201) and response.get("success") is True,
                   "Facebook Reel byte upload not confirmed")
    except (HTTPError,URLError,TimeoutError,OSError):
        raise ReelBlocked("Facebook Reel video upload ambiguous; ledger prevents retries") from None
    finish=graph(cfg["page"]+"/video_reels",cfg["token"],data={
        "upload_phase":"finish","video_id":uid,"video_state":"PUBLISHED",
        "description":caption,"title":"TrustFolio • 5 Best Washing Machines"})
    demand(finish.get("success") is True,
           "Facebook video_reels finish not confirmed; ledger prevents retries")
    status=json_request(f"https://graph.facebook.com/{GRAPH_VERSION}/{uid}?fields=id,status",
                        token=cfg["token"])
    demand(str(status.get("id"))==uid,"Facebook Reel readback ID mismatch")
    return {"status":"FACEBOOK_REEL_ACCEPTED_STATUS_RECHECK_REQUIRED",
            "video_id":uid,"observed_state":status.get("status",{})}

def publish(cfg,receipt,render_record,mp4,url,caption,*,fresh_fetch=fetch_live):
    source=receipt
    # Prepare only when *all* source/photo/voice/first-release verification fields TRUE.
    digest=inspect_mp4(mp4)
    demand(render_record.get("video_sha256")==digest,
           "Rendered SHA not equal local MP4 bytes")
    demand(caption==caption_for(source)["caption"],
           "Caption does not correspond to these exact five products and prices")
    verify_public_media(url,digest)
    # Source manifest cannot attest to media hosted later. This exact verifier
    # alone grants the hosted SHA integrity gate, only after bytes match.
    render_record=dict(render_record)
    render_record["public_media_sha256_pass"]=True
    ig=preflight_account(cfg)
    # One explicit latest live refresh before touching public Meta post, not cached catalog.
    recent=fresh_fetch(source["category"],source["budget_inr"],
                       source["mode"],source.get("brand",""))
    prepublish_hard_gate(render_record,source,recent)
    published={}
    for network in ("instagram","facebook"):
        path,sha=reserve(cfg,network,source["mode"],source["snapshot_sha256"],digest)
        result=(instagram(cfg,ig,url,caption) if network=="instagram"
                else facebook(cfg,mp4,caption))
        # This update is AFTER provider accepted/readback and may itself fail;
        # reservation remains and prevents duplicate publishing.
        ledger_update(cfg,path,sha,{
            "network":network,"campaign":source["snapshot_sha256"],
            "video_sha256":digest,**result})
        published[network]=result
    return published

def main():
    p=argparse.ArgumentParser()
    for key in ("source-receipt","render-qa","mp4","public-url","caption"):
        p.add_argument("--"+key,required=True)
    a=p.parse_args()
    cfg=read_config()
    source=json.loads(Path(a.source_receipt).read_text(encoding="utf-8"))
    qa=json.loads(Path(a.render_qa).read_text(encoding="utf-8"))
    caption=Path(a.caption).read_text(encoding="utf-8").strip()
    outputs=publish(cfg,source,qa,a.mp4,a.public_url,caption)
    print("META_REELS_PUBLISHED_WITH_READBACK="+json.dumps(outputs))
if __name__=="__main__":main()
