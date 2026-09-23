export interface GraphItem {id:string;path:string;label:string;group:string;kind:'pdf'|'report'}
export interface GraphLink {from:string;to:string;kind:'source'|'related'}
const palette=['#82c7bd','#e2bc7e','#d99b95','#a8bc8d','#aaa4cb','#b7c8db','#d4acbb','#aec6a3'];
interface Point {item:GraphItem;x:number;y:number;z:number;px:number;py:number;r:number}

/** Perspective projection, with redraw only after interaction or resize. */
export class PaperGraph3D {
  private canvas:HTMLCanvasElement;private tip:HTMLElement;private list:HTMLElement;private observer:ResizeObserver;
  private points:Point[]=[];private yaw=.37;private pitch=-.22;private zoom=1;private panX=0;private panY=0;
  private start:{x:number;y:number;panX:number;panY:number;yaw:number;pitch:number;rotate:boolean}|null=null;
  private lastX=0;private lastY=0;private scheduled=false;private disposed=false;
  private frame=0;private lastFrame=0;private resumeAt=0;private nextTurn=0;
  private velocityYaw=0;private velocityPitch=0;private targetYaw=0;private targetPitch=0;private direction=0;
  private reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)');
  constructor(private host:HTMLElement,private items:GraphItem[],private links:GraphLink[],private open:(path:string)=>void){
    host.addClass('rd-graph3d');
    this.canvas=host.createEl('canvas',{cls:'rd-graph3d-canvas',attr:{tabindex:'0',role:'img','aria-label':`3D 논문 그래프. PDF ${items.filter(n=>n.kind==='pdf').length}개와 리포트 ${items.filter(n=>n.kind==='report').length}개. 휠로 확대, 드래그로 이동, Shift+드래그로 회전합니다.`}});
    this.tip=host.createDiv({cls:'rd-graph3d-tip'});this.tip.hidden=true;
    this.list=host.createDiv({cls:'rd-graph3d-accessible'});
    for(const item of items){const b=this.list.createEl('button',{text:`${item.kind==='pdf'?'원본 PDF':'분석 리포트'} · ${item.group} · ${item.label}`,attr:{type:'button'}});b.onclick=()=>open(item.path);}
    this.canvas.addEventListener('wheel',this.wheel,{passive:false});
    this.canvas.addEventListener('pointerdown',this.down);
    this.canvas.addEventListener('pointermove',this.move);
    this.canvas.addEventListener('pointerup',this.up);
    this.canvas.addEventListener('pointercancel',this.cancel);
    this.canvas.addEventListener('pointerleave',this.leave);
    this.canvas.addEventListener('contextmenu',this.contextMenu);
    this.canvas.addEventListener('keydown',this.key);
    this.direction=Math.random()*Math.PI*2;this.velocityYaw=this.targetYaw=Math.cos(this.direction)*.0015;this.velocityPitch=this.targetPitch=Math.sin(this.direction)*.0015;this.nextTurn=performance.now()+7500;
    this.observer=new ResizeObserver(()=>this.draw());this.observer.observe(host);this.draw();this.frame=requestAnimationFrame(this.animate);
  }
  destroy(){this.disposed=true;cancelAnimationFrame(this.frame);this.observer.disconnect();this.canvas.removeEventListener('wheel',this.wheel);this.canvas.removeEventListener('pointerdown',this.down);this.canvas.removeEventListener('pointermove',this.move);this.canvas.removeEventListener('pointerup',this.up);this.canvas.removeEventListener('pointercancel',this.cancel);this.canvas.removeEventListener('pointerleave',this.leave);this.canvas.removeEventListener('contextmenu',this.contextMenu);this.canvas.removeEventListener('keydown',this.key);this.host.empty();}
  private schedule(){if(this.scheduled||this.disposed)return;this.scheduled=true;requestAnimationFrame(()=>{this.scheduled=false;this.draw();});}
  private animate=(now:number)=>{if(this.disposed)return;const elapsed=this.lastFrame?Math.min(40,now-this.lastFrame):0;this.lastFrame=now;
    if(!document.hidden&&this.host.isConnected&&!this.start&&now>=this.resumeAt){
      const needsReset=Math.abs(this.zoom-1)>.001||Math.abs(this.panX)>.25||Math.abs(this.panY)>.25;
      if(needsReset){const blend=this.reducedMotion.matches?1:1-Math.exp(-elapsed/1500);this.zoom+=(1-this.zoom)*blend;this.panX-=this.panX*blend;this.panY-=this.panY*blend;if(Math.abs(this.zoom-1)<.001)this.zoom=1;if(Math.abs(this.panX)<.25)this.panX=0;if(Math.abs(this.panY)<.25)this.panY=0;}
      if(!this.reducedMotion.matches){
        if(now>=this.nextTurn){this.direction+=(Math.random()<.5?-1:1)*(1.1+Math.random()*(Math.PI*2-2.2));const speed=.0012+Math.random()*.0006;this.targetYaw=Math.cos(this.direction)*speed;this.targetPitch=Math.sin(this.direction)*speed;this.nextTurn=now+7000+Math.random()*5000;}
        const blend=1-Math.exp(-elapsed/850);this.velocityYaw+=(this.targetYaw-this.velocityYaw)*blend;this.velocityPitch+=(this.targetPitch-this.velocityPitch)*blend;this.yaw+=this.velocityYaw*elapsed;this.pitch+=this.velocityPitch*elapsed;
      }
      if(needsReset||!this.reducedMotion.matches)this.draw();
    }
    this.frame=requestAnimationFrame(this.animate);
  };
  private pause(){this.resumeAt=performance.now()+4500;}
  private wheel=(e:WheelEvent)=>{e.preventDefault();this.pause();this.zoom=Math.max(.45,Math.min(3.5,this.zoom*Math.exp(-e.deltaY*.0012)));this.schedule();};
  private down=(e:PointerEvent)=>{this.pause();this.canvas.setPointerCapture(e.pointerId);this.start={x:e.clientX,y:e.clientY,panX:this.panX,panY:this.panY,yaw:this.yaw,pitch:this.pitch,rotate:e.shiftKey||e.button===2};this.tip.hidden=true;};
  private move=(e:PointerEvent)=>{this.lastX=e.clientX;this.lastY=e.clientY;if(this.start){const dx=e.clientX-this.start.x,dy=e.clientY-this.start.y;if(this.start.rotate){this.yaw=this.start.yaw+dx*.007;this.pitch=this.start.pitch+dy*.007;}else{this.panX=this.start.panX+dx;this.panY=this.start.panY+dy;}this.schedule();return;}this.hover(e.clientX,e.clientY);};
  private up=(e:PointerEvent)=>{const s=this.start;this.start=null;this.pause();if(this.canvas.hasPointerCapture(e.pointerId))this.canvas.releasePointerCapture(e.pointerId);if(s&&!s.rotate&&e.button===0&&Math.hypot(e.clientX-s.x,e.clientY-s.y)<6){const node=this.hit(e.clientX,e.clientY);if(node)this.open(node.item.path);}this.hover(e.clientX,e.clientY);};
  private cancel=()=>{this.start=null;this.pause();this.tip.hidden=true;};
  private leave=()=>{if(!this.start)this.tip.hidden=true;};
  private contextMenu=(e:MouseEvent)=>e.preventDefault();
  private key=(e:KeyboardEvent)=>{if(e.key==='+'||e.key==='='){this.zoom=Math.min(3.5,this.zoom*1.15);}else if(e.key==='-'){this.zoom=Math.max(.45,this.zoom/1.15);}else if(e.key==='ArrowLeft'){this.panX+=24;}else if(e.key==='ArrowRight'){this.panX-=24;}else if(e.key==='ArrowUp'){this.panY+=24;}else if(e.key==='ArrowDown'){this.panY-=24;}else if(e.key==='Enter'&&this.items.length){this.open(this.items[0].path);}else return;e.preventDefault();this.pause();this.schedule();};
  private hit(x:number,y:number){const rect=this.canvas.getBoundingClientRect(),px=x-rect.left,py=y-rect.top;return this.points.filter(p=>Math.hypot(p.px-px,p.py-py)<=Math.max(13,p.r+6)).sort((a,b)=>b.z-a.z)[0];}
  private hover(x:number,y:number){const p=this.hit(x,y);if(!p){this.tip.hidden=true;this.canvas.style.cursor='grab';return;}const rect=this.canvas.getBoundingClientRect();this.tip.textContent=`${p.item.kind==='pdf'?'PDF':'리포트'} · ${p.item.group} · ${p.item.label}`;this.tip.hidden=false;this.tip.style.left=Math.max(10,Math.min(rect.width-this.tip.offsetWidth-10,x-rect.left+12))+'px';this.tip.style.top=Math.max(10,Math.min(rect.height-this.tip.offsetHeight-8,y-rect.top-34))+'px';this.canvas.style.cursor='pointer';}
  private draw(){if(this.disposed)return;const rect=this.host.getBoundingClientRect(),w=Math.max(1,Math.floor(rect.width)),h=Math.max(1,Math.floor(rect.height)),dpr=Math.min(2,devicePixelRatio||1);const pixelWidth=Math.round(w*dpr),pixelHeight=Math.round(h*dpr);if(this.canvas.width!==pixelWidth||this.canvas.height!==pixelHeight){this.canvas.width=pixelWidth;this.canvas.height=pixelHeight;}const ctx=this.canvas.getContext('2d');if(!ctx)return;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
    ctx.fillStyle='#23332f';ctx.fillRect(0,0,w,h);
    const groups=[...new Set(this.items.map(i=>i.group))].sort(),groupCounts=new Map<string,number>();
    const counts=new Map(groups.map(g=>[g,this.items.filter(i=>i.group===g).length]));
    const centers=new Map(groups.map((g,j)=>{const y=1-2*(j+.5)/groups.length,a=j*2.399963229728653,r=Math.sqrt(1-y*y);return [g,{x:Math.cos(a)*r,y,z:Math.sin(a)*r}] as const;}));
    const scale=Math.min(w,h)*.46*this.zoom;
    const project=(item:GraphItem)=>{const ix=groupCounts.get(item.group)||0;groupCounts.set(item.group,ix+1);const center=centers.get(item.group)!,a=ix*2.399963229728653,cap=Math.min(.7,.19+Math.sqrt((counts.get(item.group)||1)/this.items.length)*.55),r=cap*Math.sqrt((ix+.5)/(counts.get(item.group)||1));
      const ref=Math.abs(center.y)>.9?{x:1,y:0,z:0}:{x:0,y:1,z:0};const ux=ref.y*center.z-ref.z*center.y,uy=ref.z*center.x-ref.x*center.z,uz=ref.x*center.y-ref.y*center.x,ul=Math.hypot(ux,uy,uz),vx=center.y*uz-center.z*uy,vy=center.z*ux-center.x*uz,vz=center.x*uy-center.y*ux;
      const tx=ux/ul*Math.cos(a)+vx/ul*Math.sin(a),ty=uy/ul*Math.cos(a)+vy/ul*Math.sin(a),tz=uz/ul*Math.cos(a)+vz/ul*Math.sin(a),normal=Math.hypot(center.x+r*tx,center.y+r*ty,center.z+r*tz),x=(center.x+r*tx)/normal,y=(center.y+r*ty)/normal,z=(center.z+r*tz)/normal;
      const cx=Math.cos(this.yaw),sx=Math.sin(this.yaw),cy=Math.cos(this.pitch),sy=Math.sin(this.pitch),xx=x*cx-z*sx,zz=x*sx+z*cx,yy=y*cy-zz*sy,depth=y*sy+zz*cy,perspective=2.5/(2.9-depth);return {item,x,y,z:depth,px:w*.5+this.panX+xx*scale*perspective,py:h*.5+this.panY+yy*scale*perspective,r:(item.kind==='report'?5.5:3.6)*perspective};};
    this.points=this.items.map(project);const byId=new Map(this.points.map(p=>[p.item.id,p]));
    for(const edge of this.links){const a=byId.get(edge.from),b=byId.get(edge.to);if(!a||!b)continue;ctx.beginPath();ctx.moveTo(a.px,a.py);ctx.lineTo(b.px,b.py);ctx.strokeStyle=edge.kind==='source'?'rgba(226,188,126,.38)':'rgba(178,202,190,.2)';ctx.lineWidth=edge.kind==='source'?1.2:.8;ctx.stroke();}
    const ordered=[...this.points].sort((a,b)=>a.z-b.z);for(const p of ordered){const idx=groups.indexOf(p.item.group),color=palette[idx%palette.length];ctx.beginPath();ctx.arc(p.px,p.py,Math.max(2.2,p.r),0,Math.PI*2);ctx.fillStyle=color;ctx.globalAlpha=Math.max(.48,Math.min(1,.7+p.z*.2));ctx.fill();ctx.globalAlpha=1;if(p.item.kind==='pdf'){ctx.strokeStyle='rgba(255,255,255,.48)';ctx.lineWidth=.8;ctx.stroke();}}
  }
}
