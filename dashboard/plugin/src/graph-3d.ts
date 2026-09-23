export interface GraphItem {id:string;path:string;label:string;group:string;kind:'pdf'|'report'}
export interface GraphLink {from:string;to:string;kind:'source'|'related'}
const palette=['#4cc9e9','#f4bd64','#f27378','#68d9a1','#b998f1','#e6dd6b','#80aceb','#ef97be'];
interface Point {item:GraphItem;x:number;y:number;z:number;px:number;py:number;r:number}

/** Perspective projection, with redraw only after interaction or resize. */
export class PaperGraph3D {
  private canvas:HTMLCanvasElement;private tip:HTMLElement;private list:HTMLElement;private observer:ResizeObserver;
  private points:Point[]=[];private yaw=.37;private pitch=-.22;private zoom=1;private panX=0;private panY=0;
  private start:{x:number;y:number;panX:number;panY:number;yaw:number;pitch:number;rotate:boolean}|null=null;
  private lastX=0;private lastY=0;private scheduled=false;private disposed=false;
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
    this.observer=new ResizeObserver(()=>this.draw());this.observer.observe(host);this.draw();
  }
  destroy(){this.disposed=true;this.observer.disconnect();this.canvas.removeEventListener('wheel',this.wheel);this.canvas.removeEventListener('pointerdown',this.down);this.canvas.removeEventListener('pointermove',this.move);this.canvas.removeEventListener('pointerup',this.up);this.canvas.removeEventListener('pointercancel',this.cancel);this.canvas.removeEventListener('pointerleave',this.leave);this.canvas.removeEventListener('contextmenu',this.contextMenu);this.canvas.removeEventListener('keydown',this.key);this.host.empty();}
  private schedule(){if(this.scheduled||this.disposed)return;this.scheduled=true;requestAnimationFrame(()=>{this.scheduled=false;this.draw();});}
  private wheel=(e:WheelEvent)=>{e.preventDefault();this.zoom=Math.max(.45,Math.min(3.5,this.zoom*Math.exp(-e.deltaY*.0012)));this.schedule();};
  private down=(e:PointerEvent)=>{this.canvas.setPointerCapture(e.pointerId);this.start={x:e.clientX,y:e.clientY,panX:this.panX,panY:this.panY,yaw:this.yaw,pitch:this.pitch,rotate:e.shiftKey||e.button===2};this.tip.hidden=true;};
  private move=(e:PointerEvent)=>{this.lastX=e.clientX;this.lastY=e.clientY;if(this.start){const dx=e.clientX-this.start.x,dy=e.clientY-this.start.y;if(this.start.rotate){this.yaw=this.start.yaw+dx*.007;this.pitch=Math.max(-1.4,Math.min(1.4,this.start.pitch+dy*.007));}else{this.panX=this.start.panX+dx;this.panY=this.start.panY+dy;}this.schedule();return;}this.hover(e.clientX,e.clientY);};
  private up=(e:PointerEvent)=>{const s=this.start;this.start=null;if(this.canvas.hasPointerCapture(e.pointerId))this.canvas.releasePointerCapture(e.pointerId);if(s&&!s.rotate&&e.button===0&&Math.hypot(e.clientX-s.x,e.clientY-s.y)<6){const node=this.hit(e.clientX,e.clientY);if(node)this.open(node.item.path);}this.hover(e.clientX,e.clientY);};
  private cancel=()=>{this.start=null;this.tip.hidden=true;};
  private leave=()=>{if(!this.start)this.tip.hidden=true;};
  private contextMenu=(e:MouseEvent)=>e.preventDefault();
  private key=(e:KeyboardEvent)=>{if(e.key==='+'||e.key==='='){this.zoom=Math.min(3.5,this.zoom*1.15);}else if(e.key==='-'){this.zoom=Math.max(.45,this.zoom/1.15);}else if(e.key==='ArrowLeft'){this.panX+=24;}else if(e.key==='ArrowRight'){this.panX-=24;}else if(e.key==='ArrowUp'){this.panY+=24;}else if(e.key==='ArrowDown'){this.panY-=24;}else if(e.key==='Enter'&&this.items.length){this.open(this.items[0].path);}else return;e.preventDefault();this.schedule();};
  private hit(x:number,y:number){const rect=this.canvas.getBoundingClientRect(),px=x-rect.left,py=y-rect.top;return this.points.filter(p=>Math.hypot(p.px-px,p.py-py)<=Math.max(13,p.r+6)).sort((a,b)=>b.z-a.z)[0];}
  private hover(x:number,y:number){const p=this.hit(x,y);if(!p){this.tip.hidden=true;this.canvas.style.cursor='grab';return;}const rect=this.canvas.getBoundingClientRect();this.tip.textContent=`${p.item.kind==='pdf'?'PDF':'리포트'} · ${p.item.group} · ${p.item.label}`;this.tip.hidden=false;this.tip.style.left=Math.max(10,Math.min(rect.width-this.tip.offsetWidth-10,x-rect.left+12))+'px';this.tip.style.top=Math.max(10,Math.min(rect.height-this.tip.offsetHeight-8,y-rect.top-34))+'px';this.canvas.style.cursor='pointer';}
  private draw(){if(this.disposed)return;const rect=this.host.getBoundingClientRect(),w=Math.max(1,Math.floor(rect.width)),h=Math.max(1,Math.floor(rect.height)),dpr=Math.min(2,devicePixelRatio||1);this.canvas.width=Math.round(w*dpr);this.canvas.height=Math.round(h*dpr);const ctx=this.canvas.getContext('2d');if(!ctx)return;ctx.scale(dpr,dpr);ctx.clearRect(0,0,w,h);
    const gradient=ctx.createRadialGradient(w*.5,h*.48,5,w*.5,h*.5,Math.max(w,h)*.72);gradient.addColorStop(0,'#343c57');gradient.addColorStop(1,'#202534');ctx.fillStyle=gradient;ctx.fillRect(0,0,w,h);
    const groups=[...new Set(this.items.map(i=>i.group))].sort(),groupCounts=new Map<string,number>(),centers=new Map(groups.map((g,j)=>{const a=j*2.399963229728653;return [g,{x:Math.cos(a)*.58,y:Math.sin(a)*.42,z:Math.sin(a*1.3)*.35}] as const;}));
    const scale=Math.min(w,h)*.54*this.zoom,project=(item:GraphItem)=>{const ix=groupCounts.get(item.group)||0;groupCounts.set(item.group,ix+1);const center=centers.get(item.group)!,a=ix*2.399963229728653,r=.09*Math.sqrt(ix),x=center.x+Math.cos(a)*r,y=center.y+Math.sin(a)*r,z=center.z+Math.sin(a*1.7)*.16;
      const cx=Math.cos(this.yaw),sx=Math.sin(this.yaw),cy=Math.cos(this.pitch),sy=Math.sin(this.pitch),xx=x*cx-z*sx,zz=x*sx+z*cx,yy=y*cy-zz*sy,depth=y*sy+zz*cy,perspective=2.4/(2.7-depth);return {item,x,y,z:depth,px:w*.5+this.panX+xx*scale*perspective,py:h*.5+this.panY+yy*scale*perspective,r:(item.kind==='report'?6.5:4.3)*perspective};};
    this.points=this.items.map(project);const byId=new Map(this.points.map(p=>[p.item.id,p]));
    for(const edge of this.links){const a=byId.get(edge.from),b=byId.get(edge.to);if(!a||!b)continue;ctx.beginPath();ctx.moveTo(a.px,a.py);ctx.lineTo(b.px,b.py);ctx.strokeStyle=edge.kind==='source'?'rgba(241,190,107,.5)':'rgba(124,163,211,.23)';ctx.lineWidth=edge.kind==='source'?1.4:.8;ctx.stroke();}
    const ordered=[...this.points].sort((a,b)=>a.z-b.z);for(const p of ordered){const idx=groups.indexOf(p.item.group),color=palette[idx%palette.length];ctx.beginPath();ctx.arc(p.px,p.py,Math.max(2.5,p.r),0,Math.PI*2);ctx.fillStyle=color;ctx.globalAlpha=Math.max(.44,Math.min(1,.76+p.z*.16));ctx.shadowColor=color;ctx.shadowBlur=p.item.kind==='report'?14:7;ctx.fill();ctx.shadowBlur=0;ctx.globalAlpha=1;if(p.item.kind==='pdf'){ctx.strokeStyle='rgba(255,255,255,.78)';ctx.lineWidth=1;ctx.stroke();}}
  }
}
