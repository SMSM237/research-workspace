import test from 'node:test';import assert from 'node:assert/strict';import path from 'node:path';import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),{resolveCodex,dispatchFailure}=require('./codex-dispatch.test-build.cjs');
test('updated executable is resolved on each send without plugin restart',()=>{
 let version='old';const bin=path.resolve('installed/bin'),old=path.join(bin,'old/codex.exe'),fresh=path.join(bin,'new/codex.exe');
 const fs={existsSync:p=>p===bin||p===(version==='old'?old:fresh),readdirSync:()=>[{name:version,isDirectory:()=>true}],statSync:()=>({mtimeMs:2})};
 assert.equal(resolveCodex(old,bin,fs,path),old);version='new';assert.equal(resolveCodex(old,bin,fs,path),fresh);
});
test('missing executable cannot fall back outside the trusted installation',()=>{
 const fs={existsSync:()=>false};assert.throws(()=>resolveCodex('/elsewhere/codex.exe','/installed/bin',fs,path));
 assert.match(dispatchFailure({code:'ENOENT'}),/실행 파일/);assert.match(dispatchFailure({killed:true}),/초과/);
});
