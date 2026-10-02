import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),{PaperGraph3D}=require('./graph-3d.test-build.cjs');
test('rotation reuses geometry and canvas dimensions without per-frame layout reads',()=>{
 let reads=0,frame,draws=0,clock=10;
 globalThis.window={matchMedia:()=>({matches:false})};globalThis.document={hidden:false};globalThis.devicePixelRatio=1;
 globalThis.requestAnimationFrame=fn=>(frame=fn,1);globalThis.cancelAnimationFrame=()=>{};
 globalThis.ResizeObserver=class{observe(){}disconnect(){}};
 const ctx=new Proxy({clearRect(){draws++;}}, {get:(o,k)=>k in o?o[k]:()=>{}});
 const el=()=>({hidden:false,style:{},addEventListener(){},removeEventListener(){},createEl:()=>el(),createDiv:()=>el(),getContext:()=>ctx});
 const host={isConnected:true,addClass(){},createEl:()=>el(),createDiv:()=>el(),empty(){},getBoundingClientRect(){reads++;return {width:230,height:180};}};
 const items=[{id:'a',path:'Paper/a.pdf',label:'a',kind:'pdf',group:'A'},{id:'b',path:'Paper reports/b.md',label:'b',kind:'report',group:'A'}];
 const graph=new PaperGraph3D(host,items,[{from:'a',to:'b',kind:'source'}],()=>{}),initialReads=reads;
 for(let i=0;i<12;i++)frame(clock+=16.67);
 assert.ok(draws>=10);assert.equal(reads,initialReads,'rotation must not force a layout read each frame');
 graph.destroy();const prior=draws;frame(clock+16.67);assert.equal(draws,prior,'destroy stops rendering');
});
