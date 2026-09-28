import test from 'node:test';
import assert from 'node:assert/strict';
import {shouldRefreshCard} from './dashboard-refresh.test-build.cjs';

test('adding a task updates task views without rebuilding the PDF queue or 3D graph',()=>{
  const affected=['home','graph','tasks','weekly','projects','queue','calendar','schedules','meetings','papers']
    .filter(kind=>shouldRefreshCard(kind,'Tasks/할 일.md'));
  assert.deepEqual(affected,['tasks','weekly','calendar']);
  assert.equal(shouldRefreshCard('queue','@selection'),false);
  assert.equal(shouldRefreshCard('graph','@selection'),false);
  assert.equal(shouldRefreshCard('home','.research-activity/2026-09-28/abc.json'),true);
  assert.equal(shouldRefreshCard('queue','.research-activity/2026-09-28/abc.json'),false);
  assert.equal(shouldRefreshCard('queue','.figure-reports/dashboard-weather.json'),false);
});

test('PDF and report changes still update the pending list and graph',()=>{
  for(const path of ['Paper/new.pdf','Paper reports/new.md','Dashboard/pdf-links.json']){
    assert.equal(shouldRefreshCard('queue',path),true,path);
    assert.equal(shouldRefreshCard('graph',path),true,path);
  }
  assert.equal(shouldRefreshCard('papers','Paper reports/new.md'),true);
  assert.equal(shouldRefreshCard('tasks','Paper/new.pdf'),false);
  assert.equal(shouldRefreshCard('queue','News/story.md'),false);
  assert.equal(shouldRefreshCard('queue',''),true);
});
