"""Make four-second Flow editing clips and replace ONLY approved regenerated scenes."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime
import json
import shutil
import subprocess
import tempfile

from .flow_prompts import DYNAMIC
from .live import DataBlocked, check_receipt

SCENE_COUNT=10
SCENE_SECONDS=4


def _run(args):
    subprocess.run(args,check=True,stdout=subprocess.DEVNULL)


def file_hash(path):
    h=sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def probe(path):
    if not shutil.which('ffprobe'):
        raise RuntimeError('ffprobe required')
    try:
        raw=subprocess.check_output(['ffprobe','-v','error','-show_entries',
            'format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels',
            '-of','json',str(path)],text=True)
        result=json.loads(raw)
        video=next(s for s in result['streams'] if s['codec_type']=='video')
        audio=next((s for s in result['streams'] if s['codec_type']=='audio'),None)
        return {'duration':float(result['format']['duration']),
                'width':video['width'],'height':video['height'],
                'video_codec':video['codec_name'],'fps':video['r_frame_rate'],
                'audio_codec':audio['codec_name'] if audio else None}
    except (KeyError,ValueError,StopIteration,subprocess.CalledProcessError) as e:
        raise RuntimeError('Invalid video input') from e


def check_master(path):
    x=probe(path)
    if abs(x['duration']-40)>0.15 or (x['width'],x['height'])!=(360,640) or x['video_codec']!='h264':
        raise DataBlocked('Expected exact 40s 360×640 approved visual master')
    return x


def extract_originals(master,output):
    """Write 10 independent 4-second clips; never alter the approved original."""
    master=Path(master).resolve();output=Path(output)
    check_master(master)
    (output/'original_clips').mkdir(parents=True,exist_ok=True)
    (output/'starting_frames').mkdir(exist_ok=True)
    for n in range(1,SCENE_COUNT+1):
        clip=output/'original_clips'/f'scene_{n:02d}.mp4'
        _run(['ffmpeg','-nostdin','-y','-loglevel','error','-ss',str((n-1)*4),'-i',str(master),
              '-t','4','-map','0:v:0','-map','0:a?','-c:v','libx264','-preset','veryfast',
              '-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k',
              '-ar','48000','-movflags','+faststart',str(clip)])
        frame=output/'starting_frames'/f'scene_{n:02d}.png'
        _run(['ffmpeg','-nostdin','-y','-loglevel','error','-ss','0.2','-i',str(clip),
              '-frames:v','1',str(frame)])
    (output/'data').mkdir(exist_ok=True)
    (output/'data'/'original_master_evidence.json').write_text(json.dumps({
        'master_sha256':file_hash(master),'duration_seconds':40,'fps':24,
        'note':'Original source preserved; all cuts are separate derivative files.'},indent=2)+'\n')
    return output


def _normalize(src,out):
    x=probe(src)
    if abs(x['duration']-4)>0.3:
        raise DataBlocked(f'Replacement clip must be approximately 4 seconds: {src}')
    if x['audio_codec']:
        cmd=['ffmpeg','-nostdin','-y','-loglevel','error','-i',str(src),'-t','4',
            '-map','0:v:0','-map','0:a:0']
    else:
        cmd=['ffmpeg','-nostdin','-y','-loglevel','error','-i',str(src),
            '-f','lavfi','-i','anullsrc=channel_layout=stereo:sample_rate=48000',
            '-t','4','-map','0:v:0','-map','1:a:0']
    cmd+=['-vf','fps=24,scale=360:640:force_original_aspect_ratio=decrease,'
           'pad=360:640:(ow-iw)/2:(oh-ih)/2,setsar=1',
           '-af','aresample=async=1:first_pts=0,apad',
           '-c:v','libx264','-preset','medium','-crf','16','-pix_fmt','yuv420p',
           '-c:a','aac','-ar','48000','-ac','2','-b:a','192k',
           '-movflags','+faststart','-shortest',str(out)]
    _run(cmd)
    after=probe(out)
    if abs(after['duration']-4)>0.12 or (after['width'],after['height'])!=(360,640):
        raise DataBlocked('Normalized video duration / size mismatch')


def assemble(master, handoff, replacements, approvals, output, *, require_all=True):
    """Replace only approved Flow video clips, never draw product cards.

    The compiled visual is *not* current-price certified for publishing:
    old recorded prices must be independently refreshed immediately before publication.
    """
    master=Path(master).resolve();output=Path(output).resolve()
    if master==output:
        raise DataBlocked('Never overwrite source master')
    check_master(master)
    root=Path(handoff)
    doc=json.loads((root/'data'/'verified_receipt.json').read_text())
    # Allow a historically valid receipt for post-edit assembly; approval must
    # not be mistaken for present-time or pre-publish live price verification.
    from datetime import timezone
    historical=datetime.fromisoformat(doc['checked_at'].replace('Z','+00:00'))
    check_receipt(doc, now=historical, allow_demo=False)
    handshake=json.loads((root/'data'/'flow_handoff_manifest.json').read_text())
    if handshake.get('verified_receipt_sha256')!=doc['snapshot_sha256']:
        raise DataBlocked('Prompt bundle does not match receipt')
    approvals=json.loads(Path(approvals).read_text())
    entries=approvals.get('scenes') or {}
    replacements=Path(replacements)
    mandatory=DYNAMIC if require_all else tuple(int(k) for k in entries.keys())
    if require_all and set(mandatory)!=set(int(x) for x in entries.keys()):
        raise DataBlocked('All 6 dynamic scenes require approval (4,5,7,8,9,10)')
    approved={}
    for scene in mandatory:
        if scene not in DYNAMIC:
            raise DataBlocked('Cannot replace this fixed storytelling scene')
        ent=entries.get(str(scene))
        if not isinstance(ent,dict) or ent.get('receipt_sha256')!=doc['snapshot_sha256']:
            raise DataBlocked('Missing approval or receipt mismatch')
        for key in ('character_ok','visual_quality_ok','product_match_ok','facts_text_ok','hindi_audio_ok','continuity_ok'):
            if ent.get(key) is not True:
                raise DataBlocked(f'Scene {scene} QA not approved: {key}')
        clip=replacements/f'scene_{scene:02d}.mp4'
        if not clip.is_file() or file_hash(clip)!=ent.get('sha256'):
            raise DataBlocked(f'Approved scene {scene} binary missing or altered')
        approved[scene]=clip
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='tf-premium-flow-') as td:
        folder=Path(td)
        clips=[]
        for scene in range(1,SCENE_COUNT+1):
            src=approved.get(scene)
            if src is None:
                src=root/'original_clips'/f'scene_{scene:02d}.mp4'
                if not src.is_file():
                    raise DataBlocked(f'Missing original scene clip {scene}')
            temp=folder/f'part_{scene:02d}.mp4'
            _normalize(src,temp)
            clips.append(temp)
        concat=folder/'concat.txt'
        concat.write_text(''.join(f"file '{p.as_posix()}'\n" for p in clips))
        _run(['ffmpeg','-nostdin','-y','-loglevel','error','-f','concat','-safe','0',
              '-i',str(concat),'-c','copy','-movflags','+faststart',str(output)])
    x=probe(output)
    if abs(x['duration']-40)>0.35:
        output.unlink(missing_ok=True)
        raise DataBlocked('Compiled output must remain 40 seconds')
    metadata={"status":"UNPUBLISHED_VISUAL_REVIEW_NOT_LIVE_PRICE_CERTIFIED",
              "source_master_sha256":file_hash(master),"assembled_mp4_sha256":file_hash(output),
              "verified_receipt_sha256":doc['snapshot_sha256'],
              "replaced_scenes":sorted(approved),"duration":x['duration'],
              "warning":"Snapshot ages; refresh product prices again before each publication. No scheduler/publishing."}
    output.with_suffix('.receipt.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata
