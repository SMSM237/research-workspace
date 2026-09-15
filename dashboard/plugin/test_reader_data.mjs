import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {sourceMap,localPath}=require('./reader-data.test-build.cjs');
const packet=()=>({report_id:'P1',figures:[{image:{path:'Resources/P1/F1.png',source_ref:'s1'}}],sources:[{id:'s1',document_id:'D001',page:2}]});
test('local source mapping preserves physical PDF page',()=>assert.deepEqual(sourceMap(packet(),'P1'),[ {imagePath:'Resources/P1/F1.png',pdfPath:'Sources/P1/D001.pdf',page:2} ]));
test('unknown document remains image-only',()=>{const p=packet();p.sources=[];assert.equal(sourceMap(p,'P1')[0].pdfPath,null);});
test('do not misattribute another report',()=>assert.throws(()=>sourceMap(packet(),'P2')));
test('reject unsafe image paths and source IDs',()=>{for(const path of ['../outside.png','https://x/a.png','Resources/P1/../F1.png','Resources/P2/F1.png','Resources/P1/%2e%2e/F1.png']){const p=packet();p.figures[0].image.path=path;assert.throws(()=>sourceMap(p,'P1'));}const p=packet();p.sources[0].document_id='../private';assert.equal(sourceMap(p,'P1')[0].pdfPath,null);});
test('invalid pages cannot become PDF targets',()=>{for(const page of [0,-1,2.5,true,'2']){const p=packet();p.sources[0].page=page;assert.equal(sourceMap(p,'P1')[0].pdfPath,null);}});
test('duplicate sources and duplicate image paths fail closed',()=>{for(const key of ['figures','sources']){const p=packet();p[key].push(p[key][0]);assert.throws(()=>sourceMap(p,'P1'));}});
test('vault-bound local paths only',()=>{assert.equal(localPath('Sources/P1/D001.pdf'),true);for(const p of ['/tmp/a','C:\\a','../a','a//b','https://x','a/%23'])assert.equal(localPath(p),false);});

test('standalone table maps to its own physical page and table anchor',()=>{
 const p=packet();p.sources.push({id:'t1',kind:'table',document_id:'D001',page:7});
 p.standalone=[{id:'table-1',image:{path:'Resources/P1/T1.png',source_ref:'t1'}}];
 assert.deepEqual(sourceMap(p,'P1')[1],{imagePath:'Resources/P1/T1.png',pdfPath:'Sources/P1/D001.pdf',page:7,kind:'table',anchor:'table-1'});
 p.standalone[0].image.path='Resources/P1/F1.png';assert.throws(()=>sourceMap(p,'P1'));
 p.standalone[0].image.path='../outside.png';assert.throws(()=>sourceMap(p,'P1'));
});
