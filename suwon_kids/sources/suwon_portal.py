"""수원특례시 행사축제포털 (https://www.suwon.go.kr/culture/index.do)."""
import html
import json
import re
from datetime import date

from suwon_kids import http
from suwon_kids.models import Event

BASE = 'https://www.suwon.go.kr/culture/'


def parse_date(s: str | None) -> date | None:
    m = re.match(r'(\d{4})-?(\d{2})-?(\d{2})', s or '')
    return date(*map(int, m.groups())) if m else None


def fetch_list(max_pages: int = 10) -> list[dict]:
    rows, page, total = [], 1, 1
    while page <= min(total, max_pages):
        d = json.loads(http.get(f'{BASE}smartSearchListJson.do?q_rowPerPage=200&q_currPage={page}'))
        rows += d.get('dataList') or []
        total = d.get('totalPage') or 1
        page += 1
    return rows


def _cell(page: str, label: str) -> str:
    m = re.search(rf'<th[^>]*>\s*{label}\s*</th>\s*<td[^>]*>(.*?)</td>', page, re.S)
    if not m:
        return ''
    text = re.sub(r'<[^>]+>', ' ', re.sub(r'<br\s*/?>', '\n', m.group(1), flags=re.I))
    return re.sub(r'[ \t\xa0]+', ' ', html.unescape(text)).strip()


def parse_detail(page: str) -> dict:
    body = '\n'.join(x for x in (_cell(page, '행사개요'), _cell(page, '행사내용')) if x)
    return {'host': _cell(page, '주최기관'), 'body': body}


def fetch_detail(seq: str) -> dict:
    return parse_detail(http.get(f'{BASE}ingCultureView.do?ctrSeqNo={seq}').decode('utf-8', 'replace'))


def to_events(rows: list[dict]) -> list[Event]:
    """날짜를 못 읽는 행은 건너뛴다."""
    return [to_event(r) for r in rows if parse_date(r.get('startDt'))]


def to_event(row: dict) -> Event:
    start = parse_date(row.get('startDt'))
    end = parse_date(row.get('endDt')) or start
    times = [t for t in (row.get('startTime'), row.get('endTime')) if t]
    return Event(
        id=f"suwon:{row['ctrSeqNo']}",
        source='suwon',
        title=(row.get('cultureNm') or '').strip(),
        start=start,
        end=end,
        time='~'.join(times) or None,
        place=row.get('ctrLocation') or '',
        address=' '.join(x for x in (row.get('baseAddr'), row.get('detailAddr')) if x),
        url=f"{BASE}ingCultureView.do?ctrSeqNo={row['ctrSeqNo']}",
        target=row.get('ctrTarget') or '',
    )
