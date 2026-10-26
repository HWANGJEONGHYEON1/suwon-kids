"""수원특례시 행사축제포털 (https://www.suwon.go.kr/culture/index.do)."""
import json
import re
from datetime import date

from suwon_kids import http
from suwon_kids.models import Event

BASE = 'https://www.suwon.go.kr/culture/'


def parse_date(s: str | None) -> date | None:
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', s or '')
    return date(*map(int, m.groups())) if m else None


def fetch_list(max_pages: int = 10) -> list[dict]:
    rows, page, total = [], 1, 1
    while page <= min(total, max_pages):
        d = json.loads(http.get(f'{BASE}smartSearchListJson.do?q_rowPerPage=200&q_currPage={page}'))
        rows += d.get('dataList') or []
        total = d.get('totalPage') or 1
        page += 1
    return rows


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
