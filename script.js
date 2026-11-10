"use strict";
// All data was rendered by the original server at export time. No DB/API calls.
const $all = (selector, root=document) => [...root.querySelectorAll(selector)];
// Detail tabs must follow the actual header height at every breakpoint.
const siteHeader = document.querySelector('body > header');
if (siteHeader) {
  const syncHeaderHeight = () => document.documentElement.style.setProperty('--site-header-height', `${siteHeader.getBoundingClientRect().height}px`);
  syncHeaderHeight();
  new ResizeObserver(syncHeaderHeight).observe(siteHeader);
}
const notice = () => document.getElementById('offline-dialog').showModal();
// Explain the application form before handing off to a mail composer.
const applicationLink = $all('a[href^="mailto:"]').find(a => a.textContent.trim() === '참가 신청하기');
if (applicationLink) {
  const mail = new URL(applicationLink.href);
  const guide = document.createElement('dialog');
  guide.id = 'application-guide';
  guide.setAttribute('aria-labelledby', 'application-guide-title');
  guide.innerHTML = `
    <h2 id="application-guide-title">데모데이 참가 신청 안내</h2>
    <p>아래 절차에 따라 신청 메일을 보내주세요.</p>
    <ol>
      <li><strong>메일 작성 화면 열기</strong><br>Gmail 또는 기본 메일 앱을 선택하세요. 받는 사람·제목·신청 양식이 자동으로 입력됩니다.</li>
      <li><strong>신청 정보 작성하기</strong><br>회사명(팀명), 담당자명, 연락처, 이메일, 서비스명과 소개, 참가 희망 데모데이, 문의사항을 채워주세요.</li>
      <li><strong>내용 확인 후 전송하기</strong><br>작성 내용을 확인하고 메일 화면에서 직접 전송하면 됩니다.</li>
    </ol>
    <div class="application-mail-summary"><strong>받는 사람</strong><span data-mail-recipient></span><strong>제목</strong><span data-mail-subject></span></div>
    <p class="application-guide-note">Gmail은 Google 로그인이 필요합니다. 기본 메일 앱은 기기에 설정된 앱으로 열립니다. 버튼을 눌러도 메일이 자동 발송되지는 않습니다.</p>
    <div class="application-guide-actions"><button type="button" data-guide-close autofocus>닫기</button><a data-default-mail>기본 메일 앱으로 작성</a><a data-gmail target="_blank" rel="noopener noreferrer">Gmail로 작성</a></div>`;
  guide.querySelector('[data-mail-recipient]').textContent = mail.pathname;
  guide.querySelector('[data-mail-subject]').textContent = mail.searchParams.get('subject') || '';
  guide.querySelector('[data-default-mail]').href = applicationLink.href;
  const gmail = new URL('https://mail.google.com/mail/');
  gmail.search = new URLSearchParams({view:'cm', fs:'1', to:mail.pathname, su:mail.searchParams.get('subject') || '', body:mail.searchParams.get('body') || ''}).toString();
  guide.querySelector('[data-gmail]').href = gmail.href;
  guide.querySelector('[data-guide-close]').addEventListener('click', () => guide.close());
  document.body.append(guide);
  applicationLink.setAttribute('aria-haspopup', 'dialog');
  applicationLink.addEventListener('click', event => { event.preventDefault(); guide.showModal(); });
}
const closeModals = () => {
  $all('.modal-layer.offline-open').forEach(x => x.classList.remove('offline-open'));
  document.body.classList.remove('no-scroll');
};
function openModal(selector) {
  const modal=document.querySelector(selector);
  if (!modal) return notice();
  closeModals();modal.classList.add('offline-open');document.body.classList.add('no-scroll');
  modal.querySelector('input:not([type=hidden]),button,a')?.focus();
}
function revealBatch(selector, key, button) {
  const items=$all(selector);const hidden=items.filter(x=>x.hidden);
  if (!hidden.length) { if(button)button.hidden=true;return; }
  const batch=hidden[0].dataset[key];
  hidden.filter(x=>x.dataset[key]===batch).forEach(x=>x.hidden=false);
  if(button)button.hidden=!items.some(x=>x.hidden);
}
$all('#endContest-list>[data-snapshot-batch]').forEach(x=>x.hidden=x.dataset.snapshotBatch!=='0');
$all('#moreFunding>[data-company-batch]').forEach(x=>x.hidden=x.dataset.companyBatch!=='0');
$all('#changup-card-list>[data-news-batch]').forEach(x=>x.hidden=x.dataset.newsBatch!=='0');
const endMore=document.getElementById('more-endContest-btn');
if(endMore)endMore.hidden=!$all('#endContest-list>li').some(x=>x.hidden);
$all('[data-original-action*="moreFunding"]').forEach(x=>x.hidden=!$all('#moreFunding>li').some(y=>y.hidden));
$all('form').forEach(form=>form.addEventListener('submit',event=>{event.preventDefault();notice();}));
document.addEventListener('click',event=>{
  const target=event.target.closest('a,button,[data-original-action],.close-modal');
  if(!target)return;
  if(target.matches('[data-close-offline]')){document.getElementById('offline-dialog').close();return;}
  if(target.dataset.toggle==='modal' && target.dataset.target){event.preventDefault();openModal(target.dataset.target);return;}
  if(target.matches('.close-modal,.close-btn') || target.dataset.originalAction?.includes('forceHideModal')){event.preventDefault();closeModals();return;}
  if(target.matches('.go-to-top')){event.preventDefault();window.scrollTo({top:0,behavior:'smooth'});return;}
  if(target.dataset.unavailable){event.preventDefault();notice();return;}
  const action=target.dataset.originalAction||'';
  if(action.includes('toggleMobileMenu')){
    event.preventDefault();const nav=document.getElementById('neoFullNavMenu');
    const active=!nav.classList.contains('active');
    ['active','expand','expand-delay'].forEach(c=>nav.classList.toggle(c,active));
    target.classList.toggle('active',active);target.setAttribute('aria-expanded',String(active));return;
  }
  if(action.includes('showLogin')||action.includes('loginModal')){event.preventDefault();openModal('#header-login-layer');return;}
  if(action.includes('moreEndContest')){event.preventDefault();revealBatch('#endContest-list>li','snapshotBatch',target);return;}
  if(action.includes('moreFunding')){event.preventDefault();revealBatch('#moreFunding>li','companyBatch',target);return;}
  if(action.includes('changupTable.moreList')){event.preventDefault();revealBatch('#changup-card-list>[data-news-batch]','newsBatch',target);return;}
  if(action.includes('forceHideModal')||action.includes('hideInnerModal')){event.preventDefault();closeModals();return;}
  if(action.includes('showModal')){
    event.preventDefault();const match=action.match(/showModal\(['"]([^'"]+)/);if(match)openModal(match[1]);else notice();return;
  }
  if(target.dataset.localLink)return;
  if(action && (!target.getAttribute('href')||target.getAttribute('href')==='#')){event.preventDefault();notice();}
});
document.addEventListener('keydown',event=>{if(event.key==='Escape')closeModals();});
$all('.modal-layer').forEach(x=>x.addEventListener('click',event=>{if(event.target===x)closeModals();}));
// Original home news/statistics switch, with the original DOM and CSS.
const sections=$all('.swap-content>section.swap');const dots=$all('.swap-indicator .swap-dot');
let active=sections.findIndex(x=>x.classList.contains('active'));
function swap(index){active=index;sections.forEach((x,i)=>x.classList.toggle('active',i===index));dots.forEach((x,i)=>x.classList.toggle('active',i===index));}
if(sections.length>1){dots.forEach((x,i)=>{x.tabIndex=0;x.setAttribute('role','button');x.setAttribute('aria-label',i===0?'창업지원 공고':'서비스 통계');x.addEventListener('click',()=>swap(i));x.addEventListener('keydown',e=>{if(e.key==='Enter')swap(i);});});setInterval(()=>{if(!document.hidden)swap((active+1)%sections.length);},6000);}
const slides=$all('#mainBanner>.swiper-wrapper>.swiper-slide');let slide=0;
if(slides.length>1){function showSlide(index){slide=(index+slides.length)%slides.length;slides.forEach((x,i)=>x.hidden=i!==slide);}showSlide(0);document.querySelector('.swiper-button-next')?.addEventListener('click',()=>showSlide(slide+1));document.querySelector('.swiper-button-prev')?.addEventListener('click',()=>showSlide(slide-1));setInterval(()=>showSlide(slide+1),10000);}else document.querySelector('.swiper-button-area')?.setAttribute('hidden','');
// Region selection uses embedded snapshots, not the source server.
const regionRows=$all('ul.regional-table li.data[data-id]');
function selectRegion(id){
  const template=document.getElementById('region-'+id);const container=document.querySelector('section.contest-list.map-type');
  if(!template||!container)return;
  $all('#fundingMap path,ul.regional-table li.data').forEach(x=>x.classList.toggle('pointed',x.dataset.id===id));
  container.replaceChildren(template.content.cloneNode(true));container.scrollIntoView({behavior:'smooth',block:'start'});
}
regionRows.forEach(row=>{
 const id=row.dataset.id;row.tabIndex=0;row.setAttribute('role','button');row.addEventListener('click',()=>selectRegion(id));row.addEventListener('keydown',e=>{if(e.key==='Enter')selectRegion(id);});
 $all('#fundingMap path').filter(x=>x.dataset.id===id).forEach(path=>{path.classList.remove('inactive');path.classList.add('active');path.addEventListener('click',()=>selectRegion(id));});
});
// Original detail tabs have matching fragment IDs; retain ordinary anchor behavior.
$all('a[href^="#"]').forEach(a=>{const href=a.getAttribute('href');if(href.length<2)return;let panel;try{panel=document.querySelector(href);}catch{return;}if(!panel)return;a.addEventListener('click',()=>{panel.hidden=false;});});
