"""Author the reusable JSON Schema. No data is inferred by this generator."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def string(**kw): return {'type':'string', 'minLength':1, **kw}
def arr(item, minimum=0): return {'type':'array','items':item,'minItems':minimum}
def obj(props, required=None): return {'type':'object','additionalProperties':False,'properties':props,'required':list(props) if required is None else required}
def ref(name): return {'$ref':f'#/$defs/{name}'}
id=string(pattern='^[A-Za-z0-9][A-Za-z0-9_-]*$')
block=obj({'text':string(),'refs':arr(id)})
concept_link=obj({'concept_id':id,'context':string(),'placement':{'enum':['before_results','before_interpretation']},'critical':{'type':'boolean'}})
figure=obj({'id':id,'label':string(),'kind':{'enum':['main','supplementary']},'title':string(),'panels':arr(string(),1),
'image':obj({'path':string(),'alt':string(),'origin':{'enum':['source_render','synthetic_demo']},'source_ref':id}),
'question':ref('block'),'takeaway':ref('block'),'observations':arr(ref('block'),1),'author_interpretation':arr(ref('block'),1),'scientific_interpretation':arr(ref('block'),1),'limitations':arr(ref('block'),1),'methods':arr(ref('block'),1),
'panel_groups':arr(obj({'panels':arr(string(),1),'reading':string(),'refs':arr(id,1)}),1),
'concept_links':arr(concept_link),'related_figures':arr(id)})
concept=obj({'id':id,'term':string(),'english':string(),'category':{'enum':['definition','reading_guide','interpretation']},'definition':string(),'details':arr(string(),1),'caution':string(),'origin':{'enum':['paper','external','general_reasoning','demo']},'refs':arr(id)})
source=obj({'id':id,'kind':{'enum':['main_text','methods','figure','supplementary_text','supplementary_figure','table','background','demo']},'locator':string(),'note':{'type':'string'},'document_id':string(),'page':{'type':'integer','minimum':1},'page_label':string(),'section':string(),'url':string()},['id','kind','locator','note'])
schema=obj({'schema_version':{'const':'0.1.0'},'report_id':id,'kind':{'enum':['paper','demo']},
'paper':obj({'title':string(),'subtitle':string(),'authors':arr(string(),1),'year':{'type':'integer','minimum':1500,'maximum':2200},'venue':string(),'doi':{'type':['string','null']}}),
'summary':obj({'takeaway':ref('block'),'question':ref('block'),'findings':arr(obj({'figure_id':id,'text':string()}),1),'critical_limitations':arr(ref('block'),1)}),
'design':obj({'blocks':arr(ref('block'),1),'flow':arr(obj({'figure_id':id,'question':string()}),1)}),
'figures':arr(ref('figure'),1),'concepts':arr(ref('concept')),'integration':arr(ref('block'),1),'applications':arr(ref('block')),
'standalone':arr(obj({'id':id,'title':string(),'blocks':arr(ref('block'),1)})),
'sources':arr(ref('source'),1),
'coverage':arr(obj({'source_id':id,'status':{'enum':['analyzed','context_only','not_provided','unreadable','not_analyzed']},'linked_to':arr(id),'reason':{'type':'string'}}),1)})
schema={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:figure-first:report:0.1.0',**schema,'$defs':{'block':block,'figure':figure,'concept':concept,'source':source}}
p=ROOT/'schemas/report.schema.json'; p.write_text(json.dumps(schema,ensure_ascii=False,indent=2),encoding='utf-8')
resources=ROOT/'src/figure_reports/resources'; resources.mkdir(exist_ok=True)
(resources/'report.schema.json').write_bytes(p.read_bytes())
