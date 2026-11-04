"""AK플라자 수원 행사. 쇼핑뉴스 목록(HTML)을 쪽별로 받아 항목을 뽑는다."""
import html
import re
from datetime import date, datetime

from suwon_kids import http
from suwon_kids.models import MallItem

SITE = 'https://www.akplaza.com'
LIST_URL = f'{SITE}/board/news/list?store=02&page='
MALL = 'AK플라자 수원'
MAX_PAGES = 6

_SEQ = re.compile(r"location\.href='view\?store=02&(?:amp;)?seq=(\d+)'")


def _text(s: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()


def _day(s: str) -> date:
    return datetime.strptime(s.strip(), '%Y.%m.%d').date()


def parse_list(html_text: str) -> list[MallItem]:
    out = []
    for blk in html_text.split('<div class="posts-item"')[1:]:
        seq = _SEQ.search(blk[:300])
        name = re.search(r'class="posts-name"[^>]*>(.*?)</a>', blk, re.S)
        start = re.search(r'class="start-date">(.*?)</span>', blk, re.S)
        end = re.search(r'class="end-date">(.*?)</span>', blk, re.S)
        if not (seq and name and start and end):
            continue
        badges = [_text(b) for b in re.findall(r'class="badge-name">(.*?)</span>', blk, re.S)]
        try:
            period = _day(_text(start.group(1))), _day(_text(end.group(1)))
        except ValueError:
            continue
        title = _text(name.group(1))
        if not title:
            continue
        out.append(MallItem(
            id=f'ak:{seq.group(1)}',
            source='ak',
            mall=MALL,
            title=title,
            brand=None,
            start=period[0],
            end=period[1],
            place=badges[-1] if len(badges) > 1 else '',  # 첫 배지는 '수원' 지점 표기, 둘째가 층·매장
            url=f'{SITE}/board/news/view?store=02&seq={seq.group(1)}',
        ))
    return out


def fetch(today: date, get=http.get) -> list[MallItem]:
    items, seen, last_exc, ok = [], set(), None, False
    for page in range(1, MAX_PAGES + 1):
        try:
            parsed = parse_list(get(f'{LIST_URL}{page}').decode('utf-8'))
            ok = True
        except Exception as e:
            last_exc = e
            continue
        if not parsed:  # 빈 쪽이면 멈춘다
            break
        items += [i for i in parsed if i.id not in seen]
        seen.update(i.id for i in parsed)
    if not ok and last_exc:
        raise last_exc
    return items
