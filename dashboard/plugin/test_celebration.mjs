import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import vm from 'node:vm';import ts from 'typescript';import data from './dashboard-data.test-build.cjs';
const code=ts.transpileModule(fs.readFileSync('src/dashboard.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
class TFile {path='Tasks/QA.md';}
const module={exports:{}};
vm.runInNewContext(code,{exports:module.exports,require:id=>id==='obsidian'?{TFile,ItemView:class{},MarkdownRenderChild:class{}}:id==='./dashboard-data'?data:{},console});
function fixture(){
 const day=data.localDay(),file=new TFile(),storage=new Map();let text='- [ ] final ⏳ '+day,shows=0,fail=false;
 const d=Object.create(module.exports.ResearchDashboard.prototype);
 d.plugin={app:{vault:{getAbstractFileByPath:()=>file,process:async(f,fn)=>{if(fail)throw Error('disk failure');text=fn(text);},read:async()=>text},loadLocalStorage:k=>storage.get(k),saveLocalStorage:(k,v)=>storage.set(k,v)}};
 d.snapshot=async()=>({tasks:data.parseTasks(file.path,text)});d.celebration={show:()=>shows++};d.selectedDay='';
 return {d,day,storage,get text(){return text},get shows(){return shows},task:()=>data.parseTasks(file.path,text)[0],fail:()=>fail=true};
}
test('successful save celebrates once per day; reopening and undo/recheck do not replay',async()=>{const f=fixture();await f.d.toggle(f.task(),{});assert.equal(f.shows,1);assert.match(f.text,/\[x\]/);await f.d.snapshot();assert.equal(f.shows,1);await f.d.toggle(f.task(),{});await f.d.toggle(f.task(),{});assert.equal(f.shows,1);assert.equal(f.storage.get('research-task-celebration-day'),f.day);});
test('failed save and future-date action never celebrate or mark the day celebrated',async()=>{const f=fixture();f.fail();await assert.rejects(f.d.toggle(f.task(),{}),/disk failure/);assert.equal(f.shows,0);assert.equal(f.storage.size,0);const g=fixture();g.d.selectedDay='2099-01-01';await g.d.toggle(g.task(),{});assert.equal(g.shows,0);assert.equal(g.storage.size,0);});
test('simultaneous final saves across views celebrate once',async()=>{const f=fixture();await Promise.all([f.d.toggle(f.task(),{}),f.d.toggle(f.task(),{}).catch(()=>{})]);assert.equal(f.shows,1);});
