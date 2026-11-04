"""Apply text and product-area overlays to the existing corrected review."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

source, checkpoint, output = map(Path, sys.argv[1:])
output.mkdir(exist_ok=True)
qa = json.loads((source / 'FINAL_QA.json').read_text())
products = json.loads((checkpoint / 'inputs/products.json').read_text())['products']
video = source / 'TrustFolio_35000_Corrected.mp4'
assert hashlib.sha256(video.read_bytes()).hexdigest() == 'e1d6ee71b2ac2a02e5e1b4342927ac34fc100774e183728019c0b31bd5918fee'
assert [p['rank'] for p in products] == [1, 2, 3, 4, 5]
assert qa['chapters_preserved'] == 12
latin = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
hindi = '/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf'
cream, brown = '#f5e2b9', '#512d13'
overlays = []

def panel(box):
    layer = Image.new('RGBA', (720, 1280))
    draw = ImageDraw.Draw(layer)
    draw.rectangle(box, fill=cream)
    return layer, draw

def label(draw, xy, value, size, width=164, font=latin):
    face = ImageFont.truetype(font, size)
    while draw.textlength(value, font=face) > width and size > 16:
        size -= 1
        face = ImageFont.truetype(font, size)
    assert draw.textlength(value, font=face) <= width, value
    draw.text(xy, value, font=face, fill=brown)

def add(layer, start, end):
    path = output / f'overlay_{len(overlays)}.png'
    layer.save(path)
    overlays.append((path, start, end))

layer, draw = panel((470, 60, 695, 255))
label(draw, (478, 70), '₹35,000', 43, 210)
label(draw, (478, 118), 'के बजट में', 31, 210, hindi)
label(draw, (478, 158), 'TOP 5', 34, 210)
label(draw, (478, 203), 'WASHING MACHINES', 20, 210)
add(layer, 12.041667, 16.041667)
models = {1: 'WW70R22EK0X/TL', 3: 'WGA14200IN', 4: 'XS8014BWME'}
photo_proofs = json.loads((checkpoint / 'review/TrustFolio_Washing_Machines_35000_Complete_Review.mp4.qa.json').read_text())['photos']
for product, timing, proof in zip(products, qa['timing'], photo_proofs, strict=True):
    rank = product['rank']
    assert rank == timing['rank'] == proof['rank']
    assert product['product_id'] == proof['product_id']
    specs = {s['label']: s['value'] for s in product['specifications']}
    layer, draw = panel((468, 43, 719, 1250))
    label(draw, (480, 58), f'#{rank} {product["brand"]}', 29, 201)
    label(draw, (480, 99), f'{specs["Capacity"]} · {specs["Load Type"]}', 25, 205)
    label(draw, (480, 134), models.get(rank, 'Model unverified'), 22, 205)
    path = checkpoint / f'review/rank_{rank:02d}_source.png'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == proof['sha256']
    pic = Image.open(path).convert('RGBA')
    white = Image.new('RGBA', pic.size, 'white')
    white.alpha_composite(pic)
    rgb = white.convert('RGB')
    mask = ImageChops.difference(rgb, Image.new('RGB', rgb.size, 'white')).convert('L').point(lambda x: 255 if x > 24 else 0)
    if mask.getbbox():
        rgb = rgb.crop(mask.getbbox())
    rgb = ImageOps.contain(rgb, (207, 290), Image.Resampling.LANCZOS)
    layer.paste(rgb, (480 + (207-rgb.width)//2, 177 + (290-rgb.height)//2))
    label(draw, (480, 490), f'₹{product["price_inr"]:,.0f}', 40)
    provenance = product['price_label']
    assert provenance in ('LIVE', 'CATALOG - UNVERIFIED')
    label(draw, (480, 540), provenance.split(' - ')[0], 23)
    y = 575
    if provenance.startswith('CATALOG'):
        label(draw, (480, y), 'Not live-verified', 19)
        y += 35
    labels = {'Capacity':'Capacity','Load Type':'Load','Automation Type':'Operation','Washing Machine Type':'Operation','Energy Rating':'Energy','Wash Features':'Heater'}
    for key, value in specs.items():
        label(draw, (480, y), labels[key], 20)
        label(draw, (480, y+24), 'Built-in' if key == 'Wash Features' and value == 'In-built Heater' else 'Fully auto' if value == 'Fully Automatic' else value, 25)
        y += 58
    add(layer, timing['visual_start'], timing['visual_end'])

layer, draw = panel((491, 701, 719, 744))
label(draw, (499, 705), 'Comparison', 29, 210)
add(layer, qa['timing'][-1]['visual_end'], qa['duration_seconds']+1)

def run(*args):
    subprocess.run(args, check=True)

command = ['ffmpeg','-v','error','-y','-i',str(video)]
graph = []
for i, (path, start, end) in enumerate(overlays, 1):
    command += ['-i',str(path)]
    previous = '0:v' if i == 1 else f'v{i-1}'
    graph.append(f"[{previous}][{i}:v]overlay=0:0:enable='gte(t,{start})*lt(t,{end})'[v{i}]")
target = output / 'TrustFolio_35000_Mobile.mp4'
run(*command,'-filter_complex_threads','1','-filter_complex',';'.join(graph),'-map',f'[v{len(overlays)}]','-map','0:a:0','-c:a','copy','-c:v','libx264','-crf','17','-preset','veryfast','-pix_fmt','yuv420p','-movflags','+faststart',str(target))
for name in (video,target):
    result = subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(name)],text=True)
    assert abs(float(result)-qa['duration_seconds'])<.05
def audio_hash(path):
    return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-c','copy','-f','hash','-'])
assert audio_hash(video)==audio_hash(target)
frames = [13]+[(r['visual_start']+r['visual_end'])/2 for r in qa['timing']]+[67]
for i,t in enumerate(frames):
    run('ffmpeg','-v','error','-y','-ss',str(t),'-i',str(target),'-frames:v','1','-vf','scale=360:640',str(output/f'mobile_{i}.png'))
(output/'mobile_qa.json').write_text(json.dumps({'audio_packets_identical':True,'source_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'duration_seconds':qa['duration_seconds'],'model_unverified_ranks':[2,5],'mobile_frame_times':frames,'overlay_safe_area_note':'Product details terminate before x=322 and y=460 at 360px. Reel UI varies by device.','audio_lip_sync_reviewed':False},indent=2))
for path,_,_ in overlays:
    path.unlink()
