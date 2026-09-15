import {App,Modal,EventRef} from 'obsidian';
import {Task,localDay} from './dashboard-data';
import {DashboardRecords,ScheduleRecord,taskEditableText} from './dashboard-records';

class RecordDialog extends Modal {
  protected form!:HTMLFormElement;protected fields!:HTMLElement;protected actions!:HTMLElement;protected error!:HTMLElement;protected busy=false;
  protected setup(title:string){this.modalEl.classList.add('rd-schedule-modal');this.titleEl.textContent=title;this.form=this.contentEl.createEl('form',{cls:'rd-schedule-editor'});this.fields=this.form.createDiv({cls:'rd-schedule-fields'});this.error=this.fields.createEl('p',{cls:'rd-schedule-error',attr:{role:'alert'}});this.error.hidden=true;this.actions=this.form.createDiv({cls:'rd-schedule-actions'});}
  protected field(parent:HTMLElement,label:string,type:string,value:string){const l=parent.createEl('label');l.createSpan({text:label});const i=l.createEl('input',{type,attr:{required:'true','aria-label':label}});i.value=value;return i;}
  protected button(text:string,action:()=>void,cls=''){const b=this.actions.createEl('button',{text,cls,attr:{type:'button'}});b.onclick=action;return b;}
  protected async run(action:()=>Promise<void>,close=true){if(this.busy)return;this.busy=true;this.error.hidden=true;this.form.setAttribute('aria-busy','true');this.actions.querySelectorAll('button').forEach(b=>b.disabled=true);try{await action();if(close)this.close();}catch(e){this.error.textContent=e instanceof Error?e.message:'저장하지 못했습니다. 다시 시도해 주세요.';this.error.hidden=false;this.error.scrollIntoView({block:'nearest'});}finally{this.busy=false;this.form.removeAttribute('aria-busy');this.actions.querySelectorAll('button').forEach(b=>b.disabled=false);}}
  protected deleteButton(text:string,explanation:string,action:()=>Promise<void>){let armed=false;const b=this.button(text,()=>{if(!armed){armed=true;b.textContent='삭제 확인';this.error.textContent=explanation;this.error.hidden=false;this.error.scrollIntoView({block:'nearest'});return;}void this.run(action);},'rd-record-delete');}
  onClose(){this.contentEl.empty();}
}
export class ScheduleEditor extends RecordDialog {
  private minutesEvents:EventRef[]=[];
  constructor(app:App,private records:DashboardRecords,private initial:ScheduleRecord|undefined,private day:string,private create:(title:string,day:string,time:string)=>Promise<void>,private openMinutes:(record:ScheduleRecord)=>Promise<void>,private refresh:()=>void){super(app);}
  onOpen(){
    this.setup(this.initial?'회의 일정 수정':'회의 일정 추가');
    const title=this.field(this.fields,'회의 제목','text',this.initial?.title||'');title.maxLength=90;title.placeholder='예: 연구 진행 상황 논의';
    const row=this.fields.createDiv({cls:'rd-schedule-datetime'}),day=this.field(row,'날짜','date',this.initial?.day||this.day||localDay()),time=this.field(row,'시간','time',this.initial?.time||'09:00');
    const valid=()=>{title.setCustomValidity(title.value.trim()?'':'회의 제목을 입력해 주세요.');return this.form.reportValidity();};title.oninput=()=>title.setCustomValidity('');
    const save=async()=>{if(this.initial)this.initial=await this.records.edit(this.initial,title.value,day.value,time.value);else await this.create(title.value,day.value,time.value);this.refresh();};
    if(this.initial){
      this.deleteButton('일정 삭제','이 일정을 삭제할까요? 작성한 회의록은 그대로 남습니다.',async()=>{await this.records.removeSchedule(this.initial!);this.refresh();});
      const minutes=this.button('',()=>{if(valid())void this.run(async()=>{await save();await this.openMinutes(this.initial!);});},'rd-record-minutes');
      const update=()=>{minutes.textContent=this.records.hasMinutes(this.initial!)?'회의록 열기':'회의록 작성';};update();
      // Also follow deletion/restoration while this dialog remains open.
      this.minutesEvents=[this.app.vault.on('delete',update),this.app.vault.on('create',update),this.app.vault.on('rename',update)];
    }
    this.button('취소',()=>this.close());const submit=this.button(this.initial?'변경 저장':'일정 저장',()=>{},'mod-cta');submit.type='submit';submit.onclick=null;
    this.form.onsubmit=e=>{e.preventDefault();if(valid())void this.run(save);};title.focus();
  }
  onClose(){for(const event of this.minutesEvents)this.app.vault.offref(event);this.minutesEvents=[];super.onClose();}
}
export class TaskEditor extends RecordDialog {
  constructor(app:App,private records:DashboardRecords,private task:Task,private refresh:()=>void){super(app);}
  onOpen(){
    this.setup('할 일 수정');const title=this.field(this.fields,'할 일 내용','text',taskEditableText(this.task));title.maxLength=500;
    this.fields.createEl('p',{cls:'rd-record-help',text:'완료 상태와 기존 날짜는 유지됩니다.'});
    this.deleteButton('할 일 삭제','이 할 일을 삭제할까요? 다른 할 일과 본문은 그대로 남습니다.',async()=>{await this.records.editTask(this.task,null);this.refresh();});
    this.button('취소',()=>this.close());const submit=this.button('변경 저장',()=>{},'mod-cta');submit.type='submit';submit.onclick=null;
    this.form.onsubmit=e=>{e.preventDefault();if(this.form.reportValidity())void this.run(async()=>{await this.records.editTask(this.task,title.value);this.refresh();});};title.focus();
  }
}
export class MeetingCreateModal extends RecordDialog {
  constructor(app:App,private create:(title:string)=>Promise<void>,private kind:'meeting'|'project'='meeting'){super(app);}
  onOpen(){this.setup(this.kind==='project'?'연구 프로젝트 추가':'새 회의록');const title=this.field(this.fields,this.kind==='project'?'프로젝트 이름':'회의 제목','text','');title.maxLength=90;title.placeholder=this.kind==='project'?'진행 중인 연구 과제 이름을 적어 주세요':'회의 제목을 적어 주세요';this.button('취소',()=>this.close());const submit=this.button('작성 시작',()=>{},'mod-cta');submit.type='submit';submit.onclick=null;this.form.onsubmit=e=>{e.preventDefault();if(this.form.reportValidity())void this.run(()=>this.create(title.value));};title.focus();}
}
