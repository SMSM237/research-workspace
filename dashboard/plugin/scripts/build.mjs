/** Local build without a network dependency. Requires TypeScript locally or globally.
 * Transpilation catches syntax errors, NOT SDK semantic type errors. Run npm run
 * typecheck separately with the installed official Obsidian SDK before release.
 */
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
const require=createRequire(import.meta.url);
let ts;
try { ts=require('typescript'); }
catch {
  const npm=process.platform==='win32'?'npm.cmd':'npm';
  const root=execFileSync(npm,['root','-g'],{encoding:'utf8',shell:process.platform==='win32'}).trim();
  ts=require(resolve(root,'typescript'));
}
const compile=(file)=>{
  const result=ts.transpileModule(readFileSync(file,'utf8'),{fileName:file,reportDiagnostics:true,
    compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.CommonJS,strict:true,esModuleInterop:true}});
  const errors=(result.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error);
  if(errors.length)throw new Error(ts.formatDiagnosticsWithColorAndContext(errors,{getCanonicalFileName:x=>x,getCurrentDirectory:()=>process.cwd(),getNewLine:()=> '\n'}));
  return result.outputText;
};
writeFileSync('paper-relations.test-build.cjs',compile('src/paper-relations.ts'));
writeFileSync('daily-verse.test-build.cjs',compile('src/daily-verse.ts'));
writeFileSync('task-celebration.test-build.cjs',compile('src/task-celebration.ts'));
const policy=compile('src/policy.ts');
writeFileSync('policy.test-build.cjs',policy);
const readerData=compile('src/reader-data.ts');
writeFileSync('reader-data.test-build.cjs',readerData);
writeFileSync('annotation-data.test-build.cjs',compile('src/annotation-data.ts'));
writeFileSync('status-data.test-build.cjs',compile('src/status-data.ts'));
writeFileSync('dashboard-data.test-build.cjs',compile('src/dashboard-data.ts'));
writeFileSync('dashboard-records.test-build.cjs',compile('src/dashboard-records.ts'));
writeFileSync('meeting-data.test-build.cjs',compile('src/meeting-data.ts'));
writeFileSync('remote-data.test-build.cjs',compile('src/remote-data.ts'));
writeFileSync('remote-receiver.test-build.cjs',compile('src/remote-receiver.ts').replaceAll('require("./remote-data")','require("./remote-data.test-build.cjs")'));
if(!process.argv.includes('--policy-only')) {
  const marker='/* Research Dashboard bundled styles */';
  writeFileSync('styles.css',readFileSync('styles.css','utf8').split(marker)[0].trimEnd()+'\n'+marker+'\n'+readFileSync('dashboard.css','utf8')+'\n'+readFileSync('color-cards.css','utf8')+'\n'+readFileSync('meeting.css','utf8')+'\n'+readFileSync('remote-control.css','utf8')+'\n'+readFileSync('graph3d.css','utf8')+'\n'+readFileSync('dashboard-layout.css','utf8'));
  const names=['paper-relations','graph-3d','daily-verse','policy','reader-data','annotation-data','status-data','dashboard-data','dashboard-extras','dashboard-records','record-dialogs','meeting-data','meeting-view','task-celebration','dashboard','library','annotations','mobile-reader','remote-data','remote-receiver','remote-control','main'];
  const modules=names.map(name=>`${JSON.stringify('./'+name)}:(module,exports,require)=>{\n${compile('src/'+name+'.ts')}\n}`).join(',\n');
  writeFileSync('main.js',`Object.assign(exports,(()=>{const modules={${modules}};const cache={};const load=(id)=>{if(!modules[id])return require(id);if(cache[id])return cache[id].exports;const m={exports:{}};cache[id]=m;modules[id](m,m.exports,load);return m.exports;};return load('./main');})());\n`);
}
console.log(`TypeScript ${ts.version}: syntax transpilation complete. Full SDK typecheck is separate.`);
