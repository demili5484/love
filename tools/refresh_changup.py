"""Refresh startup notices from Pitchup without replacing local UI customizations."""
from pathlib import Path
from urllib.request import urlopen
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8082'

def fetch(route):
    with urlopen(BASE + route, timeout=40) as response:
        return BeautifulSoup(response.read().decode('utf-8'), 'html.parser')

def sanitize(fragment):
    for script in fragment.select('script'):
        script.decompose()
    for element in fragment.find_all(True):
        for name in list(element.attrs):
            if name.startswith('on'):
                del element.attrs[name]
    return fragment

home = fetch('/')
news = fetch('/changup?size=2000')
cards = news.select('#changup-card-list .changup-card')
assert cards and home.select('.news-feed .news-item'), 'No notices returned; existing files preserved'
# Spring may cap pageable size; continue if the response is full.
if len(cards) == 2000:
    page = 1
    while True:
        batch = fetch('/changup/more?size=2000&page=' + str(page)).select('.changup-card')
        cards.extend(batch)
        if len(batch) < 2000:
            break
        page += 1

local_home = BeautifulSoup((ROOT/'index.html').read_text(encoding='utf-8'), 'html.parser')
local_news = BeautifulSoup((ROOT/'changup.html').read_text(encoding='utf-8'), 'html.parser')
local_home.select_one('.news-feed').replace_with(sanitize(home.select_one('.news-feed')))
listing = local_news.select_one('#changup-card-list')
listing.clear()
for index, card in enumerate(cards):
    card['data-news-batch'] = str(index // 10)
    listing.append(sanitize(card))

for name, doc in [('index.html', local_home), ('changup.html', local_news)]:
    (ROOT/name).write_text(str(doc), encoding='utf-8')
report_path = ROOT/'snapshot-report.json'
report = json.loads(report_path.read_text(encoding='utf-8'))
report['notice_count'] = len(cards)
report['notices_refreshed_at'] = datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('Updated home notices and', len(cards), 'startup notices; local layout and interactions preserved')
