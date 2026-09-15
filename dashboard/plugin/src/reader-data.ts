export interface FigureSource { imagePath: string; pdfPath: string | null; page: number | null; kind?: 'table'; anchor?: string; }
export function localPath(path: string): boolean {
  return !!path && !/[\\:%?#\u0000]/.test(path) && !path.startsWith('/') &&
    path.split('/').every(part=>part!=='' && part!=='.' && part!=='..');
}
export function sourceMap(raw: unknown, reportId: string): FigureSource[] {
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(reportId)) throw new Error('Invalid report ID');
  const data=raw as {report_id?:unknown;figures?:unknown;standalone?:unknown;sources?:unknown};
  if (!data || data.report_id!==reportId || !Array.isArray(data.figures) || !Array.isArray(data.sources)) throw new Error('Invalid report source map');
  const sources=new Map<string,{document_id?:unknown;page?:unknown;kind?:unknown}>();
  for(const s of data.sources){
    if(!s || typeof s.id!=='string' || sources.has(s.id))throw new Error('Invalid or duplicate source');
    sources.set(s.id,s);
  }
  const images=new Set<string>();
  if(data.standalone!==undefined&&!Array.isArray(data.standalone))throw new Error('Invalid standalone entries');
  const entries=[...data.figures,...(Array.isArray(data.standalone)?data.standalone.filter(e=>e?.image):[])];
  return entries.map(f=>{
    const image=f?.image;const path=image?.path;
    if(typeof path!=='string' || !localPath(path) || !path.startsWith(`Resources/${reportId}/`) || !/\.(png|jpe?g|webp)$/i.test(path) || images.has(path))throw new Error('Invalid or duplicate image');
    images.add(path);
    const src=sources.get(image.source_ref);
    const valid=typeof src?.document_id==='string' && /^[A-Za-z0-9_-]+$/.test(src.document_id) && typeof src.page==='number' && Number.isInteger(src.page) && src.page>0;
    const extra:Partial<FigureSource>=src?.kind==='table'?{kind:'table',...(typeof f.id==='string'&&/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(f.id)?{anchor:f.id}:{})}:{};
    return {imagePath:path,pdfPath:valid?`Sources/${reportId}/${src!.document_id}.pdf`:null,page:valid?src!.page as number:null,...extra};
  });
}
