export interface StatusModel {connection:'disconnected'|'connecting'|'connected'|'snapshot';label:string;stage:string;detail:string;counts:string;running:boolean;}
const stages:Record<string,string>={queued:'분석 대기',parsing:'자료 추출 중',prepared:'자료 준비 완료',figure_analysis:'Figure 분석 중',critical_review:'핵심 쟁점 검토 중',integration:'결과 통합 중',qc:'리포트 검증 중',review:'분석 결과 검토 대기',complete:'분석 완료',failed:'분석 오류',waiting:'입력 대기'};
const labels={disconnected:'연결 해제',connecting:'연결 중',connected:'연결 완료'};
export function statusModel(value:unknown,now=Date.now()):StatusModel{
  const off:StatusModel={connection:'disconnected',label:labels.disconnected,stage:'',detail:'분석기가 연결되면 진행 단계가 표시됩니다.',counts:'',running:false};
  if(value===null)return off;
  try{
    const s=value as Record<string,unknown>;
    if(!s||s.version!==1||typeof s.stage!=='string'||!Object.prototype.hasOwnProperty.call(stages,s.stage)||typeof s.updated_at!=='string')throw Error();
    const age=now-Date.parse(s.updated_at);if(!Number.isFinite(age)||age < -60000)throw Error();
    if(s.connection!==undefined&&!['disconnected','connecting','connected'].includes(String(s.connection)))throw Error();
    const counts=[];
    for(const [prefix,label] of [['figures','Figure'],['supplements','서플']]){
      const done=s[prefix+'_done'],total=s[prefix+'_total'];
      if(done!==undefined||total!==undefined){if(typeof done!=='number'||typeof total!=='number'||!Number.isInteger(done)||!Number.isInteger(total)||done<0||total<done)throw Error();counts.push(`${label} ${done}/${total}`);}
    }
    if(age>120000)return {...off,detail:'최근 응답 없음 · 마지막 단계: '+stages[s.stage]};
    const connection=(s.connection||'connected') as 'disconnected'|'connecting'|'connected';
    if(connection==='disconnected')return {...off,detail:'마지막 단계: '+stages[s.stage]};
    if(connection==='connecting')return {...off,connection,label:labels.connecting,detail:'분석기 응답을 기다리고 있습니다.'};
    return {connection,label:labels[connection],stage:stages[s.stage],detail:typeof s.message==='string'?s.message.slice(0,300):'',counts:counts.join(' · '),running:['parsing','figure_analysis','critical_review','integration','qc'].includes(s.stage)};
  }catch{return {...off,detail:'상태 기록을 확인할 수 없습니다.'};}
}

export function sharedStatusModel(value:unknown,now=Date.now()):StatusModel{
  const empty:StatusModel={connection:'snapshot',label:'상태 동기화 대기',stage:'',counts:'',running:false,detail:'Windows에서 기록한 분석 상태가 Git 동기화 후 표시됩니다.'};
  if(value===null)return empty;
  try{
    const s=value as Record<string,unknown>;const stamp=Date.parse(String(s.updated_at));
    if(s.version!==1||s.transport!=='git_snapshot'||!Number.isFinite(stamp)||stamp>now+60000)throw Error();
    const checked=statusModel({...s,connection:'connected',updated_at:new Date(now).toISOString()},now);
    if(checked.connection!=='connected')throw Error();
    return {...checked,connection:'snapshot',label:'동기화된 분석 상태',running:false,
      detail:`마지막 기록 ${new Date(stamp).toLocaleString('ko-KR')} · 실시간 연결 상태가 아닙니다.`};
  }catch{return {...empty,detail:'동기화된 상태 파일을 읽지 못했습니다. GitSync에서 동기화를 확인해 주세요.'};}
}
