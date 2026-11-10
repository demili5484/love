"""Check exported pages, local dependencies, original styles, and HTTP responses."""
from pathlib import Path
from urllib.parse import urlsplit, unquote, quote
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
import json, re, hashlib

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('D:/dev/pitchup/src/main/webapp')
report=json.loads((ROOT/'snapshot-report.json').read_text(encoding='utf-8'))
errors=[]; references=set(); scripts=set()
def check_url(value, parent=ROOT):
    if not value or value.startswith(('data:','#','http:','https:','//','mailto:','tel:')):return
    path=unquote(urlsplit(value).path)
    dest=(ROOT/path.lstrip('/')) if path.startswith('/') else parent/path
    if not dest.is_file():errors.append('Missing file: '+str(dest))
    else:references.add(dest.resolve().relative_to(ROOT.resolve()).as_posix())

for name in report['pages']:
    page=(ROOT/name).read_text(encoding='utf-8')
    doc=BeautifulSoup(page,'html5lib')
    assert doc.title and doc.body,name
    for el in doc.find_all(True):
        assert not any(key.startswith('on') for key in el.attrs),name
        if el.name=='script':
            assert urlsplit(el.get('src','')).path=='script.js' and not el.get_text(strip=True),name
        if el.name=='form':assert not el.get('action') and el.get('data-offline-form')=='true',name
        for key in ['src','poster']:
            if el.get(key):check_url(el[key])
        if el.name=='a':check_url(el.get('href'))
        if el.name=='link' and any(x in el.get('rel',[]) for x in ['stylesheet','icon','image_src']):check_url(el.get('href'))
        if el.get('style'):
            for value in re.findall(r'url\([\"\']?([^\)\"\']+)',el['style']):check_url(value)

css_checked=0
for path in ROOT.rglob('*.css'):
    if '.snapshot-cache' in path.parts:continue
    text=path.read_text(encoding='utf-8-sig')
    for value in re.findall(r'url\([\"\']?([^\)\"\']+)',text):check_url(value,path.parent)
    original=SOURCE/path.relative_to(ROOT)
    if original.is_file():
        def normalized(value):
            value=re.sub(r'url\([^)]*\)','url(ASSET)',value)
            value=re.sub(r'/\*# sourceMappingURL=.*?\*/','',value)
            return value.strip()
        assert normalized(text)==normalized(original.read_text(encoding='utf-8-sig')),str(path)
        css_checked+=1

home=BeautifulSoup((ROOT/'index.html').read_text(encoding='utf-8'),'html5lib')
news=BeautifulSoup((ROOT/'changup.html').read_text(encoding='utf-8'),'html5lib')
assert len(home.select('#endContest-list>li'))==13
assert len(news.select('.changup-card'))==report['notice_count']
assert not re.search(r'fetch\(|XMLHttpRequest|WebSocket|\$\.ajax|localStorage|sessionStorage',(ROOT/'script.js').read_text(encoding='utf-8'))
assert not errors,'\n'.join(errors[:30])

def request(path):
    with urlopen('http://127.0.0.1:8083/'+quote(path,safe='/'),timeout=20) as response:
        assert response.status==200,path
    return path
paths=set(report['pages'])|references
with ThreadPoolExecutor(max_workers=6) as executor:list(executor.map(request,paths))
with urlopen('http://127.0.0.1:8083/contest/map',timeout=10) as response:assert response.status==200
result={'pages':len(report['pages']),'http_checks':len(paths)+1,'original_stylesheets_matched':css_checked,
        'ended_contests':13,'startup_notices':report['notice_count'],'missing_references':0,
        'database_requests_in_runtime':0,'browser_visual_comparison':'not performed by this script'}
(ROOT/'verification-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
