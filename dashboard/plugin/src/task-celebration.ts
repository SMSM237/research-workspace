/** Short, non-blocking decoration. No data writes and no render-triggered replay. */
export class TaskCelebration {
  private dispose:(()=>void)|undefined;
  destroy(){this.dispose?.();this.dispose=undefined;}
  show(anchor:HTMLElement){
    this.destroy();
    const doc=anchor.ownerDocument,win=doc.defaultView;if(!win)return;
    const root=doc.createElement('div');root.className='rd-celebration';
    const message=doc.createElement('div');message.className='rd-celebration-message';
    message.setAttribute('role','status');message.setAttribute('aria-live','polite');root.append(message);doc.body.append(root);
    const animations:Animation[]=[];let timer:number|undefined;
    const cleanup=()=>{if(timer!==undefined)win.clearTimeout(timer);animations.forEach(a=>a.cancel());root.remove();};
    this.dispose=cleanup;
    message.textContent='오늘 할 일을 모두 마쳤어요!';
    const reduced=win.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if(!reduced){
      const box=anchor.getBoundingClientRect();
      const x=Math.max(50,Math.min(win.innerWidth-50,box.left+box.width/2));
      const y=Math.max(100,Math.min(win.innerHeight-100,box.top+box.height/2));
      const colors=['#2875bc','#268469','#dea63c','#8c74b5','#ed9e80'];
      for(let i=0;i<48;i++){
        const bit=doc.createElement('i');bit.className='rd-confetti';bit.setAttribute('aria-hidden','true');
        bit.style.left=x+'px';bit.style.top=y+'px';bit.style.backgroundColor=colors[i%colors.length];root.append(bit);
        const angle=Math.PI*(1.08+(i%16)/15*.84),speed=80+(i*37%140),dx=Math.cos(angle)*speed,dy=Math.sin(angle)*speed;
        animations.push(bit.animate([
          {transform:'translate(0,0) rotate(0deg)',opacity:0},
          {transform:`translate(${dx*.6}px,${dy}px) rotate(${i*29}deg)`,opacity:1,offset:.35},
          {transform:`translate(${dx}px,${100+i%5*12}px) rotate(${360+i*31}deg)`,opacity:0}
        ],{duration:1150+i%6*45,easing:'cubic-bezier(.2,.5,.5,1)',fill:'both'}));
      }
    }
    timer=win.setTimeout(()=>{cleanup();this.dispose=undefined;},2400);
  }
}
