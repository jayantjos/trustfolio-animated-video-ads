"""Blender 3.6+/4.x: TRUE THREE-DIMENSIONAL Tropical Laundry Parade pilot.

Illustrative 3D washing-machine mascots live in a physically rendered set with
real geometry, correct sun/contact shadows, moving limbs and cinematic camera.
Every real ranked product retains its actual *original* photo on a distinct
3D identity display; stylized mascot is NOT represented as accurate SKU mesh.
Strictly PRIVATE historical-source demo, never publishable.

Run: blender -b --python three_d/tropical_laundry.py -- \
  --story premium/public/story.json --output output/3d_frames --frames 72
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import random
import sys

try:
    import bpy
    from mathutils import Vector
except ImportError:
    raise SystemExit("Run with Blender: blender -b --python three_d/tropical_laundry.py -- ...")

random.seed(20261019)
MATH=math.pi
CREAM=(0.97,.94,.84,1)
WHITE=(.94,.96,1.,1)
INK=(.071,.060,.18,1)
PURPLE=(.27,.075,.63,1)
GOLD=(1.,.69,.13,1)
AQUA=(.19,.80,.86,1)
CORAL=(.96,.35,.43,1)
GREEN=(.18,.48,.28,1)

def parse():
    parser=argparse.ArgumentParser()
    parser.add_argument("--story",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--frames",type=int,default=72)
    parser.add_argument("--resolution",type=int,default=70)
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    if not 1<=args.frames<=96:
        raise ValueError("Pilot length limited to 1..96 frames")
    if not 40<=args.resolution<=100:
        raise ValueError("Render resolution must be between 40 and 100 percent")
    return args

def mat(name,col,metal=0,rough=.33,emission=0):
    m=bpy.data.materials.new(name)
    m.diffuse_color=col
    m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=col
    p.inputs["Metallic"].default_value=metal
    p.inputs["Roughness"].default_value=rough
    if emission:
        try:
            p.inputs["Emission Color"].default_value=col
            p.inputs["Emission Strength"].default_value=emission
        except KeyError:
            p.inputs["Emission"].default_value=col
    return m

def image_mat(name,image_path):
    path=Path(image_path).resolve()
    if not path.exists():
        raise RuntimeError("Authentic product photo missing: "+str(path))
    m=mat(name,WHITE,rough=.67)
    tree=m.node_tree
    p=tree.nodes.get("Principled BSDF")
    image=bpy.data.images.load(str(path),check_existing=True)
    tex=tree.nodes.new("ShaderNodeTexImage")
    tex.image=image
    tex.interpolation="Linear"
    tree.links.new(tex.outputs["Color"],p.inputs["Base Color"])
    return m

def assign(obj,material):
    obj.data.materials.append(material)
    return obj

def bevel(obj,width=.07,segments=3):
    mod=obj.modifiers.new("Soft factory-molded corners","BEVEL")
    mod.width=width;mod.segments=segments
    # Avoid obsolete weighted-normal/autosmooth requirements on Blender 4.0+
    return obj

def cube(name,loc,scale,material,bevel_width=0,parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    obj=bpy.context.object;obj.name=name;obj.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    assign(obj,material)
    if bevel_width:bevel(obj,bevel_width)
    if parent:obj.parent=parent
    return obj

def uv(name,loc,rad,material,parent=None,segments=20,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,radius=1,location=loc)
    obj=bpy.context.object;obj.name=name
    obj.scale=rad if isinstance(rad,tuple) else (rad,rad,rad)
    assign(obj,material)
    if parent:obj.parent=parent
    for p in obj.data.polygons:p.use_smooth=True
    return obj

def cyl(name,loc,rad,depth,material,rotation=(0,0,0),parent=None,vertices=18):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=rad,depth=depth,location=loc,rotation=rotation)
    obj=bpy.context.object;obj.name=name
    assign(obj,material)
    if parent:obj.parent=parent
    bevel(obj,.025,2)
    for poly in obj.data.polygons:poly.use_smooth=True
    return obj

def ring(name,loc,major,minor,material,parent=None):
    bpy.ops.mesh.primitive_torus_add(major_segments=32,minor_segments=10,
      location=loc,rotation=(MATH/2,0,0),major_radius=major,minor_radius=minor)
    obj=bpy.context.object;obj.name=name
    assign(obj,material)
    if parent:obj.parent=parent
    for p in obj.data.polygons:p.use_smooth=True
    return obj

def text_obj(name,body,loc,material,size=.3,align="CENTER",rotation=(MATH/2,0,0),parent=None):
    curve=bpy.data.curves.new(name,"FONT")
    curve.body=str(body);curve.align_x=align
    curve.size=size;curve.extrude=.006;curve.bevel_depth=.002
    obj=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(obj)
    obj.location=loc;obj.rotation_euler=rotation
    assign(obj,material)
    if parent:obj.parent=parent
    return obj

def empty(name,loc,parent=None):
    obj=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(obj)
    obj.location=loc
    if parent:obj.parent=parent
    return obj

def identity_photo(rank,mat_image,parent,mat_gold,mat_dark):
    # A clearly distinct actual product photograph, NOT a faked exact 3D model.
    # Mesh plane faces the -Y camera. Unique source rank is anchored in name.
    base=cube("Actual model photo plaque #"+str(rank),(0,-.54,1.63),(.46,.036,.48),mat_gold,.025,parent)
    plane=cube("Unaltered sourced product image #"+str(rank),(0,-.565,1.63),(.43,.009,.448),mat_image,.0,parent)
    text_obj("source photo caption","REAL PHOTO",(0,-.585,1.37),mat_dark,size=.071,parent=parent)
    return base

def character(product, location, rank, palette, materials, photos):
    px,py=location
    root=empty("Rank "+str(rank)+" true 3D mascot rig",(px,py,0))
    shell=materials["shells"][rank-1]
    trim=materials["silver"]
    body=cube("Lacquer machine body rank "+str(rank),(0,0,1.13),(1.02,.75,1.41),shell,.12,root)
    cube("rounded control fascia",(0,-.406,1.51),(.86,.045,.38),materials["cream"],.035,root)
    cube("machine display",(0,-.44,1.57),(.35,.02,.13),materials["screen"],.018,root)
    for x in (-.35,.37):
        cyl("chrome program dial",(x,-.47,1.47),.061,.035,trim,rotation=(MATH/2,0,0),parent=root)
    ring("chrome front-load drum",(0,-.40,.98),.34,.051,trim,root)
    ring("violet accent drum",(0,-.436,.98),.25,.019,materials["purple"],root)
    uv("dark glossy washer glass",(0,-.444,.98),(.263,.019,.263),materials["glass"],root)
    uv("glass shine",( -.10,-.477,1.086),(.063,.009,.040),materials["shine"],root)
    # expressive face exists as independent moving meshes, never part of source photo
    # Eyes and expressive speaking mouth sit on the front-load drum itself.
    # Their geometry has real depth and independent animation, not a flat sticker.
    eyes=[]
    for eye_x in (-.134,.134):
        uv("bright cartoon eye white",(eye_x,-.49,1.054),(.122,.037,.120),materials["cream"],root)
        eyes.append(uv("animated dark pupil",(eye_x,-.532,1.049),(.052,.030,.074),materials["ink"],root))
    for ch_x in (-.253,.253):
        uv("soft pink cheek",(ch_x,-.495,.856),(.070,.021,.048),materials["blush"],root)
    mouth=uv("large smiling speaking mouth",(0,-.53,.824),(.126,.025,.061),materials["mouth"],root)
    # genuine photo follows same 3D character, always identifiable as photo reference
    identity_photo(rank,photos[rank],root,materials["gold"],materials["ink"])
    # real product brand/rank: text display on 3D molded character, from original source
    brand=str(product.get("brand","Brand"))[:13].upper()
    text_obj("actual rank brand "+str(rank),brand,(0,-.444,1.74),materials["ink"],size=.089,parent=root)
    tag=cube("rank badge gold",(0,-.443,1.84),(.33,.035,.16),materials["gold"],.035,root)
    text_obj("actual position #"+str(rank),"#"+str(rank),(0,-.469,1.795),materials["ink"],size=.12,parent=root)
    feet=[]
    arms=[]
    for direction in (-1,1):
        arm=empty("Gesture arm pivot "+str(rank)+" "+str(direction),(direction*.54,0,1.26),root)
        limb=cyl("articulated purple arm",(direction*.28,-.07,-.045),.072,.56,materials["purple"],
                 rotation=(0,MATH/2,0),parent=arm)
        uv("soft round glove",(direction*.56,-.07,-.08),(.135,.115,.11),materials["cream"],arm)
        arms.append(arm)
        leg=empty("Walking leg pivot "+str(rank)+" "+str(direction),(direction*.24,0,.47),root)
        cyl("moving trouser leg",(0,0,-.20),.092,.40,materials["purple"],parent=leg)
        uv("3D cartoon shoe",(0,-.123,-.46),(.165,.255,.088),materials["navy"],leg)
        feet.append(leg)
    wheels=[]
    return {"root":root,"arms":arms,"legs":feet,"eyes":eyes,"mouth":mouth,"rank":rank,
            "base_y":py}

def palm(x,y,materials,size=1):
    base=empty("Palm tree",(x,y,0))
    trunk=materials["trunk"];leaf=materials["leaf"]
    cyl("tropical palm trunk",(0,0,2.4*size),.17*size,4.8*size,trunk,parent=base)
    for k in range(7):
        a=2*MATH*k/7
        x2=math.cos(a)*1.45*size;y2=math.sin(a)*1.45*size
        uv("broad lush tropical leaf",(x2,y2,4.63*size),(.98*size,.25*size,.10*size),leaf,base)
        obj=bpy.context.object
        obj.rotation_euler=(0,-.20, a+.12)
    for k in range(4):
        uv("coconut",(math.cos(k*MATH/2)*.23*size,math.sin(k*MATH/2)*.23*size,4.6*size),
            .12*size,materials["coconut"],base)

def building(x,y,materials,idx):
    base=materials["huts"][idx%len(materials["huts"])]
    width=2.5+(idx%3)*.35
    height=2.6+(idx%2)*.48
    cube("Village laundry boutique",(x,y,height/2),(width,1.7,height),base,.08)
    roof=cube("village cottage tiled roof",(x,y,height+.26),(width+.34,2.1,.36),materials["roof"],.04)
    roof.rotation_euler[1]=.12 if idx%2 else -.12
    for direction in (-1,1):
        cube("window white surround",(x+direction*.66,y-.88,height*.58),(.45,.065,.65),materials["cream"],.05)
        cube("window reflective",(x+direction*.66,y-.929,height*.58),(.35,.018,.54),materials["glass"],.015)
    cube("boutique door",(x,y-.92,height*.33),(.64,.07,1.6),materials["door"],.045)

def stage(materials):
    cube("tropical sunshine sky visual background",(0,30,13),(80,1,40),materials["sky"])
    cube("physical ground plane",(0,0,-.16),(70,90,.30),materials["grass"],.03)
    for offset,peak in ((-10,3.7),(1,5.1),(11,4.2)):
        bpy.ops.mesh.primitive_cone_add(vertices=6,radius1=4.9,radius2=0,
            depth=peak,location=(offset,16,peak*.42))
        hill=bpy.context.object
        hill.name="Layered tropical mountain real mesh"
        assign(hill,materials["hedge"])

    cube("curving stylized royal lavender road",(0,0,-.006),(10,90,.08),materials["road"],.01)
    for i in range(-9,18):
        cube("road center golden dash",(0.0,i*1.55+.3,.05),(.14,.68,.007),materials["stripe"],.0)
    for x in (-5.02,5.02):
        cube("pavement curb",(x,0,.11),(.16,70,.29),materials["cream"],.025)
    for i,y in enumerate((-10,-4,3,10,17)):
        for side in (-1,1):
            palm(side*(6.4+(i%2)*1.75),y+.45*side,materials,size=.79+(i%3)*.17)
            if i in (0,2,4):
                building(side*10.1,y+4.2,materials,i+(side+1)//2)
    for i in range(28):
        side=-1 if i%2 else 1
        x=side*(5.8+(i%4)*.61);y=-9+i*.83
        uv("flower petal landscaping",(x,y,.08),(.16,.23,.17),materials["flower"],segments=10,rings=8)
        uv("low hedge",(x,y,.14),(.34,.33,.32),materials["hedge"],segments=10,rings=8)
    for i in range(30):
        x=random.uniform(-5.8,5.8);y=random.uniform(-8,13)
        if abs(x)<4.7:continue
        uv("ground leaf detail",(x,y,.13),(.26,.35,.13),materials["hedge"],segments=8,rings=6)
    text_obj("TrustFolio scenic sign","T R U S T F O L I O",(0,8.6,4.75),materials["ink"],.82)

def setup_render(args,materials):
    scene=bpy.context.scene
    if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]:
        scene.render.engine="BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]:
        scene.render.engine="BLENDER_EEVEE"
    else:
        scene.render.engine="CYCLES"
        scene.cycles.samples=12
    scene.render.image_settings.file_format="PNG"
    scene.render.resolution_x=540
    scene.render.resolution_y=960
    scene.render.resolution_percentage=args.resolution
    scene.render.film_transparent=False
    scene.render.image_settings.color_mode="RGB"
    scene.render.image_settings.color_depth="8"
    scene.render.film_transparent=False
    scene.render.use_file_extension=True
    scene.render.use_compositing=False
    scene.render.fps=12
    scene.render.fps_base=1
    # Moderate Eevee CPU workload, physically real geometry/depth/lights.
    if hasattr(scene,"eevee") and hasattr(scene.eevee,"taa_render_samples"):
        scene.eevee.taa_render_samples=16
    try:
        scene.view_settings.view_transform="AgX"
    except Exception:
        scene.view_settings.view_transform="Filmic"
    # Blender 4 AgX look identifiers include "AgX -"; old Filmic uses old labels.
    available=["AgX - Medium High Contrast","Medium High Contrast","AgX - Base Contrast","Medium High Contrast"]
    for look in available:
        try:
            scene.view_settings.look=look
            break
        except (TypeError,ValueError):
            continue
    scene.view_settings.exposure=-.15
    scene.view_settings.gamma=1
    world=bpy.data.worlds.new("Warm tropical daylight world")
    world.use_nodes=True
    world.node_tree.nodes.get("Background").inputs["Color"].default_value=(.38,.57,.78,1)
    world.node_tree.nodes.get("Background").inputs["Strength"].default_value=.8
    scene.world=world
    def area(name,loc,power,col,size):
        obj_data=bpy.data.lights.new(name,"AREA")
        light_obj=bpy.data.objects.new(name,obj_data);bpy.context.collection.objects.link(light_obj)
        light_obj.location=loc;obj_data.energy=power;obj_data.shape="DISK";obj_data.size=size;obj_data.color=col
        rot=Vector((0,0,0))-light_obj.location;light_obj.rotation_euler=rot.to_track_quat('-Z','Y').to_euler()
    sun=bpy.data.lights.new("Warm late-afternoon sun","SUN")
    sobj=bpy.data.objects.new("Warm late-afternoon sun",sun);bpy.context.collection.objects.link(sobj)
    sobj.rotation_euler=(.39,-.44,-.47);sun.energy=2.35
    sun.color=(1,.91,.77)
    if hasattr(sun,"angle"):sun.angle=.12
    area("Aqua softbox fill",(-5,-7,9),1200,(.65,.83,1),8)
    area("Warm rim key",(6,4,9),1700,(1,.80,.57),7)
    camera_data=bpy.data.cameras.new("Cinematic 38mm moving camera")
    cam=bpy.data.objects.new("Cinematic 38mm moving camera",camera_data)
    bpy.context.collection.objects.link(cam)
    cam.location=(0,-11.1,3.57)
    point=Vector((0,-1.40,1.50))
    cam.rotation_euler=(point-Vector(cam.location)).to_track_quat('-Z','Y').to_euler()
    camera_data.type="PERSP";camera_data.lens=35
    camera_data.dof.use_dof=True
    camera_data.dof.focus_distance=9.0
    camera_data.dof.aperture_fstop=11
    scene.camera=cam
    return cam

def validate_story(story,storypath):
    if story.get("status")!="HISTORICAL_DEMO_NOT_FOR_PUBLICATION":
        raise ValueError("3D pilot accepts authenticated historical demo only")
    if story.get("publishing_enabled") is not False:
        raise ValueError("3D public/production use is forbidden")
    if story.get("category")!="washing-machines" or story.get("budget")!=35000:
        raise ValueError("Pinned five-ranked washing machine pilot only")
    ranked=story.get("products")
    if not isinstance(ranked,list) or len(ranked)!=5:
        raise ValueError("Exactly five ranked original models required")
    if [p.get("rank") for p in ranked]!=[1,2,3,4,5]:
        raise ValueError("Source product order must remain 1..5")
    ids=[p.get("id") for p in ranked]
    if len(set(ids))!=5 or ids!=story.get("rankedProductIds"):
        raise ValueError("Original product ID mismatch")
    if not all(p.get("sha256") and p.get("image") for p in ranked):
        raise ValueError("Source photographs/hashes required")
    if not story.get("sourceSha256") or "NOT FOR PUBLICATION" not in story.get("watermark",""):
        raise ValueError("Historical source watermark required")
    images={}
    for p in ranked:
        image=(storypath.parent/p["image"]).resolve()
        if storypath.parent.resolve() not in image.parents:
            raise ValueError("Unsafe product photo path")
        if not image.exists():raise ValueError("Source photograph absent "+str(image))
        images[p["rank"]]=image
    return ranked,images

def materials():
    return {
        "shells":[mat("Royal mint washer",(.48,.88,.77,1),rough=.22),
                  mat("Pearl blue washer",(.48,.71,.95,1),rough=.21),
                  mat("Sunny yellow washer",(1.,.77,.35,1),rough=.23),
                  mat("Blush lavender washer",(.77,.66,.95,1),rough=.2),
                  mat("Powder coral washer",(.99,.62,.62,1),rough=.22)],
        "sky":mat("sky cyclorama",(.39,.72,.94,1),rough=1),
        "grass":mat("lush emerald grass",(.31,.66,.39,1),rough=.89),
        "road":mat("cinematic warm tropical road",(.33,.35,.45,1),rough=.84),
        "stripe":mat("sun yellow center line",(.99,.87,.47,1),rough=.83),
        "silver":mat("bright chrome metal",(.87,.90,.96,1),metal=.80,rough=.15),
        "cream":mat("soft cream white",WHITE,rough=.33),
        "screen":mat("lit fascia glass",(.18,.50,.69,1),metal=.16,rough=.1,emission=.09),
        "glass":mat("dark glass",(.12,.30,.48,1),metal=.5,rough=.12),
        "shine":mat("white specular",(.82,1.,1.,1),rough=.1,emission=.25),
        "ink":mat("ink black",INK,rough=.32),
        "purple":mat("purple arms",PURPLE,rough=.32),
        "gold":mat("rank badge gold",GOLD,metal=.22,rough=.25),
        "navy":mat("navy sneakers",(.21,.17,.4,1),rough=.57),
        "blush":mat("cheek pink",(.95,.37,.51,1),rough=.45),
        "mouth":mat("mouth rose",(.55,.05,.23,1),rough=.4),
        "trunk":mat("warm palm bark",(.45,.27,.13,1),rough=.9),
        "leaf":mat("tropical palm fronds",(.17,.48,.24,1),rough=.57),
        "coconut":mat("coconut shell",(.33,.18,.11,1),rough=.91),
        "huts":[mat("cream cottage",(.99,.89,.73,1),rough=.73),
                mat("pink cottage",(.91,.58,.63,1),rough=.77),
                mat("turquoise cottage",(.31,.77,.74,1),rough=.81)],
        "roof":mat("tile roof",(.78,.38,.29,1),rough=.86),
        "door":mat("cottage door",(.51,.23,.46,1),rough=.5),
        "flower":mat("bright roadside blossom",(.95,.69,.31,1),rough=.87),
        "hedge":mat("hedge green",(.15,.46,.21,1),rough=.94),
    }

def animate(scene,characters,cam,frames):
    # Subtle physically meaningful acting: stepping, waving, blink and mouth.
    for f in range(1,frames+1):
        t=(f-1)/12
        for order,rig in enumerate(characters):
            rank=rig["rank"]
            # Scene flows toward camera, characters perform parade movement
            move=t*.125
            wavephase=t*5.1+order*.58
            rig["root"].location[1]=rig["base_y"]+move
            rig["root"].location[2]=.04*max(0,math.sin(wavephase*2))
            rig["root"].rotation_euler[2]=math.sin(wavephase*.35)*.035
            rig["root"].keyframe_insert(data_path="location",frame=f)
            rig["root"].keyframe_insert(data_path="rotation_euler",frame=f)
            for i,arm in enumerate(rig["arms"]):
                arm.rotation_euler[1]=(-1 if i==0 else 1)*(.18+math.sin(wavephase+i)*.48)
                arm.keyframe_insert(data_path="rotation_euler",frame=f)
            for i,leg in enumerate(rig["legs"]):
                leg.rotation_euler[0]=math.sin(wavephase+i*MATH)*.21
                leg.keyframe_insert(data_path="rotation_euler",frame=f)
            # Mouth speaks in alternating character turns, not false audio sync.
            speak=(int(t/1.25)%5)==order
            rig["mouth"].scale[2]=.028+( .06 if speak else .018)*abs(math.sin(t*14+order))
            rig["mouth"].keyframe_insert(data_path="scale",frame=f)
            for eye in rig["eyes"]:
                eye.scale[2]=.009 if (int(t*5+order*4)%41==0) else .052
                eye.keyframe_insert(data_path="scale",frame=f)
        cam.location[0]=math.sin(t*.36)*.23
        cam.location[2]=3.57+.06*math.sin(t*.46)
        cam.keyframe_insert(data_path="location",frame=f)
    scene.frame_set(1)
    scene.frame_start=1;scene.frame_end=frames

def main():
    args=parse()
    path=Path(args.story).resolve()
    story=json.loads(path.read_text(encoding="utf8"))
    products,images=validate_story(story,path)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    mats=materials()
    mats["photo"]={rank:image_mat("Actual retailer product photo rank "+str(rank),img)
                   for rank,img in images.items()}
    stage(mats)
    characters=[]
    # Stagger real 3D friends in depth: two back, two middle, hero foreground.
    # Reader sees cinematic perspective rather than five tiny figures in one row.
    poses=[(-2.73,.70),(2.73,.70),(-1.97,-1.85),(1.97,-1.85),(0,-5.12)]
    for i,rank in enumerate((5,4,3,2,1)):
        product=products[rank-1]
        rig=character(product,poses[i],rank,mats["shells"][i],mats,mats["photo"])
        if rank==1:
            rig["root"].scale=(1.14,1.14,1.14)
        characters.append(rig)
    cam=setup_render(args,mats)
    scene=bpy.context.scene
    animate(scene,characters,cam,args.frames)
    target=Path(args.output).resolve()
    target.mkdir(parents=True,exist_ok=True)
    scene.render.filepath=str(target)+"/frame_"
    for frame in range(1,args.frames+1):
        scene.frame_set(frame)
        scene.render.filepath=str(target/("frame_"+str(frame).zfill(4)+".png"))
        bpy.ops.render.render(write_still=True)
        if frame==1 or frame==args.frames or frame%12==0:
            print("TRUSTFOLIO_TRUE_3D_FRAME="+str(frame)+"/"+str(args.frames),flush=True)
    print("THREE_D_SOURCE_IDS="+",".join(p["id"] for p in products),flush=True)
    print("THREE_D_HISTORICAL_DEMO_ONLY=true",flush=True)
    print("THREE_D_PRODUCT_MASCOTS_ARE_STYLIZED_NOT_REAL_SKU_MODELS=true",flush=True)

if __name__=="__main__":
    main()
