"""Produce synthetic UX fixtures only. No real paper or patient data."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
R = ROOT/'assets/Resources/DEMO'; R.mkdir(parents=True, exist_ok=True)

def chart(name, title, ylabel, names, values, extra):
    fig, ax = plt.subplots(figsize=(8.8, 4.2), dpi=150)
    bars = ax.bar(names, values, width=.55)
    ax.bar_label(bars, fmt='%g', padding=5)
    ax.set_title(title, loc='left', fontweight='bold', pad=17)
    ax.set_ylabel(ylabel); ax.set_ylim(0, max(values)*1.32)
    ax.spines[['top','right']].set_visible(False)
    ax.text(0, -.22, extra, transform=ax.transAxes, fontsize=9)
    fig.text(.5, .015, 'SYNTHETIC DEMO — NOT EXPERIMENTAL EVIDENCE', ha='center', fontsize=9)
    fig.subplots_adjust(bottom=.24, left=.12, right=.95, top=.83)
    fig.savefig(R/name); plt.close(fig)
chart('Fig01.png','Figure 1a | Intratumoral cell count','Cells',['Control','Condition A'],[20,30],'Total observed cells: Control = 100; Condition A = 200')
chart('Fig02.png','Figure 2a | Projected area at two time points','Relative projected area (%)',['Initial','Endpoint'],[100,80],'One simulated endpoint pair; no death marker or replicate-level data')
chart('FigS01.png','Figure S1a | Count normalized by segmented volume','Cells per volume unit',['Control','Condition A'],[1000,600],'Counts: 20 / 30; volumes: 0.02 / 0.05 arbitrary volume units')

def b(text, *refs): return {'text':text,'refs':list(refs)}

def source(id,locator,note): return {'id':id,'kind':'demo','locator':locator,'note':note}

def fig(id,label,kind,title,image,source_id,question,takeaway,observations,author,interpretation,limitation,method,concept_id,context,related=[]):
 return {'id':id,'label':label,'kind':kind,'title':title,'panels':['a'],
 'image':{'path':f'Resources/DEMO/{image}','alt':f'{label}: 가상 데이터로 제작한 읽기 형식 예시. 실제 연구 결과가 아닙니다.','origin':'synthetic_demo','source_ref':source_id},
 'question':b(question,source_id),'takeaway':b(takeaway,source_id),
 'observations':[b(observations,source_id)],'author_interpretation':[b(author,source_id)],
 'scientific_interpretation':[b(interpretation,source_id)],'limitations':[b(limitation,source_id)],
 'methods':[b(method,'demo-methods')],
 'panel_groups':[{'panels':['a'],'reading':observations,'refs':[source_id]}],
 'concept_links':[{'concept_id':concept_id,'context':context,'placement':'before_results','critical':True if concept_id=='denominator' else False}],
 'related_figures':related}

sources=[source('demo-setup','가상 자료 · 연구 설정','실제 논문·DOI·환자 자료가 아닌 인터페이스 검증용 설정입니다.'),
 source('demo-fig1','가상 Figure 1a · 세포 수 비교','그림 및 모든 숫자는 직접 구성한 예시입니다.'),
 source('demo-fig2','가상 Figure 2a · 투영 면적 비교','기능적 살상 결과를 측정한 자료가 아닙니다.'),
 source('demo-s1','가상 Figure S1a · 부피로 나눈 값','원본 해상도나 조직학적 증거를 포함하지 않는 예시입니다.'),
 source('demo-methods','가상 Methods · 정량 정의','실제 분석기에 전달될 근거 연결의 예시입니다.'),
 source('demo-limit','가상 자료 · 반복 측정 정보','반복 수와 분산을 제공하지 않았다는 조건을 기록합니다.')]
report={
 'schema_version':'0.1.0','report_id':'DEMO','kind':'demo',
 'paper':{'title':'TIL 분포를 읽는 세 가지 관점','subtitle':'Figure 중심 분석 · 문맥형 개념 설명 · 표준 리포트 예시','authors':['가상 예시 — 실제 논문 아님'],'year':2026,'venue':'UX / DATA CONTRACT DEMO','doi':None},
 'summary':{'takeaway':b('같은 결과도 무엇을 세고 무엇으로 나누었는지에 따라 의미가 달라집니다. 이 예시는 그림과 조건, 개념 설명, 해석의 범위를 한곳에서 읽는 형식을 보여줍니다.','demo-setup'),
 'question':b('Figure에서 관찰된 변화와 그 변화로 설명할 수 있는 생물학적 의미를 어떻게 구분할까요?','demo-setup'),
 'findings':[{'figure_id':'fig-1','text':'내부 세포 수와 내부 세포 비율은 서로 다른 값을 말합니다.'},{'figure_id':'fig-2','text':'투영 면적의 감소만으로 기능적 살상을 확정하지 않습니다.'},{'figure_id':'fig-s1','text':'동일한 세포 수도 부피를 고려하면 다른 분포로 해석됩니다.'}],
 'critical_limitations':[b('이 문서와 그림은 가상 데이터로 만든 UX 예시입니다. 실제 논문을 분석했거나 실제 실험 결과를 확인한 것이 아닙니다.','demo-setup')]},
 'design':{'blocks':[b('하나의 결과를 “질문 → 그림 → 관찰 → 과학적 해석 → 확인 범위”로 연결합니다. 메인 Figure에 연결된 서플도 별도 근거를 가진 분석 단위로 유지합니다.','demo-setup')],
 'flow':[{'figure_id':'fig-1','question':'얼마나 많은 세포가 내부에 있었는가?'},{'figure_id':'fig-2','question':'면적 변화로 어떤 결과를 말할 수 있는가?'},{'figure_id':'fig-s1','question':'구조의 크기를 고려해도 같은 결론인가?'}]},
 'figures':[
 fig('fig-1','Figure 1','main','내부 세포 수와 비율은 같은 방향으로 변하지 않을 수 있습니다.','Fig01.png','demo-fig1',
 '종양 내부로 분류된 세포 수가 증가하면 내부 세포 비율도 증가했다고 말할 수 있을까요?',
 '가상 예시에서 내부 세포 수는 20개에서 30개로 늘지만, 전체 관찰 세포를 분모로 한 비율은 20%에서 15%로 낮아집니다.',
 'Control의 내부 세포는 20개, Condition A는 30개입니다. 전체 관찰 세포는 각각 100개와 200개로 설정했습니다.',
 '실제 저자가 없는 가상 문서입니다. 저자 해석을 관찰 결과와 분리해 저장하는 위치를 보여줍니다.',
 '절대 세포 수를 비교하는 질문과 전체 관찰 세포 중 차지하는 비율을 비교하는 질문은 다릅니다. 두 수치를 동시에 제시하면 어떤 변화가 관찰됐는지 더 명확하게 설명할 수 있습니다.',
 '이 비교만으로 세포의 이동 속도나 살상 기능이 증가했다고 결론 내리지는 않습니다. 해당 기능을 직접 측정한 근거가 별도로 필요합니다.',
 '내부 세포 수는 정의된 내부 영역에서 센 값입니다. 비율은 내부 세포 수를 전체 관찰 세포 수로 나눕니다. 실제 분석에서는 원문에서 분모와 내부 영역 정의를 확인해야 합니다.',
 'denominator','이 Figure에서 30 > 20만 읽으면 비율도 증가했다고 오해할 수 있습니다. 어떤 분모를 사용했는지가 결론을 바꿉니다.',['fig-s1']),
 fig('fig-2','Figure 2','main','측정한 면적의 변화와 기능적 결과를 구분합니다.','Fig02.png','demo-fig2',
 '종양의 투영 면적이 줄었다는 결과는 무엇을 직접 보여줄까요?',
 '가상 예시의 투영 면적은 초기 대비 80%입니다. 이는 측정한 면적이 감소했다는 결과이며, 그 원인까지 지정하는 값은 아닙니다.',
 '초기 값을 100으로 두었을 때 endpoint의 투영 면적은 80입니다. 이 그림에는 세포 사멸 표지나 반복 실험의 분산이 포함되지 않았습니다.',
 '실제 저자 해석은 없습니다. 향후 실제 논문에서는 저자가 면적 변화를 어떤 의미로 기술했는지 원문과 연결합니다.',
 '분석자는 측정량과 기능적 해석 사이의 연결 근거를 확인해야 합니다. 다른 Figure에서 기능적 지표가 측정됐다면 함께 연결하고, 없다면 현재 근거 범위를 넘지 않습니다.',
 '면적만 제공된 상태에서 세포 사멸률을 수치로 환산하지 않습니다. 기능적 결론의 부재를 음성 결과로 해석하지도 않습니다.',
 '투영 면적은 같은 정의와 기준으로 비교한다는 가정의 예시입니다. 실제 논문에서는 이미지 취득 방식, 분할 기준, 정규화 시점과 대조군을 확인합니다.',
 'measurement','이 그림에서 직접 측정한 것은 면적입니다. “살상”이라는 해석을 붙이려면 무엇이 추가로 확인되어야 하는지 구분하게 합니다.'),
 fig('fig-s1','Figure S1','supplementary','세포 수를 부피로 나누면 다른 비교가 됩니다.','FigS01.png','demo-s1',
 '내부 세포 수를 구조의 부피로 나누면 두 조건의 비교는 어떻게 달라질까요?',
 '가상 부피를 0.02와 0.05로 두면 세포 수/부피 값은 1,000과 600입니다. 이것은 비율과도 다른 측정값입니다.',
 'Control은 20/0.02 = 1,000, Condition A는 30/0.05 = 600입니다. 부피 단위는 계산 설명을 위한 임의 단위입니다.',
 '실제 저자 해석은 없습니다. 메인 Figure를 보완하는 서플의 해석을 같은 체계로 기록하는 예시입니다.',
 'Figure 1의 절대 수, 전체 관찰 세포에 대한 비율, Figure S1의 부피당 수는 질문이 다릅니다. 어느 하나가 자동으로 더 올바른 지표는 아니며 연구 질문에 맞게 선택해야 합니다.',
 '부피 정의와 측정 방법이 없으면 이 값을 실제 세포 밀도로 재현할 수 없습니다. 가상 수치를 실제 실험의 정량 기준으로 사용하지 않습니다.',
 '세포 수와 부피가 같은 관찰 단위에서 얻어졌다고 가정합니다. 실제 적용에서는 동일 시료 대응과 부피 측정 기준을 확인해야 합니다.',
 'density','Figure 1에서 설명한 분모의 문제를 부피당 세포 수로 확장합니다. 비율과 밀도를 같은 이름으로 표기하지 않도록 돕습니다.',['fig-1'])],
 'concepts':[
 {'id':'denominator','term':'분모와 비율','english':'Denominator & proportion','category':'reading_guide','definition':'비율은 “무엇을 센 값인가”뿐 아니라 “어떤 전체로 나눈 값인가”로 정의됩니다.','details':['이 예시에서 20/100은 20%, 30/200은 15%입니다. 분자의 크기만 비교하면 비율의 변화 방향을 알 수 없습니다.','전체 투입 세포, 영상 안에서 관찰한 세포, 살아 있는 세포는 서로 다른 분모가 될 수 있습니다. 실제 보고서는 원문의 정의를 그대로 기록하고 임의로 바꾸지 않습니다.'],'caution':'분모가 다르면 같은 퍼센트 표기라도 직접 비교할 수 있는 값인지 다시 확인해야 합니다.','origin':'general_reasoning','refs':[]},
 {'id':'measurement','term':'측정량과 해석','english':'Measurement & interpretation','category':'interpretation','definition':'직접 측정한 값과 그 값으로 설명하려는 현상은 구분해서 기록합니다.','details':['현재 그림에서 직접 제공한 값은 투영 면적입니다. 특정 원인을 선택하려면 그 원인을 구분할 수 있는 추가 관찰이나 실험이 있어야 합니다.','방법을 모르거나 관련 Figure가 제공되지 않았다면, “확인되지 않음”으로 남깁니다. 자료가 없다는 사실은 현상이 없다는 결과와 다릅니다.'],'caution':'자료가 보여주는 변화는 분명히 설명하되, 측정하지 않은 기전이나 기능까지 관찰 사실로 확대하지 않습니다.','origin':'general_reasoning','refs':[]},
 {'id':'density','term':'비율과 밀도','english':'Proportion & density','category':'definition','definition':'비율은 전체 중의 몫이고, 여기서 밀도는 정해진 공간 크기당 세포 수입니다.','details':['세포 수/전체 세포 수와 세포 수/부피는 분모의 대상과 단위가 다릅니다. 따라서 수치가 비슷해 보여도 같은 정량값이 아닙니다.','부피를 사용하는 값은 부피가 어떻게 정의되고 측정되었는지에 영향을 받습니다. 실제 분석에서는 해당 Methods를 함께 연결해야 합니다.'],'caution':'수치만 옮기지 않고 분자, 분모, 단위와 관찰 범위를 함께 보존합니다.','origin':'general_reasoning','refs':[]}],
 'integration':[b('세 가지 그림은 동일한 현상을 서로 다른 측정값으로 설명할 때 생기는 해석 차이를 보여주는 예시입니다. 좋은 리포트는 어떤 값이 변화했는지와 그 변화로 무엇을 주장할 수 있는지를 함께 기록합니다.','demo-fig1','demo-fig2','demo-s1')],
 'applications':[b('사용자 연구에서 TIL의 이동·내부 분포·기능적 결과를 다룰 때, 각각 어떤 측정값과 근거에 연결되는지 분리해 정리하는 템플릿으로 활용할 수 있습니다. 이는 이 가상 예시가 입증한 연구 결론이 아니라 문서 설계 제안입니다.','demo-setup')],
 'standalone':[{'id':'unreported-replicates','title':'반복 수와 분산이 제공되지 않은 경우','blocks':[b('이 가상 데이터에는 독립 반복 수, 분산, 통계 검정 결과를 설정하지 않았습니다. 따라서 유의성이나 재현성을 주장하는 문장을 생성하지 않습니다. 실제 논문에서도 미제공 정보는 추정으로 채우지 않습니다.','demo-limit')]}],
 'sources':sources,
 'coverage':[{'source_id':s['id'],'status':'analyzed','linked_to': {'demo-setup':['summary','design','applications'],'demo-fig1':['fig-1'],'demo-fig2':['fig-2'],'demo-s1':['fig-s1'],'demo-methods':['fig-1','fig-2','fig-s1'],'demo-limit':['unreported-replicates']}[s['id']],'reason':''} for s in sources]
}
(ROOT/'examples/demo.analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Synthetic fixture and 3 local PNG figures created.')
