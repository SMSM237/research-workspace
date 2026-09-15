export const MEETING_SECTIONS=[
 {key:'attendees',title:'참석자',hint:'참석자 이름과 소속을 적어 주세요.',icon:'users',tone:'blue'},
 {key:'agenda',title:'안건',hint:'이번 회의에서 다룰 주제와 질문을 적어 주세요.',icon:'list',tone:'violet'},
 {key:'discussion',title:'논의 내용',hint:'의견, 검토한 자료, 중요한 내용을 자유롭게 적어 주세요.',icon:'messages-square',tone:'neutral'},
 {key:'decisions',title:'결정 사항',hint:'합의한 내용과 다음 진행 방향을 적어 주세요.',icon:'check-circle',tone:'green'},
 {key:'actions',title:'후속 할 일',hint:'해야 할 일과 담당자를 적어 주세요.\n체크박스는 아래 ‘할 일 추가’를 눌러 넣을 수 있습니다.',icon:'check-square',tone:'amber'}
] as const;
export interface MeetingSlot {key:string;start:number;end:number;value:string;}
export function meetingSlots(raw:string):MeetingSlot[]{
 const lines=raw.split(/\r?\n/),heads:Array<{line:number;key?:string}>=[];let fence='',front=lines[0]==='---';
 for(let n=front?1:0;n<lines.length;n++){const line=lines[n];if(front){if(line==='---')front=false;continue;}
  const mark=line.match(/^\s*(`{3,}|~{3,})/);if(mark){if(!fence)fence=mark[1][0];else if(mark[1][0]===fence)fence='';continue;}if(fence)continue;
  const m=line.match(/^#{1,2}\s+(.+?)\s*$/);if(!m)continue;const section=line.startsWith('## ')?MEETING_SECTIONS.find(s=>s.title===m[1]||(s.key==='actions'&&m[1]==='후속 업무')):undefined;heads.push({line:n,key:section?.key});
 }
 const slots:MeetingSlot[]=[];
 heads.forEach((h,i)=>{if(!h.key)return;if(slots.some(s=>s.key===h.key))throw Error('같은 회의록 항목이 중복되어 있습니다. 원문에서 제목을 확인해 주세요.');const start=h.line+1,end=heads[i+1]?.line??lines.length;let value=lines.slice(start,end).join('\n').trim();if(value==='<!-- - [ ] 할 일 내용 -->')value='';slots.push({key:h.key,start,end,value});});return slots;
}
export function writeMeeting(raw:string,values:Record<string,string>):string{
 const slots=meetingSlots(raw),lines=raw.split(/\r?\n/),sep=raw.includes('\r\n')?'\r\n':'\n';
 for(const slot of [...slots].reverse()){const value=values[slot.key];if(value===undefined||value===slot.value)continue;lines.splice(slot.start,slot.end-slot.start,'',...value.trim().split(/\r?\n/),'');}
 let result=lines.join(sep);for(const section of MEETING_SECTIONS)if(!slots.some(s=>s.key===section.key)&&values[section.key]?.trim())result=result.replace(/\s*$/,'')+sep+sep+'## '+section.title+sep+sep+values[section.key].trim().replace(/\r?\n/g,sep)+sep;
 meetingSlots(result);return result;
}
