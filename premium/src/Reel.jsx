import React from "react";
import {AbsoluteFill, Audio, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from "remotion";
import story from "../public/story.json";

const COLORS={
  deep:"#171144", ink:"#232045", plum:"#552BC3", purple:"#7840F5",
  lilac:"#D1BBFF", navy:"#151B4D", blue:"#179DE7", teal:"#45DCE8",
  gold:"#FFD23F", snow:"#F8FDFF", calm:"#E7F6FF"
};
const lerp=(x,a,b,c,d)=>interpolate(x,[a,b],[c,d],{extrapolateLeft:"clamp",extrapolateRight:"clamp"});
const shadow="0 18px 54px rgba(25,19,82,.22)";
const font="'Noto Sans Devanagari','Noto Sans',Arial,sans-serif";
const F=story.fps;
const rankProduct=(rank)=>story.products.find((p)=>p.rank===rank);
const pulse=(sec)=>{
  const idx=Math.max(0,Math.min(story.mouthEnvelope100ms.length-1,Math.floor(sec*10)));
  return story.mouthEnvelope100ms[idx]||0;
};

const Bubble=({i,t})=>{
  const size=20+(i*19)%77;
  const x=(48+i*139+(Math.sin(t*.7+i*1.71)*35))%1150-35;
  const y=(260+i*131-t*(21+i%5*12))%1790;
  return <div style={{
    position:"absolute",left:x,top:y,width:size,height:size,borderRadius:"50%",
    background:"radial-gradient(circle at 25% 24%,rgba(255,255,255,.94),rgba(141,232,255,.21) 47%,rgba(39,146,236,.19) 88%)",
    border:"2px solid rgba(255,255,255,.8)",
    boxShadow:"inset -6px -8px 15px rgba(58,135,240,.13),0 14px 26px rgba(25,101,187,.08)",
    opacity:.80
  }}/>;
};

const LaundryWorld=({t})=><AbsoluteFill style={{
  overflow:"hidden",
  background:"radial-gradient(ellipse at 78% 5%,#FFFFFF 0%,#EBF8FF 31%,#CBEAFE 71%,#A9C8FF 100%)",
}}>
  <div style={{position:"absolute",left:-150,top:290,width:780,height:780,
    background:"radial-gradient(circle,rgba(131,83,244,.28),transparent 66%)",borderRadius:"50%"}}/>
  <div style={{position:"absolute",right:-280,top:500,width:950,height:950,
    background:"radial-gradient(circle,rgba(34,205,244,.36),transparent 67%)",borderRadius:"50%"}}/>
  <div style={{position:"absolute",top:1050,left:-260,width:1600,height:680,
    borderRadius:"50%",background:"linear-gradient(155deg,#EFFBFF 0%,#BFECFD 52%,#C7C5FF 100%)",
    boxShadow:"0 -28px 66px rgba(44,115,206,.15)"}}/>
  <div style={{position:"absolute",top:1210,left:-30,width:1130,height:12,
    background:"linear-gradient(90deg,transparent,#96DBFA,transparent)"}}/>
  {[...Array(20)].map((_,i)=><Bubble key={i} i={i} t={t}/>)}
  <div style={{position:"absolute",top:480,left:33,width:125,height:125,
    borderRadius:"25%",border:"8px solid rgba(255,255,255,.5)",
    transform:"rotate("+Math.sin(t*1.2)*12+"deg)",opacity:.4}}/>
  <div style={{position:"absolute",top:565,right:29,width:128,height:128,
    borderRadius:"48%",border:"9px solid rgba(255,255,255,.55)",
    transform:"scale("+(1+.09*Math.sin(t*1.8))+")",opacity:.55}}/>
</AbsoluteFill>;

const BrandHeader=()=>(
  <div style={{position:"absolute",left:58,top:56,width:964,height:104,zIndex:30,
    background:"linear-gradient(115deg,#271252,#5D2CCE 58%,#7A42FA)",
    borderRadius:34,boxShadow:"0 18px 36px rgba(69,35,143,.20)",
    display:"flex",alignItems:"center",padding:"0 32px",boxSizing:"border-box",
    justifyContent:"space-between",border:"2px solid rgba(255,255,255,.18)"}}>
    <div style={{display:"flex",alignItems:"center",gap:17}}>
      <svg width="58" height="60" viewBox="0 0 58 60" aria-label="concept logo mark">
        <path d="M29 3 L52 12 V32 Q50 47 29 57 Q8 48 6 32 V12Z" fill="#FFD744"/>
        <path d="M16 29 L25 38 L43 19" fill="none" stroke="#45209E" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
      <div style={{fontSize:49,letterSpacing:-2,fontWeight:950,color:"#fff",fontFamily:"Arial,sans-serif"}}>
        Trust<span style={{color:COLORS.gold}}>Folio</span>
      </div>
    </div>
    <div style={{fontSize:19,letterSpacing:3,fontWeight:800,color:"#DED1FF"}}>SMART SHOPPING</div>
  </div>
);

const SectionTitle=({t,scene})=><div style={{position:"absolute",top:190,left:60,width:960,
   zIndex:20,textAlign:"center"}}>
   <div style={{display:"inline-block",background:"#FFE15B",padding:"12px 29px",
     transform:"rotate(-2deg)",borderRadius:12,boxShadow:"0 9px 0 rgba(155,93,20,.16)",
     fontSize:30,fontWeight:950,color:"#32166D",letterSpacing:1.2}}>
     BUBBLE LAUNDRY KINGDOM
   </div>
   <div style={{fontSize:59,fontWeight:950,color:COLORS.deep,marginTop:21,letterSpacing:-1.5,
       textShadow:"0 4px 0 rgba(255,255,255,.72)"}}>
     TOP 5 WASHING MACHINES
   </div>
   <div style={{display:"inline-block",fontSize:36,fontWeight:920,color:COLORS.purple,
       background:"rgba(255,255,255,.83)",border:"2px solid rgba(129,90,223,.17)",
       padding:"5px 24px",borderRadius:22,marginTop:10}}>
     UNDER ₹35,000 <span style={{fontSize:24,color:"#776DA0"}}> • HISTORICAL DEMO</span>
   </div>
 </div>;

const Face=({t,small=false})=>{
  const opening=.15+Math.min(.87,pulse(t)*2);
  const eye=(small?12:17),rx=(small?14:20);
  return <div style={{
    position:"absolute",bottom:small?32:53,left:"50%",transform:"translateX(-50%)",
    width:small?74:120,height:small?47:74,
    display:"flex",alignItems:"center",justifyContent:"space-around",
    background:"linear-gradient(150deg,#F7E8FF,#FFFFFF)",
    border:"3px solid rgba(136,69,236,.20)",borderRadius:999,
    boxShadow:"inset 0 3px 12px rgba(122,58,180,.12)"}}>
    <div style={{width:eye,height:eye+4,borderRadius:"50%",background:COLORS.deep,
      transform:"translateY("+Math.sin(t*7)*2+"px)"}}/>
    <div style={{width:rx+2,height:(small?9:14)+opening*(small?6:20),
      borderRadius:"45% 45% 60% 60%",background:"#EA5E8B",
      border:"2px solid #AE2755"}}/>
    <div style={{width:eye,height:eye+4,borderRadius:"50%",background:COLORS.deep,
      transform:"translateY("+Math.sin(t*7)*2+"px)"}}/>
  </div>;
};

const Buddy=({product,scale=1,x=0,y=0,t=0,hero=false,angle=0,delay=0,opacity=1})=>{
  const bob=Math.sin(t*3.3+delay)*15;
  const wave=Math.sin(t*7.4+delay)*24;
  const sway=Math.sin(t*2.6+delay)*5;
  const width=hero?550:390;
  const height=hero?700:525;
  const friendlyTag=product.brand||product.platform;
  return <div style={{
    position:"absolute",left:x,top:y,width,height,
    transform:"translateY("+bob+"px) rotate("+(angle+sway)+"deg) scale("+scale+")",
    transformOrigin:"center center",opacity,
    filter:hero?"drop-shadow(0 30px 20px rgba(41,54,121,.24))":"drop-shadow(0 12px 10px rgba(41,54,121,.18))"
  }}>
    <div style={{position:"absolute",left:55,top:height*.48,width:140,height:25,borderRadius:20,
      background:"#7948D3",transformOrigin:"right center",
      transform:"rotate("+(-21+wave)+"deg)",zIndex:0}}/>
    <div style={{position:"absolute",right:55,top:height*.48,width:140,height:25,borderRadius:20,
      background:"#7948D3",transformOrigin:"left center",
      transform:"rotate("+(21-wave)+"deg)",zIndex:0}}/>
    {[0,1].map((i)=><div key={i} style={{
      position:"absolute",left:i?width*.59:width*.32,bottom:25,
      width:29,height:72,borderRadius:20,background:"#6544C4",
      transformOrigin:"center top",transform:"rotate("+((i?1:-1)*Math.sin(t*4+delay)*15)+"deg)"}}/>)}
    <div style={{
      position:"absolute",inset:"0 52px 55px",
      background:"linear-gradient(155deg,#FFFFFF 0%,#F9F6FF 68%,#E5E6FF 100%)",
      border:"7px solid #FFFFFF",boxShadow:"inset 0 0 0 3px rgba(117,72,222,.18),"+shadow,
      borderRadius:hero?58:48,zIndex:3,overflow:"visible"}}>
      <div style={{position:"absolute",left:0,top:0,right:0,height:63,borderRadius:"45px 45px 4px 4px",
        background:"linear-gradient(90deg,#6D45CB,#AB7AFF)",display:"flex",
        justifyContent:"center",alignItems:"center",fontSize:hero?27:22,color:"white",fontWeight:950}}>
        {friendlyTag.toUpperCase()}
      </div>
      <Img src={staticFile(product.image)} style={{
        position:"absolute",width:"87%",height:"62%",left:"6.5%",top:"14%",
        objectFit:"contain",mixBlendMode:"multiply"}}/>
      <Face t={t} small={!hero}/>
      <div style={{
        position:"absolute",top:-34,left:-38,width:hero?86:74,height:hero?86:74,
        borderRadius:"50%",background:COLORS.gold,border:"7px solid #fff",
        display:"flex",alignItems:"center",justifyContent:"center",
        color:COLORS.deep,fontSize:hero?41:37,fontWeight:950,
        boxShadow:"0 10px 20px rgba(57,42,141,.25)"}}>
        #{product.rank}
      </div>
    </div>
    <div style={{position:"absolute",bottom:4,left:"50%",transform:"translateX(-50%)",
      width:hero?360:265,height:hero?87:73,borderRadius:29,
      background:"linear-gradient(100deg,#FFD43D,#FFE775)",
      border:"5px solid white",display:"flex",alignItems:"center",justifyContent:"center",
      fontSize:hero?41:32,fontWeight:950,color:COLORS.deep,
      boxShadow:"0 13px 23px rgba(36,27,103,.22)",zIndex:6}}>
      ₹{product.price.toLocaleString("en-IN")}
    </div>
  </div>;
};

const Stars=({t})=><div style={{position:"absolute",inset:0,zIndex:2,pointerEvents:"none"}}>
  {[...Array(15)].map((_,i)=>{
    const a=i*2.399;
    const r=185+i*21;
    const x=540+Math.cos(a+t*.14)*r;
    const y=800+Math.sin(a+t*.22)*r*.87;
    const size=18+(i%4)*11;
    return <div key={i} style={{
      position:"absolute",left:x,top:y,width:size,height:size,
      transform:"rotate("+(t*55+i*31)+"deg)",
      clipPath:"polygon(50% 0, 62% 38%, 100% 50%, 62% 62%, 50% 100%, 38% 62%, 0 50%, 38% 38%)",
      background:i%2?"#FFD74A":"#8A5AF4",opacity:.76
    }}/>;
  })}
</div>;

const IntroScene=({t})=>{
  const products=[5,4,3,2,1].map(rankProduct);
  return <div style={{position:"absolute",top:405,left:0,right:0,height:980,zIndex:10}}>
    <div style={{position:"absolute",top:68,left:80,right:80,textAlign:"center",
      fontSize:48,fontWeight:950,color:COLORS.deep}}>
       कपड़ों का पहाड़? <span style={{color:"#7A45F3"}}>पाँच दोस्त</span> तैयार!
    </div>
    <div style={{position:"absolute",top:139,left:100,right:100,textAlign:"center",
       fontSize:25,color:"#625A91",fontWeight:750}}>A CARTOON SHOWDOWN • REAL PRODUCT RANKS</div>
    {products.map((p,i)=><Buddy key={p.id} product={p} x={i<3?40+i*320:200+(i-3)*340}
       y={i<3?235:650} t={t} scale={i<3?.64:.52}
       angle={i%2?5:-5} delay={i*.9} />)}
  </div>;
};

const BattleScene=({t,rank})=>{
  const p=rankProduct(rank);
  const rival=rankProduct(rank>1?rank-1:2);
  const hero=rank===1;
  return <div style={{position:"absolute",top:430,left:0,right:0,height:1010,zIndex:9}}>
    {hero?<Stars t={t}/>:null}
    <div style={{position:"absolute",top:4,left:120,right:120,textAlign:"center",
      fontWeight:950,fontSize:hero?57:39,color:hero?COLORS.plum:COLORS.deep}}>
      {hero?"🏆  TODAY'S #1 PICK":"FRIENDLY RANK REVEAL"}
    </div>
    <div style={{
      position:"absolute",top:75,left:hero?105:80,width:hero?870:680,
      height:hero?760:670,
      borderRadius:"50%",border:"4px solid rgba(255,255,255,.66)",
      background:"radial-gradient(circle,rgba(255,255,255,.8),rgba(144,224,255,.06) 70%)"
    }}/>
    <Buddy product={p} x={hero?264:94} y={hero?130:130} t={t}
      scale={hero?1.04:1.05} hero angle={hero?1:-2}/>
    {!hero?<Buddy product={rival} x={648} y={332} t={t}
       scale={.65} angle={9} delay={2} opacity={.94}/>:null}
    <div style={{position:"absolute",top:hero?893:899,left:85,right:85,
      background:"rgba(255,255,255,.89)",border:"2px solid rgba(107,91,196,.16)",
      borderRadius:30,padding:"15px 28px",boxShadow:shadow,
      textAlign:"center",fontWeight:850,fontSize:32,color:COLORS.deep}}>
      {p.name}
    </div>
  </div>;
};

const OutroScene=({t})=><div style={{
  position:"absolute",top:425,left:0,right:0,height:1010,zIndex:10
}}>
  <div style={{textAlign:"center",fontSize:57,color:COLORS.deep,fontWeight:950}}>
    पाँच दोस्त, आपकी पसंद!
  </div>
  <div style={{textAlign:"center",marginTop:16,fontSize:31,color:COLORS.purple,
    fontWeight:850}}>REAL TOP 5 • ORIGINAL TRUSTFOLIO RANKING</div>
  <div style={{position:"absolute",left:35,top:145,width:1010,height:660,
    borderRadius:50,background:"rgba(255,255,255,.55)",border:"3px solid #fff"}}/>
  {[1,2,3,4,5].map((n,i)=>{
    const p=rankProduct(n);
    return <Buddy key={p.id} product={p} x={-12+i*182} y={285+(i%2)*36}
      t={t} delay={i} angle={-6+i*3} scale={.48}/>;
  })}
  <div style={{position:"absolute",top:790,left:100,right:100,textAlign:"center",
    fontSize:37,fontWeight:950,color:COLORS.purple}}>
    अपनी ज़रूरत का मैच चुनो!
  </div>
</div>;

const Subtitle=({line,t})=>{
  const start=line.start,end=line.end;
  const reveal=lerp(t,start,start+.25,0,1)*lerp(t,end-.25,end,1,0);
  return <div style={{
    position:"absolute",top:1495,left:66,width:948,minHeight:140,zIndex:21,
    background:"rgba(25,24,74,.94)",border:"3px solid rgba(255,226,86,.85)",
    borderRadius:34,boxShadow:"0 18px 34px rgba(21,29,71,.20)",
    padding:"16px 30px",boxSizing:"border-box",
    display:"flex",alignItems:"center",justifyContent:"center",
    textAlign:"center",opacity:reveal,transform:"translateY("+((1-reveal)*12)+"px)"
  }}>
    <div style={{fontFamily:font,fontSize:36,fontWeight:800,lineHeight:1.65,
      color:"#FFF9EC",textShadow:"0 2px 0 rgba(0,0,0,.2)"}}>{line.text}</div>
  </div>;
};

const BottomCTA=({t,finalScene})=><div style={{
  position:"absolute",left:0,right:0,bottom:0,height:251,zIndex:25,
  background:"linear-gradient(105deg,#1A174D,#28205E 65%,#3C2182)",
  borderTop:"11px solid #FCD444",boxShadow:"0 -14px 30px rgba(19,31,100,.22)",
  padding:"27px 70px",boxSizing:"border-box"}}>
  <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
    <div style={{color:"white",fontSize:39,fontWeight:950}}>
      COMPARE <span style={{color:COLORS.gold}}>TOP 5</span> ON TRUSTFOLIO
    </div>
    <div style={{
      width:74,height:74,borderRadius:"50%",background:COLORS.gold,color:COLORS.deep,
      fontSize:47,display:"flex",alignItems:"center",justifyContent:"center",
      transform:"translateX("+Math.sin(t*2)*8+"px)"}}>➜</div>
  </div>
  <div style={{color:"#C8C4FA",fontSize:30,fontWeight:850}}>www.trustfolio.in</div>
  <div style={{
    position:"absolute",bottom:22,left:50,right:50,textAlign:"center",
    fontSize:21,letterSpacing:.7,color:"#F9E8A8",fontWeight:780}}>
    CONCEPT DEMO • HISTORICAL PRICES • NOT FOR PUBLICATION
  </div>
</div>;

export const BubbleKingdom=()=>{
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  const t=frame/fps;
  let index=story.lines.findIndex((line)=>t>=line.start&&t<line.end);
  if(index<0)index=t<story.lines[0].start?0:6;
  const line=story.lines[index];
  const enter=lerp(t,line.start,line.start+.3,0,1);
  return <AbsoluteFill style={{
    fontFamily:font,color:COLORS.deep,overflow:"hidden"}}>
    <LaundryWorld t={t}/>
    <BrandHeader/>
    <SectionTitle t={t} scene={index}/>
    <div style={{position:"absolute",inset:0,opacity:enter,transform:"scale("+(1+(1-enter)*.025)+")",zIndex:9}}>
      {index===0?<IntroScene t={t}/>:index<=5?<BattleScene t={t} rank={6-index}/>:<OutroScene t={t}/>}
    </div>
    <Subtitle line={line} t={t}/>
    <BottomCTA t={t} finalScene={index===6}/>
    {story.audioFile?<Audio src={staticFile(story.audioFile)} volume={1}/>:null}
  </AbsoluteFill>;
};
