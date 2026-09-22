import {parseRequest,parseStatus,queuePrompt,statusFor,RunRequest,RunStatus,TERMINAL,UUID} from './remote-data';
export interface RemoteStore {list():Promise<string[]>;readRequest(name:string):Promise<string>;readStatus(id:string):Promise<string|null>;writeStatus(s:RunStatus):Promise<void>;readLedger():Promise<Record<string,RunStatus>>;writeLedger(l:Record<string,RunStatus>):Promise<void>;}
export interface ReceiverConfig {thread:string;runbook:string;}
export class RemoteReceiver {
  private busy=false;
  constructor(private store:RemoteStore,private config:ReceiverConfig,private send:(thread:string,message:string)=>Promise<string>) {
    if(!UUID.test(config.thread))throw Error('Invalid local thread');
  }
  async tick():Promise<void> {
    if(this.busy)return;this.busy=true;
    try {
      const ledger=await this.store.readLedger();
      // Local journal wins over a synced status that could be stale or edited.
      for(const s of Object.values(ledger)) {
        if(TERMINAL.has(s.state))continue;
        if(s.state==='dispatching'){
          s.state='blocked';s.message='이전 전달 결과를 확인할 수 없습니다. 중복 분석을 막기 위해 재전송하지 않았습니다.';
          s.updatedAt=new Date().toISOString();await this.store.writeLedger(ledger);await this.store.writeStatus(s);
        }
        return;
      }
      const names=(await this.store.list()).filter(n=>UUID.test(n.replace(/\.json$/,''))&&n.endsWith('.json')).sort();
      if(names.length>1000)throw Error('실행 요청이 1,000개를 넘습니다. PC에서 기록을 정리해 주세요.');
      const requests:RunRequest[]=[];
      for(const name of names) {
        if(ledger[name.slice(0,-5)])continue;
        try{requests.push(parseRequest(await this.store.readRequest(name),name));}catch{continue;}
      }
      requests.sort((a,b)=>a.createdAt.localeCompare(b.createdAt));
      const r=requests[0];if(!r)return;
      if(Date.now()-Date.parse(r.createdAt)>7*86400000){
        ledger[r.id]=statusFor(r,'cancelled','7일 이상 지난 요청입니다. 오래된 작업의 자동 실행을 취소했습니다.');
        await this.store.writeLedger(ledger);await this.store.writeStatus(ledger[r.id]);return;
      }
      ledger[r.id]=statusFor(r,'dispatching','Windows에서 Codex에 실행 요청을 전달합니다.');
      await this.store.writeLedger(ledger);await this.store.writeStatus(ledger[r.id]);
      try {
        const messageId=await this.send(this.config.thread,queuePrompt(r.id,r.action==='diagnostic',this.config.runbook,r.version===2?{path:r.path,sha256:r.sha256}:undefined));
        if(!UUID.test(messageId))throw Error('요청 접수 번호를 받지 못했습니다.');
        const fresh=await this.store.readLedger();
        ledger[r.id]=fresh[r.id]&&fresh[r.id].state!=='dispatching'?fresh[r.id]:{...statusFor(r,'queued','Codex가 요청을 접수했습니다. 실제 작업 시작을 기다립니다.'),queueMessageId:messageId};
      } catch {
        ledger[r.id]=statusFor(r,'blocked','Codex 전달 결과를 확인하지 못했습니다. PC에서 확인해야 하며 자동 재전송하지 않습니다.');
      }
      await this.store.writeLedger(ledger);await this.store.writeStatus(ledger[r.id]);
    } finally {this.busy=false;}
  }
}
