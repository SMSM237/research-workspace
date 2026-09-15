export const VERSES = [
 ['시편 119:105','주의 말씀은 내 발에 등이요 내 길에 빛이니이다','PSA.119'],
 ['잠언 16:9','사람이 마음으로 자기의 길을 계획할지라도 그의 걸음을 인도하시는 이는 여호와시니라','PRO.16'],
 ['시편 23:1','여호와는 나의 목자시니 내게 부족함이 없으리로다','PSA.23'],
 ['시편 63:7','주는 나의 도움이 되셨음이라 내가 주의 날개 그늘에서 즐겁게 부르리이다','PSA.63'],
 ['시편 46:1','하나님은 우리의 피난처시요 힘이시니 환난 중에 만날 큰 도움이시라','PSA.46'],
 ['시편 119:50','이 말씀은 나의 고난 중의 위로라 주의 말씀이 나를 살리셨기 때문이니이다','PSA.119'],
 ['잠언 16:3','너의 행사를 여호와께 맡기라 그리하면 네가 경영하는 것이 이루어지리라','PRO.16'],
 ['시편 23:3','내 영혼을 소생시키시고 자기 이름을 위하여 의의 길로 인도하시는도다','PSA.23'],
 ['시편 63:8','나의 영혼이 주를 가까이 따르니 주의 오른손이 나를 붙드시거니와','PSA.63'],
 ['시편 46:7','만군의 여호와께서 우리와 함께 하시니 야곱의 하나님은 우리의 피난처시로다 (셀라)','PSA.46'],
] as const;
// Short quotations verified against Korean Bible Society. NKRV copyright 1998 KBS.
// Calendar dates, not elapsed local milliseconds: DST and restarts do not shift a day.
export function dailyVerse(now=new Date()){
 const day=Math.floor(Date.UTC(now.getFullYear(),now.getMonth(),now.getDate())/86400000);
 const [ref,text,chapter]=VERSES[((day-20711)%VERSES.length+VERSES.length)%VERSES.length];
 return {ref,text,url:'https://bible.bskorea.or.kr/bible/NKRV/'+chapter};
}
export function millisUntilNextDay(now=new Date()){
 return Math.max(50,+new Date(now.getFullYear(),now.getMonth(),now.getDate()+1)-+now+50);
}
