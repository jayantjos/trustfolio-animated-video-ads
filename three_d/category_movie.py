"""TrustFolio original 20-world 3D cartoon scene engine (PRIVATE QA).

Generates genuine Blender mesh geometry and independently articulated product
CATEGORY mascots in a cinematic scene. No made-up retailer models, SKU shapes,
prices, brands or source ranking. Category concepts are NOT approved product ads.

Run:
  blender -b -t 2 --python three_d/category_movie.py -- \
      --category refrigerators --output output/frames --frames 12 --quality 76

Product-specific publication requires a separate reviewed upstream
source-bound 5-item contract with verified features, image-rights and live
prices. This scene library never publishes and has no external network I/O.
"""
import argparse
import json
import math
import random
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from three_d import tropical_laundry as B

MASTER=json.loads((ROOT/"config"/"category_education_30.json").read_text("utf-8"))
WORLDS=json.loads((ROOT/"config"/"world_motion_20.json").read_text("utf-8"))
AVAILABLE={s["backend_slug"]:s for s in MASTER["slots"] if s["enabled"]}
MOTIONS={s["slug"]:s for s in WORLDS["enabled_worlds"]}
assert len(AVAILABLE)==len(MOTIONS)==20

def parse():
    p=argparse.ArgumentParser()
    p.add_argument("--category",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--frames",type=int,default=12)
    p.add_argument("--quality",type=int,default=75)
    p.add_argument("--start-index",type=int,default=1)
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    if args.category not in AVAILABLE or args.category not in MOTIONS:
        raise ValueError("Category slug unsupported or disabled")
    if not 1<=args.frames<=96 or not 50<=args.quality<=100:
        raise ValueError("Frames and render quality out of configured bounds")
    if args.start_index<1:raise ValueError("Invalid start index")
    return args

def rgba(code):
    text=code.lstrip("#")
    return tuple(pow(int(text[i:i+2],16)/255,2.2) for i in (0,2,4))+(1,)

def m(name,col,metal=0,rough=.44):
    return B.mat(name,rgba(col),metal=metal,rough=rough)

def cube(name,xyz,dims,material,bevel=.07,parent=None):
    return B.cube(name,xyz,dims,material,bevel,parent)

def sphere(name,xyz,r,material,parent=None):
    return B.uv(name,xyz,r,material,parent,segments=16,rings=10)

def cylinder(name,xyz,r,d,material,rot=(0,0,0),parent=None):
    return B.cyl(name,xyz,r,d,material,rotation=rot,parent=parent,vertices=16)

def caption(label,position,material,size=.36):
    return B.text_obj("3D typography - "+label,label,position,material,size=size)

def actor_materials(w):
    pal=w["colors"]
    return {
       "shell":[m("mascot candy mint", "#C8FFF4",rough=.24),
                m("mascot shiny blueberry","#B8E2FF",rough=.24),
                m("mascot pastel golden","#FFF0AB",rough=.25),
                m("mascot pastel rose","#FFCEEA",rough=.24),
                m("mascot pastel lilac","#E0C9FF",rough=.25)],
       "ink":m("inky expressive eyes","#1A153F",rough=.29),
       "eye":m("soft eye whites","#FFFFFF",rough=.24),
       "gold":m("trustfolio gold","#FFDB36",metal=.13,rough=.21),
       "purple":m("trustfolio violet","#6326BD",metal=.13,rough=.27),
       "dark":m("navy CTA","#19154B",rough=.28),
       "pink":m("rose mouth","#EE528B",rough=.4),
       "chrome":m("chrome","#DCEBFA",metal=.72,rough=.16),
       "glass":m("blue glass","#173C79",metal=.29,rough=.17),
       "gray":m("midnight gray","#3A426A",rough=.37),
       "aqua":m("holographic aqua","#4BEEEB",rough=.25),
       "sky":m("sky gradient fallback",pal["sky"],rough=.9),
       "ground":m("category landscape",pal["hill"],rough=.72),
       "accent":m("environment accent",pal["gold"],rough=.4),
       "detail":m("environment secondary",pal["detail"],rough=.46),
       "wood":m("warm village wood","#BC7957",rough=.88),
       "white":m("soft white","#FEFBF4",rough=.4),
       "leaf":m("tropical emerald","#28AA66",rough=.83),
    }

def eyewink(parent, mats):
    # All characters have separate mouth, eyes and pupils; they are genuinely
    # modeled 3D features rather than eyes pasted on a stationary flat poster.
    eyes=[]
    for x in (-.19,.19):
        sphere("expressive oversized eye",(x,-.45,1.35),(.122,.046,.14),mats["eye"],parent)
        eyes.append(sphere("animated pupil",(x,-.496,1.34),(.055,.022,.068),mats["ink"],parent))
    mouth=sphere("3D mouth talking",(0,-.48,1.14),(.105,.032,.058),mats["pink"],parent)
    for x in (-.35,.35):
        sphere("cheerful cheek",(x,-.439,1.19),(.057,.016,.029),mats["pink"],parent)
    return mouth,eyes

def earbud_head(parent, mats):
    # Earbuds pair silhouette, one becomes the speaking buddy.
    cube("Earbud charging pod",(0,0,1.12),(.90,.62,.67),mats["shell"][2],.28,parent)
    for x in (-.28,.28):
        sphere("earbud speaker tip",(x,-.29,1.65),(.18,.17,.14),mats["white"],parent)
        cylinder("long earbud stem",(x,-.28,1.44),.085,.42,mats["white"],parent=parent)

def silhouette(slug,parent,mat,mats):
    """20 distinct recognisable category archetype SHAPES, never fake SKU twins."""
    face_front=-.45
    if slug=="washing-machines":
        cube("washer chassis",(0,0,1.16),(.91,.70,1.37),mat,.10,parent)
        B.ring("working washer door",(0,-.39,1.09),.29,.055,mats["chrome"],parent)
        sphere("washer glass drum",(0,-.419,1.09),(.26,.023,.26),mats["glass"],parent)
        cube("washing machine control panel",(0,-.39,1.65),(.7,.04,.17),mats["gray"],.035,parent)
    elif slug=="refrigerators":
        cube("two door fridge",(0,0,1.27),(.91,.7,1.65),mat,.13,parent)
        cube("refrigerator door line",(0,-.383,1.3),(.84,.021,.045),mats["chrome"],.012,parent)
        for z in (.83,1.64):
            cube("refrigerator metallic handle",(.3,-.43,z),(.05,.052,.38),mats["chrome"],.02,parent)
    elif slug in ("smart-phones","tablets","smart-tvs","desktop-computers","laptops","smartwatches"):
        sizes={"smart-phones":(.74,.25,1.30),"tablets":(1.0,.22,1.02),
               "smart-tvs":(1.35,.20,1.01),"desktop-computers":(1.25,.23,.96),
               "laptops":(1.30,.22,.87),"smartwatches":(.75,.27,.95)}
        sx,sy,sz=sizes[slug]
        cube(slug+" solid display body",(0,0,1.20),(sx,sy,sz),mat,.09,parent)
        cube(slug+" active display glass",(0,-sy*.56,1.20),(sx*.88,.025,sz*.82),mats["glass"],.038,parent)
        face_front=-sy*.57
        if slug=="smartwatches":
            cube("watch silicone strap top",(0,0,1.95),(.37,.13,.56),mats["purple"],.08,parent)
            cube("watch strap bottom",(0,0,.46),(.37,.13,.41),mats["purple"],.08,parent)
        elif slug in ("smart-tvs","desktop-computers"):
            cylinder("screen pedestal",(0,0,.52),.09,.30,mats["chrome"],parent=parent)
            cube("screen foot",(0,0,.37),(.65,.48,.085),mats["gray"],.03,parent)
        elif slug=="laptops":
            cube("laptop tilted keyboard base",(0,-.28,.64),(1.32,.78,.11),mats["chrome"],.04,parent)
        elif slug=="smart-phones":
            sphere("smartphone camera lens",(-.25,-.14,1.73),.075,mats["chrome"],parent)
    elif slug=="headphones-earbuds":
        earbud_head(parent,mats)
        face_front=-.37
    elif slug=="ceiling-fans":
        sphere("fan motor centre",(0,0,1.26),(.32,.33,.39),mat,parent)
        for i in range(4):
            a=i*math.pi*.5
            wing=cube("ceiling fan aero blade",(math.cos(a)*.72,math.sin(a)*.72,1.45),
               (1.13,.24,.08),mats["chrome"],.11,parent)
            wing.rotation_euler[2]=a
        face_front=-.32
    elif slug=="drones":
        cube("drone fuselage",(0,0,1.17),(.91,.60,.48),mat,.17,parent)
        for x in (-.61,.61):
            for y in (-.48,.48):
                cylinder("drone stabilising arm",(x*.53,y*.53,1.34),.055,.63,mats["gray"],rot=(0,math.pi/2,0),parent=parent)
                cylinder("drone propeller hub",(x,y,1.42),.17,.05,mats["chrome"],parent=parent)
                cube("propeller blade",(x,y,1.45),(.56,.09,.02),mats["gold"],.035,parent)
        face_front=-.34
    elif slug=="air-conditioners":
        cube("wall AC sleek housing",(0,0,1.27),(1.33,.55,.68),mat,.17,parent)
        cube("cold airflow louvre",(0,-.30,1.02),(1.20,.035,.15),mats["glass"],.028,parent)
        face_front=-.31
    elif slug=="air-coolers":
        cube("air-cooler tall body",(0,0,1.15),(.89,.67,1.38),mat,.13,parent)
        for j in range(5):
            cube("cooler front cooling vent",(0,-.355,1.46-j*.105),(.72,.035,.055),mats["gray"],.01,parent)
    elif slug=="speakers":
        cube("speaker cabinet",(0,0,1.16),(.81,.67,1.42),mat,.15,parent)
        for z,r in ((.88,.26),(1.50,.115)):
            cylinder("speaker driver",(0,-.38,z),r,.08,mats["gray"],rot=(math.pi/2,0,0),parent=parent)
            cylinder("speaker glowing ring",(0,-.44,z),r*.78,.019,mats["aqua"],rot=(math.pi/2,0,0),parent=parent)
    elif slug=="water-purifiers":
        cube("water filter dispenser",(0,0,1.21),(.84,.66,1.35),mat,.17,parent)
        cylinder("filtration window",(0,-.365,.91),.15,.06,mats["aqua"],rot=(math.pi/2,0,0),parent=parent)
        cube("water dispensing recess",(0,-.37,1.10),(.4,.05,.19),mats["glass"],.037,parent)
    elif slug=="geysers":
        cylinder("water heater cylinder",(0,0,1.22),.47,1.44,mat,parent=parent)
        cube("heater touch dial",(0,-.48,1.05),(.36,.035,.29),mats["gray"],.07,parent)
    elif slug=="microwave-ovens":
        cube("microwave body",(0,0,1.13),(1.10,.72,.89),mat,.10,parent)
        cube("microwave glass door",(-.12,-.393,1.11),(.72,.029,.66),mats["glass"],.04,parent)
        cube("microwave digital control",(.43,-.4,1.17),(.14,.025,.49),mats["gray"],.04,parent)
    elif slug=="mixer-grinders":
        cube("grinder base",(0,0,.83),(.82,.60,.65),mat,.14,parent)
        cylinder("steel mixing jar",(0,0,1.47),.29,.90,mats["chrome"],parent=parent)
        cube("mixer jar cap",(0,0,1.97),(.70,.57,.10),mats["gray"],.04,parent)
    elif slug=="induction-cooktops":
        cube("cooktop tilted cooking surface",(0,0,1.04),(1.28,.79,.26),mat,.09,parent)
        B.ring("cooktop copper burner ring",(0,-.40,1.14),.27,.024,mats["gold"],parent)
        cube("cooktop LED display",(.35,-.43,.98),(.21,.013,.095),mats["glass"],.012,parent)
    elif slug=="vacuum-cleaners":
        cylinder("vacuum cleaner canister",(0,0,1.1),.40,1.06,mat,parent=parent)
        cylinder("vacuum long hose",(0,-.15,1.9),.07,.92,mats["gray"],rot=(.20,0,0),parent=parent)
        sphere("vacuum joint",(0,-.18,1.55),.17,mats["chrome"],parent)
    else:
        raise ValueError("No genuine procedural category silhouette: "+slug)
    return face_front

def actor(slug,index,x,mats):
    center=B.empty("animated "+slug+" cartoon friend "+str(index+1),(x,0,0))
    shell=mats["shell"][index]
    face_front=silhouette(slug,center,shell,mats)
    # Eyes on the dominant plane of the object, separate expressive rig meshes.
    eyes=[]
    for ex in (-.19,.19):
        sphere("friend eye", (ex,face_front-.07,1.42),(.10,.035,.12),mats["eye"],center)
        eyes.append(sphere("animated pupil", (ex,face_front-.115,1.43),(.041,.019,.060),mats["ink"],center))
    mouth=sphere("expressive mouth", (0,face_front-.09,1.27),(.09,.021,.065),mats["pink"],center)
    limbs=[]
    legs=[]
    for direction in (-1,1):
        a=B.empty("arm hinge",(direction*.45,0,1.23),center)
        cylinder("animated sleeve",(direction*.32,-.1,-.01),.077,.58,mats["purple"],rot=(0,math.pi/2,0),parent=a)
        sphere("cartoon white glove",(direction*.6,-.12,-.05),(.127,.123,.1),mats["white"],a)
        limbs.append(a)
        leg=B.empty("walking leg hinge",(direction*.23,0,.54),center)
        cylinder("animated trouser leg",(0,0,-.25),.087,.49,mats["purple"],parent=leg)
        sphere("cartoon shoe",(0,-.08,-.49),(.18,.24,.10),mats["dark"],leg)
        legs.append(leg)
    # Explicitly NOT a product ranking. Source IDs are absent in scenery-only demo.
    return {"root":center,"eyes":eyes,"mouth":mouth,"arms":limbs,"legs":legs}

def scenefx(slug,matset):
    """Unique real depth/shape/objects for each of 20 category worlds."""
    def c(n,x,y,z,sx,sy,sz,key="detail",bv=.055):
        return cube(n,(x,y,z),(sx,sy,sz),matset[key],bv)
    def s(n,x,y,z,rad,key="accent"):
        return sphere(n,(x,y,z),rad,matset[key])
    # Scenic street and sky are common framing; architecture/particles differ.
    if slug=="washing-machines":
        for side in (-1,1):
            for i in range(3):
                c("tropical laundry house",side*6.5,-5+i*6,1.6,2.8,1.8,3,"wood")
                c("laundry cottage cream roof",side*6.5,-5+i*6,3.25,3.1,2.0,.3,"accent")
                for j in range(3):s("soap bubble",side*(4.5+j*.42),-3+i*6,2.2+j*.44,.12,"aqua")
    elif slug=="refrigerators":
        for x in (-6.1,6.1):
            for i in range(4):
                c("frost ice castle pillar",x,-5+i*4,1.8,1.0,1.2,3.6,"detail")
                s("glitter ice snowball",x,-5+i*4,3.9,.32,"white")
        c("frozen ice palace",0,9,2.5,4.5,1.0,5,"aqua")
    elif slug=="smart-phones":
        for side in (-1,1):
            for i in range(5):
                c("neon highrise",side*(5.5+i%2),-8+i*4,2.2,1.2,1.7,4.4,"dark")
                for j in range(4):c("glowing futuristic billboard",side*5.6,-8+i*4,1+j*.75,.65,.12,.28,"aqua")
    elif slug=="headphones-earbuds":
        for side in (-1,1):
            for i in range(4):
                c("concert stacked audio amp",side*5.7,-7+i*5,1.4,1.9,1.0,2.8,"dark")
                for j in range(3):s("woofer bass eye",side*5.7,-7+i*5-.58,1.1+j*.8,.32,"accent")
    elif slug=="smartwatches":
        for side in (-1,1):
            c("fitness stadium seats",side*6.8,0,1.8,3.0,16,2.5,"detail")
            for i in range(5):s("athletic track ribbon lamp",side*4.8,-8+i*4,.7,.28,"accent")
    elif slug=="laptops":
        for side in (-1,1):
            for i in range(4):
                c("digital classroom bookshelf",side*6.4,-7+i*5,1.6,2.2,.5,3.2,"wood")
                for j in range(4):c("colourful learning book",side*6.3,-7+i*5,1+j*.65,.2,.66,.49,"accent")
    elif slug=="smart-tvs":
        for side in (-1,1):
            c("cinema curtains",side*6.6,1,3.5,2,19,7,"purple")
            for i in range(4):s("cinema marquee bulbs",side*5.7,-9+i*5,3.3,.25,"gold")
        c("main theater projection screen",0,9,4,6.6,.3,4.0,"white")
    elif slug=="speakers":
        for side in (-1,1):
            for i in range(4):
                c("concert backstage giant speaker",side*6.1,-6+i*5,2.0,1.4,1.1,3.8,"dark")
                s("bass woofer lighting",side*6.1,-6+i*5-.6,1.5,.53,"aqua")
    elif slug=="air-conditioners":
        for side in (-1,1):
            for i in range(3):
                c("summer cool cafe",side*6.5,-7+i*7,1.6,2.9,1.7,3.1,"white")
                c("cold air window",side*6.5,-8+i*7,1.9,2.1,.11,1.0,"aqua")
        for i in range(10):s("cold air floating crystal",(-1)**i*4.8,i-5,2+.25*i,.18,"aqua")
    elif slug=="air-coolers":
        for side in (-1,1):
            for i in range(4):
                s("desert dune bulb",side*7,-9+i*5,.21,(1.8,1.45,.61),"accent")
                c("desert water cooler tent",side*6.4,-9+i*5,1.2,2,1.4,2.4,"wood")
    elif slug=="water-purifiers":
        for side in (-1,1):
            for i in range(4):
                cylinder("water filtration crystal towers",(side*6.0,-7+i*5,1.8),.48,3.6,matset["aqua"])
                for j in range(2):s("glass drinking droplet",side*5.2,-7+i*5,1.5+j*.8,.32,"white")
    elif slug=="geysers":
        for side in (-1,1):
            for i in range(4):
                c("winter wooden spa hut",side*6.4,-8+i*6,1.4,2.2,2.0,2.8,"wood")
                for j in range(3):s("steam puff",side*5.8,-8+i*6,3+j*.45,.25,"white")
    elif slug=="microwave-ovens":
        for side in (-1,1):
            c("movie snack theater kiosk",side*6.5,0,2.5,2.0,13,5.0,"wood")
            for i in range(5):s("popcorn snack floating sphere",side*4.8,-8+i*3.7,3,.25,"gold")
    elif slug=="mixer-grinders":
        for side in (-1,1):
            for i in range(4):
                cylinder("masala spice jar",(side*5.9,-6+i*5,1),.42,2,matset["gold"])
                s("spicy tomato dancing",(side*5.2,-6+i*5,2.5),.45,"accent")
    elif slug=="induction-cooktops":
        for side in (-1,1):
            for i in range(4):
                c("floating space cafe island",side*6.0,-7+i*4,1.1,2.4,1.4,.4,"detail")
                s("ringed cooking planet",side*6.1,-7+i*4,2.6,.48,"aqua")
    elif slug=="tablets":
        for side in (-1,1):
            for i in range(4):
                c("creative art sketchboard",side*6.2,-8+i*5,1.5,2.1,.16,2.8,"white")
                for j in range(4):s("rainbow art ink drop",side*(5.2+j*.4),-8+i*5,3+j*.18,.15,"accent")
    elif slug=="vacuum-cleaners":
        for side in (-1,1):
            for i in range(4):
                c("detective apartment sofa",side*6.2,-8+i*5,.8,2.4,1.1,1.5,"wood")
                s("dust villain swirling",side*5.2,-8+i*5,2.6,.42,"gray")
    elif slug=="ceiling-fans":
        for side in (-1,1):
            for i in range(3):
                cylinder("wind arena tall pole",(side*6,-6+i*6,2.3),.12,4.6,matset["white"])
                for j in range(3):
                    p=c("wind race bunting ribbon",side*(5.8+j*.40),-6+i*6,4.6,.73,.10,.05,"accent")
                    p.rotation_euler[2]=.31*j
    elif slug=="desktop-computers":
        for side in (-1,1):
            for i in range(4):
                c("pixel office data center",side*6.5,-8+i*5,1.6,2.1,1.6,3.2,"dark")
                for j in range(3):c("server LED dot",side*5.5,-8+i*5,1+j*.8,.23,.04,.12,"aqua")
    elif slug=="drones":
        for side in (-1,1):
            for i in range(4):
                s("flying cloud",side*5.9,-7+i*5,2.6,(1.3,.68,.39),"white")
                c("delivery cloud mailbox",side*6.0,-7+i*5,3.5,.8,.7,.7,"gold")
    else:raise ValueError("Missing environment for "+slug)

def sky_road(mats,slug):
    cube("pastel scenic physical sky cyclorama",(0,18,13),(45,.2,29),mats["sky"],0)
    cube("fully 3D ground surface",(0,0,-.17),(55,55,.31),mats["ground"],0)
    cube("category adventure boulevard",(0,1,.012),(9,50,.076),mats["detail"],0)
    for i in range(-10,18):
        cube("premium golden road line",(0,-1+i*1.6,.052),(.105,.7,.015),mats["gold"],0)
    for side in (-1,1):
        cube("cream safety curb",(side*4.48,1,.13),(.12,50,.28),mats["white"],.02)
    for i in range(11):
        for side in (-1,1):
            if i%2==0:sphere("golden bokeh scenic orb",(side*5.0,i*3-8,.7),(.18,.2,.25),mats["gold"])
    scenefx(slug,mats)

def add_lights_camera(mats,quality):
    scene=bpy.context.scene
    engines=[p.identifier for p in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    if "BLENDER_EEVEE_NEXT" in engines:scene.render.engine="BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in engines:scene.render.engine="BLENDER_EEVEE"
    else:
        scene.render.engine="CYCLES"
        scene.cycles.samples=10
    scene.render.resolution_x=540
    scene.render.resolution_y=960
    scene.render.resolution_percentage=quality
    scene.render.fps=12
    scene.render.film_transparent=False
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGB"
    try:scene.view_settings.view_transform="AgX"
    except Exception:scene.view_settings.view_transform="Filmic"
    for look in ("AgX - Medium High Contrast","Medium High Contrast","AgX - Base Contrast"):
        try:
            scene.view_settings.look=look
            break
        except (ValueError,TypeError):
            pass
    w=bpy.data.worlds.new("bright saturated studio global illumination")
    w.use_nodes=True
    w.node_tree.nodes["Background"].inputs["Color"].default_value=(.35,.52,.75,1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value=.65
    scene.world=w
    sun=bpy.data.lights.new("Warm sunny cinematic light","SUN")
    sun.energy=2.7;sun.color=(1,.88,.76)
    so=bpy.data.objects.new("Warm sunny cinematic light",sun)
    bpy.context.collection.objects.link(so)
    so.rotation_euler=(.40,-.45,-.37)
    def softbox(name,pos,power,color,sz):
        data=bpy.data.lights.new(name,"AREA")
        data.energy=power;data.shape="DISK";data.size=sz;data.color=color
        o=bpy.data.objects.new(name,data)
        bpy.context.collection.objects.link(o)
        o.location=pos;o.rotation_euler=(-Vector(pos)).to_track_quat("-Z","Y").to_euler()
    softbox("turquoise cinema fill",(-6,-8,10),1400,(.65,.84,1),9)
    softbox("warm amber rim",(5,4,9),1800,(1,.78,.56),8)
    cam_d=bpy.data.cameras.new("floating Dolly portrait lens")
    cam=bpy.data.objects.new("floating Dolly portrait lens",cam_d)
    bpy.context.collection.objects.link(cam)
    cam.location=(0,-14.2,4.03)
    aim=Vector((0,1.45,1.38))
    cam.rotation_euler=(aim-Vector(cam.location)).to_track_quat("-Z","Y").to_euler()
    cam_d.type="PERSP";cam_d.lens=34
    cam_d.dof.use_dof=True;cam_d.dof.focus_distance=16.2;cam_d.dof.aperture_fstop=9
    scene.camera=cam
    return cam

def main():
    args=parse()
    random.seed(1234)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    item=AVAILABLE[args.category]
    motion=MOTIONS[args.category]
    materials=actor_materials(motion)
    sky_road(materials,args.category)
    actors=[]
    for i in range(5):
        x=-3.36+i*1.68
        actors.append(actor(args.category,i,x,materials))
    # Props are in full THREE dimensions with camera motion, cast shadows.
    scene=bpy.context.scene
    cam=add_lights_camera(materials,args.quality)
    target=Path(args.output).resolve()
    target.mkdir(parents=True,exist_ok=True)
    metadata={"slug":args.category,"category_name":item["name"],
      "title":item["theme"],"world_kind":motion["kind"],
      "actress_mascot_count":len(actors),"source_product_count":0,
      "original_ranked_product_claims":False,
      "creative_world":motion["landmark"],
      "source_category_id":item["backend_category_id"],
      "allowed_in_public_ads":False,"production_approved":False,
      "watermark":"CATEGORY CONCEPT - NO VERIFIED PRODUCT OFFERS - NOT FOR PUBLICATION",
      "engine":"Blender 4 geometry and Eevee rendering","frames":args.frames,
      "fps":12,"quality_percentage":args.quality,"native_render_px":[540,960]}
    (target/"scene-provenance.json").write_text(json.dumps(metadata,indent=2)+"\n")
    for frame in range(1,args.frames+1):
        t=(args.start_index+frame-2)/12
        for i,body in enumerate(actors):
            phase=t*5.8+i*.75
            p=body["root"]
            p.location.y=t*.12+.1*(i%2)
            p.location.z=.085*max(0,math.sin(phase))
            p.rotation_euler[2]=math.sin(phase*.31)*.045
            for k,arm in enumerate(body["arms"]):
                arm.rotation_euler.y=(-1 if k==0 else 1)*(.25+.62*math.sin(phase+k*.9))
            for k,leg in enumerate(body["legs"]):
                leg.rotation_euler.x=.3*math.sin(phase+k*math.pi)
            body["mouth"].scale.z=.6+.25*abs(math.sin(t*7+i))
            for eye in body["eyes"]:
                eye.scale.z=.13 if int((t+i*.13)*17)%51==0 else 1.0
        cam.location.x=.18*math.sin(t*.65)
        cam.location.z=4.03+.05*math.sin(t*.6)
        scene.frame_set(frame)
        scene.render.filepath=str(target/("frame_"+str(frame).zfill(4)+".png"))
        bpy.ops.render.render(write_still=True)
    print("WORLD_3D_RENDER_COMPLETE="+args.category,flush=True)
    print("WORLD_3D_HAS_PRODUCT_CLAIMS=false",flush=True)
    print("WORLD_3D_PUBLICATION_DISABLED=true",flush=True)

if __name__=="__main__":main()
