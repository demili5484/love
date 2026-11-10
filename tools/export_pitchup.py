"""Export public, server-rendered Pitchup pages without a runtime database.

Requires the original application at localhost:8082 and beautifulsoup4.
Only explicit public GET routes are fetched; account mutations are never requested.
"""
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote
from urllib.request import urlopen
from bs4 import BeautifulSoup, Comment
import re, json, shutil, hashlib, os

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('D:/dev/pitchup/src/main/webapp')
UPLOAD = Path('D:/dev/storage/www.pitchup.kr/upload')
BASE = 'http://127.0.0.1:8082'
REPORT = {'pages': {}, 'missing_assets': [], 'failed_pages': {}}
CACHE = ROOT / '.snapshot-cache'
CACHE.mkdir(exist_ok=True)
routes = {'/':'index.html', '/intro':'index.html', '/contest/map':'map.html', '/changup':'changup.html', '/live/ensl':'live.html', '/user/login':'login.html', '/user/register':'register.html'}
documents = {}
assets = set()

def fetch(route):
    cache = CACHE / (hashlib.sha256(route.encode()).hexdigest()+'.html')
    if cache.exists(): return cache.read_text(encoding='utf-8')
    with urlopen(BASE+route, timeout=40) as r:
        html = r.read().decode('utf-8')
    cache.write_text(html,encoding='utf-8')
    return html

def soup(route): return BeautifulSoup(fetch(route), 'html5lib')
def write(path,text):
    p=ROOT/path; p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')

def asset(value, context='/'):
    if not value or value.startswith(('data:','#','mailto:','javascript:')): return value
    full=urlsplit(urljoin(BASE+context,value)); path=unquote(full.path)
    if path=='/file/':
        return 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
    if full.hostname=='img.youtube.com':
        relative='media/video-'+hashlib.sha256(value.encode()).hexdigest()[:16]+'.jpg'
        dest=ROOT/relative;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():
            with urlopen(value,timeout=20) as response:dest.write_bytes(response.read())
        assets.add(relative);return relative
    # Copy only the original application's static resources and public uploaded images.
    if full.hostname not in ['127.0.0.1','localhost','pitchup.iptime.org','pitchup.co.kr','www.pitchup.co.kr']: return value
    relative=path.lstrip('/')
    source=SOURCE/relative
    if relative.startswith('file/'):
        relative='media/'+relative[5:];source=UPLOAD/relative[6:]
    if not source.is_file() and '/img/' in path:
        relative='img/'+path.split('/img/',1)[1];source=SOURCE/relative
    if not source.is_file():
        if path not in REPORT['missing_assets']: REPORT['missing_assets'].append(path)
        return value
    if relative in assets: return relative
    assets.add(relative)
    dest=ROOT/relative;dest.parent.mkdir(parents=True,exist_ok=True)
    if source.suffix.lower()=='.css':
        text=source.read_text(encoding='utf-8-sig')
        def replace(m):
            old=m[1].strip(' \"\'');new=asset(old,path)
            if new in assets: new=os.path.relpath(ROOT/new,dest.parent).replace('\\','/')
            return 'url("'+new+'")'
        text=re.sub(r'url\(([^)]+)\)',replace,text)
        text=re.sub(r'/\*# sourceMappingURL=.*?\*/','',text)
        dest.write_text(text,encoding='utf-8')
    else: shutil.copy2(source,dest)
    return relative

def allowed(path):
    return bool(re.fullmatch(r'/(?:fundings/contest/\d+|contest/\d+/(?:funding/\d+|chart)|live/[\w-]+|help/[\w-]+|user/register/[\w-]+)',path))
def register(path):
    if path not in routes: routes[path]='page-'+path.strip('/').replace('/','-')+'.html'

def hydrate(route,doc):
    # User-supplied video for the bootup live page missing its original ID.
    if route == '/live/bootup':
        for frame in doc.select('iframe[src="https://www.youtube.com/embed/"]'):
            frame['src'] = 'https://www.youtube.com/embed/xV-LfUdTGs4'
    chart=re.fullmatch(r'/contest/(\d+)/chart',route)
    if chart and not doc.body.get('data-chart-captured'):
        doc.body['data-chart-captured']='true'
        try:
            data=json.loads(fetch('/contest/'+chart[1]+'/overview.json'))['contest']
            price=data.get('issuePrice') or data.get('issueInfo',{}).get('issuePrice',0)
            doc.select_one('#currentParticipant').string=f'{data.get("participantCount",0):,}'
            doc.select_one('#currentAmount').string=f'{data.get("currentCount",0)*price:,}'
        except Exception as e:REPORT['failed_pages']['chart-data:'+route]=str(e)
    listing=doc.select_one('#moreFunding')
    match=re.fullmatch(r'/fundings/contest/(\d+)',route)
    if listing is None or not match or listing.get('data-captured'): return
    listing['data-captured']='true'
    for number in range(30):
        fragment=soup('/CONTEST/moreFunding?page='+str(number)+'&categoryType=all&orderType=PERCENT&contestId='+match[1]+'&keyword=')
        items=fragment.select('li.funding-item')
        for item in items:
            item['data-company-batch']=str(number);listing.append(item)
        if not items or fragment.select_one('.no-more-item'):break

for route in list(routes):
    if route=='/intro':continue
    try: documents[route]=soup(route)
    except Exception as e: REPORT['failed_pages'][route]=str(e)

newsdoc=documents.get('/changup')
if newsdoc:
    listing=newsdoc.select_one('#changup-card-list')
    if listing:
        for item in listing.select('.changup-card'):item['data-news-batch']='0'
        for number in range(1,1000):
            fragment=soup('/changup/more?page='+str(number))
            items=fragment.select('.changup-card')
            if not items:break
            for item in items:
                item['data-news-batch']=str(number);listing.append(item)
        REPORT['notice_count']=len(listing.select('.changup-card'))
        print('Captured',REPORT['notice_count'],'startup notices',flush=True)

# Materialize AJAX-rendered ended contests into the original list markup.
home=documents['/']; listing=home.select_one('#endContest-list')
if listing:
    for number in range(20):
        fragment=soup('/contest/moreEndContest?page='+str(number))
        items=fragment.body.find_all('li',recursive=False)
        if not items: break
        for item in items:
            item['data-snapshot-batch']=str(number)
            listing.append(item)
        if fragment.select_one('.no-more-item'):break

# Cache every region's real list, retaining the original map and table.
mapdoc=documents.get('/contest/map')
if mapdoc:
    for row in mapdoc.select('ul.regional-table li.data[data-id]'):
        region=row['data-id']
        try:
            fragment=soup('/contest/map/list?residence='+region.upper())
            template=mapdoc.new_tag('template',id='region-'+region)
            for child in list(fragment.body.contents): template.append(child)
            mapdoc.body.append(template)
        except Exception as e:REPORT['failed_pages']['region:'+region]=str(e)

# Follow public display pages only. No private profile, admin, POST or mutation routes.
for depth in range(3):
    pending=set()
    for route,doc in list(documents.items()):
        hydrate(route,doc)
        for a in doc.select('a[href]'):
            path=urlsplit(a['href']).path
            if allowed(path) and path not in documents and path not in REPORT['failed_pages']:
                register(path);pending.add(path)
        for a in doc.select('[onclick]'):
            m=re.search(r'contestLive.popupFunding\((\d+)\)',a['onclick'])
            if m:
                # Public company detail URL is present in the original live page context.
                ids=re.findall(r'/contest/(\d+)/chart',str(doc))
                if ids:
                    path='/contest/'+ids[0]+'/funding/'+m[1]
                    register(path);a['href']=routes[path];a['data-local-link']='true'
                    if path not in documents and path not in REPORT['failed_pages']:pending.add(path)
    if not pending:break
    for route in sorted(pending):
        try:
            doc=soup(route)
            if not doc.title or '오류' in doc.title.get_text():raise ValueError('Source returned an error page')
            documents[route]=doc
        except Exception as e:REPORT['failed_pages'][route]=str(e)
    print('Captured',len(documents),'public pages',flush=True)

for route,doc in documents.items():
    hydrate(route,doc)
    for viewport in doc.select('meta[name=viewport]'):
        viewport['content']='width=device-width, initial-scale=1'
    for comment in doc.find_all(string=lambda s:isinstance(s,Comment)):comment.extract()
    for tag in doc.select('script, base, meta[name=_csrf], meta[name=_csrf_header]'):tag.decompose()
    for tag in doc.select('input[type=hidden]'):tag.decompose()
    for tag in doc.find_all(True):
        for key in list(tag.attrs):
            if key.startswith('on'):
                if key=='onclick':tag['data-original-action']=tag[key]
                del tag[key]
        if tag.name=='form':
            tag.attrs.pop('action',None);tag.attrs.pop('method',None);tag['data-offline-form']='true'
        if tag.get('style'):
            def bg(m):return 'url("'+asset(m[1].strip(' \"\''),route)+'")'
            tag['style']=re.sub(r'url\(([^)]+)\)',bg,tag['style'])
        for key in ['src','poster']:
            if tag.get(key) and tag.name!='iframe':tag[key]=asset(tag[key],route)
        if tag.name=='link' and tag.get('href') and any(r in tag.get('rel',[]) for r in ['stylesheet','icon','image_src']):tag['href']=asset(tag['href'],route)
        if tag.name=='a':
            href=tag.get('href','');path=urlsplit(href).path
            if path in routes and (path in documents or path=='/intro'):tag['href']=routes[path]
            elif href.startswith('/'):
                tag['href']='#';tag['data-unavailable']='true'
            elif href.startswith('javascript:'):tag['href']='#'
            if tag.get_text(strip=True)=='참가 신청하기':
                tag['href']='mailto:whiteport79@gmail.com?subject=%ED%94%BC%EC%B9%98%EC%97%85%20%EB%8D%B0%EB%AA%A8%EB%8D%B0%EC%9D%B4%20%EC%B0%B8%EA%B0%80%20%EC%8B%A0%EC%B2%AD&body=%EC%95%88%EB%85%95%ED%95%98%EC%84%B8%EC%9A%94.%20%ED%94%BC%EC%B9%98%EC%97%85%20%EB%8D%B0%EB%AA%A8%EB%8D%B0%EC%9D%B4%20%EC%B0%B8%EA%B0%80%EB%A5%BC%20%EC%8B%A0%EC%B2%AD%ED%95%A9%EB%8B%88%EB%8B%A4.%0D%0A%0D%0A%ED%9A%8C%EC%82%AC%EB%AA%85%28%ED%8C%80%EB%AA%85%29%3A%20%0D%0A%EB%8B%B4%EB%8B%B9%EC%9E%90%EB%AA%85%3A%20%0D%0A%EC%97%B0%EB%9D%BD%EC%B2%98%3A%20%0D%0A%EC%9D%B4%EB%A9%94%EC%9D%BC%3A%20%0D%0A%EC%84%9C%EB%B9%84%EC%8A%A4%EB%AA%85%3A%20%0D%0A%EC%84%9C%EB%B9%84%EC%8A%A4%20%EC%86%8C%EA%B0%9C%3A%20%0D%0A%EC%B0%B8%EA%B0%80%20%ED%9D%AC%EB%A7%9D%20%EB%8D%B0%EB%AA%A8%EB%8D%B0%EC%9D%B4%3A%20%0D%0A%EB%AC%B8%EC%9D%98%EC%82%AC%ED%95%AD%3A%20%0D%0A%0D%0A%EA%B0%90%EC%82%AC%ED%95%A9%EB%8B%88%EB%8B%A4.'
                tag.attrs.pop('data-original-action',None)
    # Original webFont.js used this same self-contained font file asynchronously.
    font=asset('/font/font_web.css')
    doc.head.append(doc.new_tag('link',rel='stylesheet',href=font))
    doc.head.append(doc.new_tag('link',rel='stylesheet',href='styles.css?v=20261110-header51'))
    theme=asset('/css/design-polish.css')
    if not doc.select_one('link[href="css/design-polish.css"]'):
        doc.head.append(doc.new_tag('link',rel='stylesheet',href=theme))
    # Rebuild navigation even when a cached source contains damaged labels.
    if doc.header:
        for old_nav in doc.select('.pitchup-primary-nav'):
            old_nav.decompose()
        nav=doc.new_tag('nav', attrs={'class':'pitchup-primary-nav', 'aria-label':'주 메뉴'})
        for href, label in [('index.html','홈'),('map.html','데모데이 현황'),('live.html','온라인 설명회'),('changup.html','창업지원 공고')]:
            link=doc.new_tag('a', href=href)
            link.string=label
            if href==routes[route]:link['aria-current']='page'
            nav.append(link)
        menu = doc.header.select_one(".neo-gnb .web-menu-list")
        if menu:
            menu.insert_before(nav)
        else:
            doc.header.append(nav)
    script=doc.new_tag('script',src='script.js?v=20261110-detail-offset');doc.body.append(script)
    dialog=BeautifulSoup('<dialog id="offline-dialog"><h2>안내</h2><p>현재 해당 기능은 일시 중단된 상태입니다. 이용에 양해 부탁드립니다.</p><p>관리자에게 문의해주세요.<br/><a href="mailto:whiteport79@gmail.com" style="color:#267dae;text-decoration:underline;overflow-wrap:anywhere">whiteport79@gmail.com</a></p><button type="button" data-close-offline>확인</button></dialog>','html.parser')
    doc.body.append(dialog)
    write(routes[route],str(doc))
    REPORT['pages'][routes[route]]={'source':route,'title':doc.title.get_text() if doc.title else ''}

REPORT['asset_count']=len(assets)
write('snapshot-report.json',json.dumps(REPORT,ensure_ascii=False,indent=2))
write('snapshot-routes.json',json.dumps(routes,ensure_ascii=False,indent=2))
print('Exported',len(documents),'pages;',len(assets),'assets;',len(REPORT['missing_assets']),'missing assets',flush=True)
