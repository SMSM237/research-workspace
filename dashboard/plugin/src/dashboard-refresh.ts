// Keep expensive cards mounted when an unrelated vault file changes.
export function shouldRefreshCard(kind:string,path:string):boolean {
  if(!path)return true;
  if(path==='@selection')return ['tasks','calendar','schedules'].includes(kind);
  if(path.startsWith('.research-activity/'))return kind==='home';
  if(path.startsWith('Tasks/'))return ['tasks','weekly','calendar'].includes(kind);
  if(path.startsWith('Projects/'))return ['tasks','weekly','calendar','projects','connections','home'].includes(kind);
  if(path.startsWith('Meetings/'))return ['tasks','weekly','calendar','schedules','meetings','connections','home'].includes(kind);
  if(path.startsWith('Notes/'))return ['tasks','weekly','calendar','home'].includes(kind);
  if(path.startsWith('Paper reports/'))return ['papers','queue','graph','connections','home'].includes(kind);
  if(path.startsWith('Paper/'))return ['queue','graph','home'].includes(kind);
  if(path==='Dashboard/pdf-links.json')return ['queue','graph'].includes(kind);
  if(path==='.figure-reports/dashboard-weather.json')return kind==='home';
  if(/^\.figure-reports\/[^/]+\/analysis\.json$/.test(path))return kind==='graph';
  if(path.startsWith('.figure-reports/'))return kind==='queue';
  if(path.startsWith('.paper-control/'))return kind==='queue';
  if(path==='Dashboard/논문 목록.md')return false;
  return kind==='home';
}
