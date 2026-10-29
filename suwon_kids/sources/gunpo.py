"""군포시 '주간행사계획' 게시판. 매주 hwpx 한 장으로 올라오고, 표 한 줄이 하루(날짜·시간·행사명·장소·부서)이며
칸 안의 문단이 행사 하나씩이다. 공무원 교육·회의·훈련도 섞여 있어서 Gemini가 가족이 갈 수 있는 공개 행사만 고른다."""
import html
import io
import json
import re
import zipfile
from datetime import date

from suwon_kids import ai, http, week
from suwon_kids.models import Event

BASE = 'https://www.gunpo.go.kr/www/'
LIST = BASE + 'selectBbsNttList.do?bbsNo=1003417&key=1008929'
POST = re.compile(r'href="\./(selectBbsNttView\.do\?[^"]*nttNo=(\d+)[^"]*)">\s*주간행사계획\((\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})')
FILE = re.compile(r'href="\./(downloadBbsFile\.do\?atchmnflNo=\d+)"[^>]*>.*?\.hwpx', re.S)
DAY = re.compile(r'(\d{1,2})/(\d{1,2})')
MAX_HWPX = 5_000_000
# Gemini가 실패했을 때만 쓰는 거르기 규칙: 공무원·기관 내부 행사, 군포 밖 개최
INTERNAL = re.compile(r'회의|보고회|교육|워크숍|훈련|위원회|간담회|강좌|설명회|협의|면담|기념식|발대식|공무원|보육인|시상식')
OUTSIDE = re.compile(r'^(?:서울|인천|부산|대구|대전|광주|울산|세종|강원|충청|충북|충남|전라|전북|전남|경상|경북|경남|제주)')

PROMPT = """군포시청 주간행사계획에서 아이와 가족이 직접 가서 즐길 수 있는 시민 대상 공개 행사만 고르세요.
공무원 교육·워크숍·회의·보고회·훈련·위원회·간담회, 어른 대상 강좌·설명회, 특정 직군 행사(예: 보육인, 공무원), 군포 밖에서 열리는 행사는 뺍니다.
번호만 JSON 배열로 답하세요. 예: [0, 3]. 없으면 []

{items}"""


def posts(page: str) -> list[tuple[str, date]]:
    """[(상세 경로, 주 시작일)]"""
    return [(html.unescape(path), date(int(y), int(m), int(d))) for path, _no, y, m, d in POST.findall(page)]


def _paras(cell: str) -> list[str]:
    out = [''.join(re.findall(r'<hp:t>([^<]*)</hp:t>', p)).strip() for p in re.findall(r'<hp:p\b.*?</hp:p>', cell, re.S)]
    return [html.unescape(p) for p in out if p]


def rows(hwpx: bytes, start: date) -> list[dict]:
    """표의 날짜 줄마다 행사를 문단 단위로 짝짓는다. 행사명 문단 수가 ○ 수와 다르면(줄바꿈) 시간·장소를 붙이지 않는다."""
    if len(hwpx) > MAX_HWPX:
        raise ValueError('hwpx too large')
    xml = zipfile.ZipFile(io.BytesIO(hwpx)).read('Contents/section0.xml').decode('utf-8', 'replace')
    out = []
    for tr in re.findall(r'<hp:tr\b.*?</hp:tr>', xml, re.S):
        cells = [_paras(c) for c in re.findall(r'<hp:tc\b.*?</hp:tc>', tr, re.S)]
        if len(cells) < 5 or not cells[0] or not DAY.match(cells[0][0]):
            continue
        m = DAY.match(cells[0][0])
        month = int(m.group(1))
        day = date(start.year + (month < start.month), month, int(m.group(2)))  # 12/28~1/3 주의 1월은 다음 해
        times, marks, titles, places = cells[1], cells[2], cells[3], cells[4]
        aligned = len(titles) == len(marks)
        for i, title in enumerate(titles):
            out.append({'date': day, 'title': title,
                        'time': times[i] if aligned and i < len(times) else None,
                        'place': places[i] if aligned and i < len(places) else None})
    return out


def pick(items: list[dict], gen=ai.generate) -> list[dict]:
    if not items:
        return []
    listing = '\n'.join(f"{n}. {it['title']} @ {it['place'] or '?'}" for n, it in enumerate(items))
    try:
        reply = gen(PROMPT.format(items=listing))
    except ai.AIError:  # Gemini가 안 되면 군포 전체를 버리지 말고 낱말 규칙으로 거른다
        return [it for it in items if not INTERNAL.search(it['title']) and not OUTSIDE.search(it['place'] or '')]
    m = re.search(r'\[[-\d,\s]*\]', reply)
    nums = json.loads(m.group(0)) if m else []
    return [items[n] for n in sorted(set(nums)) if 0 <= n < len(items)]


def fetch(today: date | None = None, get=http.get, gen=ai.generate) -> list[Event]:
    rng = week.this_week(today or date.today())
    found = [(path, start) for path, start in posts(get(LIST).decode('utf-8', 'replace'))
             if start <= rng[1] and (start.toordinal() + 6) >= rng[0].toordinal()]
    items = []
    for path, start in found:
        f = FILE.search(get(BASE + path).decode('utf-8', 'replace'))
        if f:
            items += [dict(it, url=BASE + path) for it in rows(get(BASE + html.unescape(f.group(1))), start)
                      if rng[0] <= it['date'] <= rng[1]]
    out = []
    for it in pick(items, gen):
        place = it['place'] or '군포시'
        out.append(Event(
            id=f"gunpo:{it['date']}:{re.sub(r'[^0-9A-Za-z가-힣]', '', it['title'])}", source='gunpo', title=it['title'],
            start=it['date'], end=it['date'], time=it['time'], place=place, address=f'경기도 군포시 {place}',
            url=it['url'], target='누구나', host='군포시'))
    return out
