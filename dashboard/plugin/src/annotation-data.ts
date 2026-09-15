export interface Annotation {id:string;anchor:string;quote:string;text:string;created:string;updated:string;resolved:boolean;}
export interface NotesData {version:1;report_id:string;comments:Annotation[];}
export function validNotes(value:unknown,rid?:string):NotesData {
  const d=value as NotesData;
  if(!d||d.version!==1||typeof d.report_id!=='string'||!/^[-A-Za-z0-9_]+$/.test(d.report_id)||rid&&d.report_id!==rid||!Array.isArray(d.comments)||d.comments.length>200)throw Error('메모 파일의 형식 또는 논문 ID가 맞지 않습니다.');
  const ids=new Set<string>();
  for(const c of d.comments){
    if(!c||typeof c.id!=='string'||!/^[-A-Za-z0-9_]+$/.test(c.id)||ids.has(c.id)||typeof c.text!=='string'||!c.text.trim()||c.text.length>20000||typeof c.quote!=='string'||c.quote.length>5000||typeof c.anchor!=='string'||!/^[\w-]*$/.test(c.anchor)||typeof c.resolved!=='boolean'||!Number.isFinite(Date.parse(c.created))||!Number.isFinite(Date.parse(c.updated)))throw Error('손상되거나 중복된 메모가 있습니다. 원본은 변경하지 않았습니다.');
    ids.add(c.id);
  }
  return d;
}
export function serializeNotes(data:NotesData):string {
  validNotes(data);
  const json=JSON.stringify(data).replace(/</g,'\\u003c');
  const text='# 본문 연결 메모\n\n플러그인의 메모 패널에서 수정합니다. 직접 작성할 자유 메모는 별도 Notes 노트에 보관합니다.\n\n<!-- rr-annotations\n'+json+'\n-->\n\n'+data.comments.map(c=>`## ${c.resolved?'해결됨':'메모'} · ${c.anchor||'논문 전체'}\n\n${c.quote.split('\n').map(x=>'> '+x).join('\n')}\n\n${c.text}\n\n작성: ${c.created} · 수정: ${c.updated}\n`).join('\n');
  if(text.length>2_000_000)throw Error('메모 파일 크기 제한을 넘었습니다.');
  return text;
}
export function parseNotes(raw:string,rid:string):NotesData {
  if(raw.length>2_000_000)throw Error('메모 파일이 너무 큽니다.');
  const match=raw.match(/<!-- rr-annotations\n([^\n]+)\n-->/);
  if(!match)throw Error('메모 파일을 읽을 수 없습니다. 원본은 보존됩니다.');
  const data=validNotes(JSON.parse(match[1]),rid);
  if(serializeNotes(data).replace(/\r\n/g,'\n')!==raw.replace(/\r\n/g,'\n'))throw Error('메모 파일이 외부에서 수정되었습니다. 원본을 확인해 주세요.');
  return data;
}
export function updateNote(data:NotesData,id:string,text:string,resolved:boolean,expectedUpdated:string,now:string):NotesData {
  const old=data.comments.find(c=>c.id===id);
  if(!old||old.updated!==expectedUpdated)throw Error('메모가 다른 곳에서 변경되었습니다. 다시 읽은 후 수정해 주세요.');
  const next={...data,comments:data.comments.map(c=>c.id===id?{...c,text, resolved,updated:now}:c)};
  validNotes(next);return next;
}
