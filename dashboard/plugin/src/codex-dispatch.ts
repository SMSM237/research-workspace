/** Resolve on every submission: desktop updates remove the previous bin directory. */
export function resolveCodex(configured:string,bin:string,fs:any,path:any):string {
  if(fs.existsSync(configured))return configured;
  const resolved=path.resolve(configured).toLowerCase(),root=path.resolve(bin).toLowerCase();
  if(path.basename(resolved)!=='codex.exe'||!resolved.startsWith(root+path.sep))throw Error('PC 분석 실행 파일 경로를 확인해 주세요.');
  const candidates=fs.existsSync(bin)?fs.readdirSync(bin,{withFileTypes:true}).filter((d:any)=>d.isDirectory()).map((d:any)=>path.join(bin,d.name,'codex.exe')).filter((p:string)=>fs.existsSync(p)).sort((a:string,b:string)=>fs.statSync(b).mtimeMs-fs.statSync(a).mtimeMs):[];
  if(!candidates.length)throw Error('Codex 실행 파일이 없습니다. 앱 업데이트가 끝난 뒤 연결을 확인해 주세요.');
  return candidates[0];
}
export function dispatchFailure(error:any):string {
  if(error?.code==='ENOENT')return 'Codex 실행 파일이 변경되어 요청을 보내지 못했습니다.';
  if(error?.killed||error?.code==='ETIMEDOUT')return 'Codex 전달 시간이 초과되었습니다. 중복 방지를 위해 자동 재전송하지 않습니다.';
  return 'Codex 전달 결과를 확인하지 못했습니다. PC 확인이 필요하며 자동 재전송하지 않습니다.';
}
