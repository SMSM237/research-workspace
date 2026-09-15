import {Plugin,TFile,requestUrl} from 'obsidian';
import {localDay,validDay} from './dashboard-data';

const WEATHER='.figure-reports/dashboard-weather.json';
export class DashboardExtras {
  private seen=new Set<string>();private pending=Promise.resolve();private request:Promise<string>|null=null;
  private place={name:'서울',lat:37.57,lon:126.98};private weatherText='서울 · 날씨 확인 중';private checked=0;
  constructor(private plugin:Plugin,private refresh:()=>void){
    const record=(file:any)=>{if(!(file instanceof TFile)||file.extension!=='md'||! /^(Tasks|Projects|Meetings|Notes)\//.test(file.path)||file.path.includes('__QA')||file.basename.startsWith('QA '))return;
      const day=localDay(),key=day+'/'+file.path;if(this.seen.has(key))return;this.seen.add(key);
      this.pending=this.pending.then(async()=>{if(file.path.startsWith('Projects/Plans/')&&!/^\s*[-*+] \[[ xX]\]/m.test(await this.plugin.app.vault.read(file))){this.seen.delete(key);return;}const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(file.path)))).map(n=>n.toString(16).padStart(2,'0')).join('');const folder='.research-activity/'+day,a=this.plugin.app.vault.adapter;if(!await a.exists(folder))await a.mkdir(folder);const path=folder+'/'+hash+'.json';if(!await a.exists(path))await a.write(path,JSON.stringify({day,path:file.path}));this.refresh();}).catch(()=>{this.seen.delete(key);});
    };
    plugin.registerEvent(plugin.app.vault.on('modify',record));plugin.registerEvent(plugin.app.vault.on('create',record));
  }
  async activity(){const counts:Record<string,number>={},a=this.plugin.app.vault.adapter;if(!await a.exists('.research-activity'))return counts;for(const dir of (await a.list('.research-activity')).folders){const day=dir.split('/').pop()!;if(validDay(day))counts[day]=(await a.list(dir)).files.filter(p=>/[a-f0-9]{64}\.json$/.test(p)).length;}return counts;}
  async useLocation(){if(!navigator.geolocation)throw Error('이 기기에서 위치 조회를 지원하지 않습니다. 서울 날씨를 유지합니다.');const p=await new Promise<GeolocationPosition>((resolve,reject)=>navigator.geolocation.getCurrentPosition(resolve,()=>reject(Error('위치를 확인하지 못했습니다. 서울 버튼으로 기본 날씨를 볼 수 있습니다.')),{timeout:10000,maximumAge:3600000,enableHighAccuracy:false}));this.place={name:'현재 위치',lat:Math.round(p.coords.latitude*100)/100,lon:Math.round(p.coords.longitude*100)/100};this.checked=0;return this.weather(true);}
  async seoul(){this.place={name:'서울',lat:37.57,lon:126.98};this.checked=0;return this.weather(true);}
  weather(force=false):Promise<string>{if(this.request)return this.request;if(!force&&Date.now()-this.checked<1800000)return Promise.resolve(this.weatherText);this.request=this.fetchWeather().finally(()=>{this.request=null;});return this.request;}
  private async fetchWeather(){const a=this.plugin.app.vault.adapter;let cached:any=null;try{cached=JSON.parse(await a.read(WEATHER));}catch{}
    const match=cached?.place?.lat===this.place.lat&&cached?.place?.lon===this.place.lon;
    if(match&&Number.isFinite(cached.at)&&Date.now()-cached.at>=0&&Date.now()-cached.at<1800000&&typeof cached.text==='string'){this.checked=cached.at;return this.weatherText=cached.text;}
    try{const p=this.place;let timer:number|undefined;const data=await Promise.race([requestUrl({url:`https://api.open-meteo.com/v1/forecast?latitude=${p.lat}&longitude=${p.lon}&current=temperature_2m,weather_code&timezone=auto`}).then(r=>r.json),new Promise<never>((_,reject)=>{timer=window.setTimeout(()=>reject(Error('timeout')),10000);})]).finally(()=>window.clearTimeout(timer));
      const c=data.current;if(!Number.isFinite(c?.temperature_2m)||!Number.isFinite(c?.weather_code)||data.current_units?.temperature_2m!=='°C')throw Error('invalid weather');const code=c.weather_code,condition=code===0?'맑음':code<=3?'구름':code<=48?'안개':code<=67?'비':code<=77?'눈':code<=82?'소나기':code<=86?'눈':code>=95?'뇌우':'날씨';
      this.checked=Date.now();this.weatherText=`${p.name} · ${Math.round(c.temperature_2m)}°C ${condition}`;if(!await a.exists('.figure-reports'))await a.mkdir('.figure-reports');await a.write(WEATHER,JSON.stringify({place:p,at:this.checked,text:this.weatherText}));return this.weatherText;
    }catch{this.checked=Date.now()-1500000;return this.weatherText=match&&typeof cached.text==='string'?`${cached.text} · 저장된 날씨 (${new Date(cached.at).toLocaleString('ko-KR')})`:`${this.place.name} · 날씨 연결을 확인해 주세요`;}
  }
}
