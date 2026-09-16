import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';
const {paperRelations,relationPositions}=createRequire(import.meta.url)('./paper-relations.test-build.cjs');
const paper=(path,title,concepts=[],tags=[])=>({path,title,concepts,tags});
test('bilingual related papers connect with explanations; index hubs and generic words do not',()=>{
 const p=[paper('a','Organoid lumen morphogenesis'),paper('b','오가노이드 내강 형태'),paper('c','Drug response IC50'),paper('d','Generic analysis model cells')];
 const g=paperRelations(p,{'index':{a:1,b:1,c:1}});assert.equal(g.nodes.length,4);assert.deepEqual(g.edges.map(e=>[e.from,e.to]),[['a','b']]);assert.ok(g.edges[0].reasons.includes('오가노이드·형태 형성'));assert.equal(g.edges[0].explicit,false);
});
test('explicit note links survive different topics, no self or duplicate edge',()=>{const g=paperRelations([paper('a','A'),paper('b','B'),paper('a','A')],{a:{a:1,b:1},b:{a:2}});assert.equal(g.edges.length,1);assert.equal(g.edges[0].explicit,true);});
test('specific cross-topic concept joins papers without forcing isolated nodes',()=>{const g=paperRelations([paper('a','A',['autophagy flux']),paper('b','B',['Autophagy flux']),paper('c','C')]);assert.equal(g.edges.length,1);assert.equal(g.nodes.length,3);assert.ok(g.edges[0].reasons.includes('autophagy flux'));});
test('group layout preserves all nodes and 44px hit spacing at mobile widths',()=>{for(const width of [230,300,650]){const p=Array.from({length:100},(_,i)=>paper(String(i),'Organoid lumen'));const g=paperRelations(p),l=relationPositions(g.nodes,g.groups,width);assert.equal(l.points.size,100);const xy=[...l.points.values()];for(let i=0;i<xy.length;i++){assert.ok(xy[i].x>=22&&xy[i].x<=width-22);assert.ok(xy[i].y+22<=l.height);for(let j=i+1;j<xy.length;j++)assert.ok(Math.abs(xy[i].x-xy[j].x)>=44||Math.abs(xy[i].y-xy[j].y)>=44);}assert.deepEqual(l,relationPositions(g.nodes,g.groups,width));}});
test('empty library has no invented groups or relations',()=>{const g=paperRelations([]);assert.equal(g.edges.length,0);assert.equal(relationPositions(g.nodes,g.groups,300).points.size,0);});
