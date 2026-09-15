export type Depth = 'summary' | 'standard' | 'detail';
/** null means an unrelated/native callout that this plugin must not change. */
export function desiredOpen(kind: string, depth: Depth, conceptsExpanded: boolean): boolean | null {
  if (kind === 'rr-critical') return true;
  if (!['rr-body','rr-detail','rr-concept','rr-supplement'].includes(kind)) return null;
  if (depth === 'detail') return true;
  if (depth === 'summary') return false;
  return kind === 'rr-body' || (kind === 'rr-concept' && conceptsExpanded);
}
