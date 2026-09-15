import test from 'node:test';
import assert from 'node:assert/strict';
import {statusModel,sharedStatusModel} from './status-data.test-build.cjs';
const now=Date.parse('2026-09-09T08:00:00Z');
const record=(stage,more={})=>({version:1,stage,updated_at:new Date(now).toISOString(),...more});
test('missing worker is disconnected, never running',()=>{const s=statusModel(null,now);assert.equal(s.connection,'disconnected');assert.equal(s.running,false);});
test('explicit connecting and connected idle remain distinct',()=>{assert.equal(statusModel(record('waiting',{connection:'connecting'}),now).connection,'connecting');const s=statusModel(record('waiting'),now);assert.equal(s.connection,'connected');assert.equal(s.running,false);});
test('only active analysis stages animate with actual counts',()=>{for(const stage of ['parsing','figure_analysis','integration','qc'])assert.equal(statusModel(record(stage),now).running,true);for(const stage of ['queued','waiting','complete','failed'])assert.equal(statusModel(record(stage),now).running,false);assert.match(statusModel(record('figure_analysis',{figures_done:2,figures_total:7,supplements_done:1,supplements_total:9}),now).counts,/Figure 2\/7 · 서플 1\/9/);});
test('stale completed record is not proof of a live connection',()=>{const s=statusModel(record('complete',{updated_at:'2000-01-01T00:00:00Z'}),now);assert.equal(s.connection,'disconnected');assert.equal(s.running,false);assert.match(s.detail,/완료/);});
test('invalid stage, future heartbeat and impossible counts fail closed',()=>{for(const r of [record('toString'),record('qc',{updated_at:'2100-01-01T00:00:00Z'}),record('qc',{figures_done:8,figures_total:7}),record('qc',{connection:'invented'})]){const s=statusModel(r,now);assert.equal(s.connection,'disconnected');assert.equal(s.running,false);assert.match(s.detail,/확인/);}});
test('a disconnected worker never animates despite an active stage',()=>{const s=statusModel(record('figure_analysis',{connection:'disconnected'}),now);assert.equal(s.connection,'disconnected');assert.equal(s.running,false);});
test('prepared is an idle checkpoint, never scientific completion',()=>{const s=statusModel(record('prepared'),now);assert.equal(s.connection,'connected');assert.equal(s.running,false);assert.equal(s.stage,'자료 준비 완료');});

test('critical review animates while completed findings wait for review',()=>{const active=statusModel(record('critical_review'),now);assert.equal(active.connection,'connected');assert.equal(active.running,true);const pending=statusModel(record('review'),now);assert.equal(pending.connection,'connected');assert.equal(pending.running,false);assert.equal(pending.stage,'분석 결과 검토 대기');});

test('Git snapshot preserves old progress without claiming a live connection',()=>{
 const s=sharedStatusModel(record('figure_analysis',{transport:'git_snapshot',updated_at:'2026-09-01T00:00:00Z',figures_done:2,figures_total:7}),now);
 assert.equal(s.connection,'snapshot');assert.equal(s.running,false);assert.equal(s.stage,'Figure 분석 중');assert.match(s.counts,/2\/7/);assert.match(s.detail,/실시간 연결 상태가 아닙니다/);
});
test('missing and malformed snapshots remain visibly unavailable',()=>{
 assert.equal(sharedStatusModel(null,now).label,'상태 동기화 대기');
 for(const r of [[],record('qc'),record('qc',{transport:'git_snapshot',updated_at:'2100-01-01'}),record('qc',{transport:'git_snapshot',figures_done:8,figures_total:7})]){
  const s=sharedStatusModel(r,now);assert.equal(s.connection,'snapshot');assert.equal(s.running,false);assert.equal(s.stage,'');assert.match(s.detail,/읽지 못했습니다/);
 }
});
