/** Local, explainable discovery hints, never citation or causal claims. */
export interface PaperProfile {path:string;title:string;concepts:string[];tags:string[];unavailable?:boolean}
export interface Relation {from:string;to:string;reasons:string[];explicit:boolean}
const topics:[string,RegExp[]][]=[
 ['오가노이드·형태 형성',[/organoid|오가노이드/i,/morphogen|morpholog|형태|topolog|위상/i,/lumen|내강/i,/phase.field|bending|elastic|장력/i]],
 ['종양·면역 반응',[/immunotherap|면역.?치료|checkpoint|면역.?관문/i,/t.cell|t 세포|t세포|car.t/i,/immune.evasion|면역.?회피|tnf/i,/antigen|항원|interferon|ifn[γg]|면역.?배제/i]],
 ['약물 반응·정밀 치료',[/pharmacogen|약물.?유전체|drug.response|dose.response|약물.?반응|drug.resistan|chemoresistan/i,/personalized|precision.oncology|정밀.?치료|functional.diagnostic|기능.?진단/i,/ic50|dss|fgfr|sorafenib/i]],
 ['섬유아세포·미세환경',[/fibroblast|섬유아세포|\bcaf\b/i,/microenvironment|미세환경|stromal|기질.?세포/i,/cd90|cd10|gpr77|thy.1/i]],
 ['혈관·장벽',[/endothelial|내피|vascular|혈관/i,/permeability|투과|barrier|장벽|teer/i]],
 ['환자 유래 모델',[/patient.derived|환자.?유래/i,/model.fidelity|celligner|model.repository|모델.?저장/i]],
 ['유전체·발현 분석',[/crispr|유전자.?편집/i,/rna.seq|transcriptom|전사체|atac.seq|chromatin|크로마틴/i,/genomic|유전체|mutational|돌연변이/i]]
];
const norm=(s:string)=>s.normalize('NFKC').toLowerCase().replace(/[–—−]/g,'-').replace(/[^a-z0-9가-힣α-ω]+/g,' ').trim().replace(/\s+/g,' ');
const generic=new Set(['analysis','model','control','method','result','cell','cells','cancer','tumor','분석','모델','세포','연구','reading guide','figure']);
export function features(p:PaperProfile){
 const title=p.title,terms=p.concepts.join(' · '),all=title+' · '+terms+' · '+p.tags.join(' · ');
 const scores=topics.map(([name,patterns])=>({name,score:patterns.reduce((s,re)=>s+(re.test(title)?3:re.test(all)?1:0),0)}));
 const primary=scores.filter(x=>x.score>=2).sort((a,b)=>b.score-a.score)[0]?.name||'연관 주제 미분류';
 const keys=new Set(p.tags.map(norm).filter(s=>s.length>2&&!generic.has(s)));
 for(const term of p.concepts){const s=norm(term);if(s.length>=4&&s.length<=70&&!generic.has(s))keys.add(s);}
 // Specific technical abbreviations remain useful across bilingual concept names.
 for(const m of all.matchAll(/\b(?:CRISPR|PTEN|TNF|NF-κB|ATAC-seq|RNA-seq|FGFR4|CD90|GPR77|autophagy|organoid|lumen|fibroblast)\b/gi))keys.add(norm(m[0]));
 return {primary,keys,scores};
}
export function paperRelations(papers:PaperProfile[],links:Record<string,Record<string,number>>={}){
 const nodes=[...new Map(papers.map(p=>[p.path,p])).values()].sort((a,b)=>a.path.localeCompare(b.path));
 const facts=new Map(nodes.map(p=>[p.path,features(p)]));const edges:Relation[]=[];
 for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){
  const a=nodes[i],b=nodes[j],af=facts.get(a.path)!,bf=facts.get(b.path)!;
  const explicit=!!(links[a.path]?.[b.path]||links[b.path]?.[a.path]);
  const shared=[...af.keys].filter(k=>bf.keys.has(k));
  const sharedTopic=af.primary===bf.primary&&af.primary!=='연관 주제 미분류';
  const reasons=[...(explicit?['직접 노트 링크']:[]),...(sharedTopic?[af.primary]:[]),...shared.slice(0,3)];
  // A specific shared term or a multi-cue topic match; generic words never connect nodes.
  if(explicit||shared.length||sharedTopic)edges.push({from:a.path,to:b.path,reasons,explicit});
 }
 return {nodes,edges,groups:new Map(nodes.map(p=>[p.path,facts.get(p.path)!.primary]))};
}
/** Stable grouped grid; preserves all nodes, with nonoverlapping 44px targets. */
export function relationPositions(nodes:PaperProfile[],groups:Map<string,string>,width:number){
 const cols=Math.max(2,Math.floor((width-24)/54)),points=new Map<string,{x:number;y:number}>(),bands:{name:string;y:number;height:number}[]=[];let y=8;
 const names=[...new Set(nodes.map(p=>groups.get(p.path)!))].sort((a,b)=>a==='연관 주제 미분류'?1:b==='연관 주제 미분류'?-1:a.localeCompare(b,'ko'));
 for(const name of names){const group=nodes.filter(p=>groups.get(p.path)===name),height=30+Math.ceil(group.length/cols)*50;bands.push({name,y,height});group.forEach((p,i)=>points.set(p.path,{x:26+(i%cols)*(width-52)/Math.max(1,cols-1),y:y+52+Math.floor(i/cols)*50}));y+=height+10;}
 return {points,bands,height:y};
}
