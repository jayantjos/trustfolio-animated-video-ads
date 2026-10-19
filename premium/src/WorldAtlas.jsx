import React from "react";
import {AbsoluteFill,useCurrentFrame,useVideoConfig} from "remotion";
import manifest from "../../config/world_motion_20.json";

const worlds=Object.fromEntries(manifest.enabled_worlds.map(x=>[x.slug,x]));
const r=(x,y,w,h,fill,rx=18)=><rect x={x} y={y} width={w} height={h} rx={rx} fill={fill} stroke="rgba(255,255,255,.68)" strokeWidth="6"/>;
const c=(x,y,rad,fill)=><circle cx={x} cy={y} r={rad} fill={fill} stroke="rgba(255,255,255,.62)" strokeWidth="6"/>;
const label=(x,y,size,value,color="#FFFFFF")=><text x={x} y={y} textAnchor="middle" fontFamily="'DejaVu Sans', sans-serif" fontWeight="900" fontSize={size} fill={color}>{value}</text>;

function Landmarks({kind,gold,pale,dark,t}){
 switch(kind){
 case "bubble-laundry-road":
   return <g>{[0,1,2].map(i=><g key={i}>
     <path d={"M"+(100+i*340)+" 655 l110 -250 l115 250Z"} fill={i%2?gold:pale} stroke="#FFFFFF" strokeWidth="12"/>
     {r(123+i*340,609,196,177,"#FFFDF4",17)}{c(221+i*340,699,65,dark)}
     {c(221+i*340,699,50,pale)}
   </g>)}{[0,1,2,3].map(i=>c(130+i*244,249+Math.sin(t+i)*40,28+i*4,"rgba(255,255,255,.38)"))}</g>;
 case "neon-city":
   return <g>{[0,1,2,3,4].map(i=><g key={i}>{r(81+i*202,316-i%2*83,166,455,dark,12)}
       {[0,1,2,3].map(j=>r(103+i*202,369-i%2*83+j*80,77,39,j%2?gold:pale,5))}</g>)}
     {r(420,333,236,322,pale,25)}{label(538,501,88,"5G",dark)}</g>;
 case "summer-rescue":
   return <g>{c(853,213,116,gold)}{r(128,491,349,313,"#FCEADB",22)}
     <path d="M88 491 l211 -198 l222 198Z" fill={dark}/>
     {r(556,390,340,313,"#D0F8FF",90)}{r(608,437,239,130,pale,45)}
     {[0,1,2].map(i=><path key={i} d={"M621 "+(598+i*42)+" q124 -50 235 -8"} fill="none" stroke="#FFFFFF" strokeWidth="13"/>)}</g>;
 case "desert-carnival":
   return <g><path d="M0 690 Q280 470 515 676 Q764 502 1080 705 V890 H0Z" fill={gold}/>
     <path d="M180 687 L343 340 L500 687Z" fill={dark}/>{r(680,562,242,151,pale)}
     {[0,1,2].map(i=>c(723+i*79,737,26,"#735E73"))}</g>;
 case "wind-stadium":
   return <g><ellipse cx="540" cy="657" rx="472" ry="195" fill={pale} stroke="#FFFFFF" strokeWidth="17"/>
     {[0,1,2].map(i=><ellipse key={i} cx="540" cy="657" rx={407-i*91} ry={149-i*35}
       stroke={i%2?gold:dark} strokeWidth="21" fill="none"/>)}
     {[0,1,2].map(i=><path key={i} d={"M"+(148+i*320)+" 464 q92 -206 165 -47"} stroke="#FFFFFF" strokeWidth="17" fill="none"/>)}</g>;
 case "pixel-office":
   return <g>{[0,1,2,3,4].map(i=><g key={i}>{r(91+i*195,301+(i%2)*78,164,442,dark,9)}
      {[0,1,2,3].map(j=>r(117+i*195,357+(i%2)*78+j*82,89,40,j%2?gold:pale,4))}</g>)}
      {r(426,467,224,183,pale,20)}{label(536,580,75,"</>",dark)}</g>;
 case "sky-post-office":
   return <g>{[0,1,2,3].map(i=><g key={i}>{c(173+i*270,617-i%2*115,109,"#FFFFFF")}{c(250+i*240,641-i%2*115,92,"#F7FDFF")}</g>)}
     {r(355,361,360,323,pale,30)}<path d="M332 389 L532 205 L734 389Z" fill={gold}/>
     {r(429,460,207,109,gold)}{label(540,535,75,"MAIL",dark)}</g>;
 case "crystal-water-village":
   return <g><path d="M0 734 Q290 540 528 689 Q765 521 1080 719 V934 H0Z" fill={pale}/>
       {[0,1,2,3,4].map(i=><path key={i} d={"M"+(98+i*212)+" 718 l75 -365 l78 365Z"} fill={i%2?gold:"#D8F5FF"} stroke="#FFFFFF" strokeWidth="10"/>)}
       {c(534,302,130,"#E9FBFF")}{c(534,302,87,dark)}</g>;
 case "winter-lodge":
   return <g><path d="M0 720 L245 337 L491 697 L760 298 L1080 720 V880 H0Z" fill="#F6FCFF"/>
     {r(319,472,469,285,dark)}<path d="M260 503 L548 302 L821 503Z" fill={gold}/>
     {r(415,579,172,178,pale)}{r(664,302,89,127,gold)}
     {[0,1,2].map(i=>c(745+i*22,282-i*41,30,"#FFFFFF"))}</g>;
 case "beat-street":
   return <g>{[0,1,2,3,4].map(i=><g key={i}>{r(92+i*185,374+i%2*48,163,401,dark,26)}
      {c(170+i*185,547+i%2*48,38,gold)}{c(170+i*185,680+i%2*48,57,pale)}</g>)}
     <path d="M175 231 L532 396 L911 220" fill="none" stroke={gold} strokeWidth="16"/></g>;
 case "space-kitchen":
   return <g>{c(813,223,133,pale)}{c(856,179,31,gold)}
      {r(185,480,741,306,"#E8E8FF",90)}{r(240,549,619,151,pale,40)}
      {[0,1,2].map(i=>c(345+i*198,630,59,dark))}
      <ellipse cx="540" cy="339" rx="196" ry="69" fill={gold}/></g>;
 case "digital-classroom":
   return <g>{r(122,255,838,489,"#FFFDF8",28)}{r(182,330,719,315,dark,12)}
      {label(540,491,84,"A + B = ?",gold)}{r(299,681,488,79,gold)}
      {[0,1,2].map(i=>r(324+i*174,761,42,90,dark,5))}</g>;
 case "snack-theatre":
   return <g>{r(124,240,829,542,dark,40)}
     <path d="M126 246 Q349 414 126 772Z M954 246 Q729 414 954 772Z" fill={pale}/>
     {r(248,355,582,281,gold)}{label(540,490,84,"MOVIE",dark)}
     {[0,1,2,3].map(i=>c(377+i*107,658,26,"#FFFFFF"))}</g>;
 case "masala-studio":
   return <g>{[0,1,2].map(i=><g key={i}>{r(222+i*235,403+i%2*37,196,327,i%2?gold:pale,28)}
      {c(320+i*235,527+i%2*37,81,dark)}{c(320+i*235,650+i%2*37,42,dark)}</g>)}
      <path d="M332 311 Q541 124 752 311" stroke="#FFFFFF" strokeWidth="23" fill="none"/></g>;
 case "ice-kingdom":
   return <g>{[0,1,2,3,4].map(i=><path key={i} d={"M"+(95+i*205)+" 734 l69 -438 l65 438Z"}
      fill={i%2?pale:"#FFFFFF"} stroke="#FFFFFF" strokeWidth="8"/>)}
      {r(338,482,405,255,"#C6F3FF",71)}<path d="M337 504 Q540 250 744 504" stroke="#FFFFFF" strokeWidth="26" fill="none"/></g>;
 case "cinema-city":
   return <g>{[0,1,2,3].map(i=>r(88+i*249,345+i%2*53,188,441,dark,17))}
      {r(238,323,600,276,pale,18)}{r(300,381,475,148,gold)}
      {label(542,485,77,"CINEMA",dark)}
      {[0,1,2,3,4].map(i=>c(333+i*103,293,26,"#FFF4B1"))}</g>;
 case "fitness-arena":
   return <g><ellipse cx="540" cy="632" rx="470" ry="183" fill={pale} stroke="#FFFFFF" strokeWidth="22"/>
      {[0,1,2].map(i=><ellipse key={i} cx="540" cy="632" rx={399-i*78} ry={134-i*23}
       stroke={i%2?gold:dark} strokeWidth="18" fill="none"/>)}
      {r(410,277,261,186,"#FFFFFF",36)}
      <path d="M449 370 h64 l27 -45 l44 86 l33 -41 h39" stroke="#F05B75" strokeWidth="17" fill="none"/></g>;
 case "music-arena":
   return <g>{[0,1,2,3].map(i=><path key={i} d={"M"+(124+i*250)+" 195 l151 481 h-304Z"} fill={gold} opacity=".23"/>)}
      {[0,1,2].map(i=><g key={i}>{r(185+i*271,378,236,419,dark,24)}
       {c(304+i*271,660,76,pale)}{c(304+i*271,483,37,gold)}</g>)}</g>;
 case "sketch-island":
   return <g><path d="M0 726 Q302 532 541 743 Q801 587 1080 758 V888 H0Z" fill={gold}/>
      {r(231,302,605,445,"#FFF9ED",36)}{r(297,361,476,314,pale,17)}
      <path d="M340 458 Q527 307 728 487 Q594 641 361 561Z" fill="none" stroke={dark} strokeWidth="18"/>
      {c(535,520,45,gold)}</g>;
 case "dust-detective":
   return <g>{r(176,356,741,361,pale,61)}{r(207,518,678,154,dark,46)}
     {c(333,727,34,gold)}{c(737,727,34,gold)}
     {c(539,427,118,"rgba(255,255,255,.19)")}
     <path d="M626 509 l144 138" stroke={gold} strokeWidth="37"/>
     {label(539,445,83,"?",gold)}</g>;
 default: return <g>{r(199,411,700,362,pale,74)}{label(540,588,64,kind,dark)}</g>;
 }
}

export const WorldAtlas=({slug="washing-machines"})=>{
 const frame=useCurrentFrame(),{fps}=useVideoConfig(),t=frame/fps;
 const item=worlds[slug];
 if(!item)throw new Error("Unsupported or disabled world: "+slug);
 const {sky,hill,gold,detail}=item.colors;
 return <AbsoluteFill style={{background:sky,overflow:"hidden"}}>
   <svg width="1080" height="1920" viewBox="0 0 1080 1920" style={{position:"absolute",inset:0}}>
     <defs><linearGradient id="skyfill" x1="0" y1="0" x2="0" y2="1">
       <stop offset="0%" stopColor={sky}/><stop offset="100%" stopColor={detail}/></linearGradient>
     </defs>
     {r(0,0,1080,1920,"url(#skyfill)",0)}
     {c(802+Math.sin(t*.55)*9,262,143,gold)}
     {[0,1,2,3].map(i=><g key={i} transform={"translate("+(Math.sin(t*.32+i)*24)+",0)"}>
       <ellipse cx={135+i*284} cy={350+i%2*109} rx="120" ry="38" fill="#FFFFFF" opacity=".65"/>
       {c(175+i*284,324+i%2*109,52,"rgba(255,255,255,.68)")}
     </g>)}
     <path d="M0 916 Q226 685 521 869 Q801 700 1080 879 V1920 H0Z" fill={hill} opacity=".34"/>
     <g transform={"translate("+(Math.sin(t*.5)*13)+","+(Math.sin(t*.45)*7)+")"}>
       <Landmarks kind={item.kind} gold={gold} pale={detail} dark={hill} t={t}/>
     </g>
     <path d="M0 1271 Q455 1012 1080 1211 V1920 H0Z" fill={hill} opacity=".48"/>
     <path d="M0 1460 Q600 1210 1080 1504 V1920 H0Z" fill={detail} opacity=".41"/>
     {[0,1,2,3,4,5,6].map(i=>c(88+i*166,1435+i%3*96+Math.sin(t+i)*21,13+i%3*9,gold))}
     {r(57,60,966,113,"#29195C",35)}{label(539,135,55,"TrustFolio  •  WORLD CONCEPT")}
     {r(66,1701,948,135,"#241848",29)}{label(540,1776,44,slug.replaceAll("-"," ").toUpperCase())}
     {label(540,1823,24,"Category-specific scenery • no product identities","#DFCFFB")}
     {label(540,1891,24,"CONCEPT ENVIRONMENT ONLY  •  NOT FOR PUBLICATION","#3B2B6A")}
   </svg>
 </AbsoluteFill>;
};
