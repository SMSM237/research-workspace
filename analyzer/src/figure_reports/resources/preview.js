(() => {
  'use strict';
  const root = document.getElementById('content');
  let mode='standard', concepts=true;
  const status=document.getElementById('mode-status');
  function apply() {
    root.dataset.mode=mode;
    root.querySelectorAll('details[data-kind]').forEach(el => {
      const k=el.dataset.kind;
      el.open = mode==='detail' || (mode==='standard' && (k==='rr-body' || (k==='rr-concept' && concepts)));
    });
    document.querySelectorAll('[data-mode]').forEach(el=>{ if(el.tagName==='BUTTON') el.setAttribute('aria-pressed',String(el.dataset.mode===mode)); });
    const toggle=document.getElementById('concept-toggle');
    toggle.setAttribute('aria-pressed',String(concepts));
    toggle.textContent=concepts?'개념 설명 펼침':'개념 설명 접힘';
    status.textContent=({summary:'요약',standard:'표준',detail:'상세'})[mode]+' 보기. 중요한 해석 범위와 개념은 항상 유지됩니다.';
  }
  document.querySelectorAll('button[data-mode]').forEach(btn=>btn.addEventListener('click',()=>{mode=btn.dataset.mode;apply();}));
  document.getElementById('concept-toggle').addEventListener('click',()=>{concepts=!concepts;if(mode==='detail')mode='standard';apply();});
  function reveal(target) {
    if(target.tagName==='DETAILS')target.open=true;
    let parent=target.parentElement;
    while(parent){ if(parent.tagName==='DETAILS')parent.open=true; parent=parent.parentElement; }
    target.scrollIntoView({block:'start'});
  }
  document.addEventListener('click',e=>{
    const a=e.target.closest('a[href^="#"]');if(!a)return;
    const target=document.getElementById(a.getAttribute('href').slice(1));
    if(target){e.preventDefault();reveal(target);try{history.replaceState(null,'',a.getAttribute('href'));}catch(_){}}
  });
  const dialog=document.getElementById('image-dialog');
  document.querySelectorAll('.figure-zoom').forEach(btn=>btn.addEventListener('click',()=>{
    const img=btn.querySelector('img');const big=dialog.querySelector('img');big.src=img.src;big.alt=img.alt;
    dialog.querySelector('p').textContent=img.alt;dialog.showModal();
  }));
  document.getElementById('close-dialog').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
  apply();
})();
