import test from 'node:test';
import assert from 'node:assert/strict';
import { desiredOpen } from './policy.test-build.cjs';

test('critical context is never collapsed', () => {
  for (const mode of ['summary','standard','detail']) {
    assert.equal(desiredOpen('rr-critical',mode,false), true);
  }
});
test('standard opens narrative but keeps details closed', () => {
  assert.equal(desiredOpen('rr-body','standard',true), true);
  assert.equal(desiredOpen('rr-detail','standard',true), false);
});
test('detail opens all report callouts even with optional concepts off', () => {
  assert.equal(desiredOpen('rr-concept','detail',false), true);
  assert.equal(desiredOpen('rr-detail','detail',false), true);
});
test('unrelated callouts remain untouched', () => {
  assert.equal(desiredOpen('warning','summary',false), null);
});
test('summary leaves concept titles accessible', () => {
  assert.equal(desiredOpen('rr-concept','summary',true), false);
});

test('supplements stay collapsed in standard/summary and open in detail',()=>{
  assert.equal(desiredOpen('rr-supplement','standard',true),false);
  assert.equal(desiredOpen('rr-supplement','summary',true),false);
  assert.equal(desiredOpen('rr-supplement','detail',false),true);
});
