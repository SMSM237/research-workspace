import test from 'node:test';
import assert from 'node:assert/strict';
import {dailyVerse,millisUntilNextDay,VERSES} from './daily-verse.test-build.cjs';
test('daily verses are stable offline and differ on each new local date',()=>{
 const start=new Date(2026,8,15);let previous;const seen=new Set();
 for(let i=0;i<VERSES.length;i++){let d=new Date(2026,8,15+i);const v=dailyVerse(d);assert.notEqual(v.ref,previous);assert.deepEqual(v,dailyVerse(new Date(d.getFullYear(),d.getMonth(),d.getDate(),23,59)));seen.add(v.ref);previous=v.ref;assert.match(v.url,/^https:\/\/bible.bskorea.or.kr\/bible\/NKRV\//);}
 assert.equal(seen.size,VERSES.length);
 for(const d of [new Date(2026,11,31,23,59,59),new Date(2028,1,29,23,59,59)]){assert.notEqual(dailyVerse(d).ref,dailyVerse(new Date(+d+1000)).ref);assert.equal(millisUntilNextDay(d),1050);}
});
