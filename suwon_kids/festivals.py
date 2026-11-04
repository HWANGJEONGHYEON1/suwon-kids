"""경기도 무료 가족 축제(불꽃축제·거리 축제·장터 등) 목록 festivals.json. 인스타 경기도어때 단독 글 소재(2026-11-02 사용자 요청).
events.json 은 수원 근교·이번 주만이라 큰 축제가 빠진다 → 경기도 전체, 시작 30일 전부터 TourAPI 에서 따로 받는다.
축제 공식 사진은 대부분 3유형(변경 금지)이라 쓰지 않고, 장소 사진만 place_photo 규칙대로 찾는다."""
import html
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from suwon_kids import place_photo
from suwon_kids.sources import tourapi

ROOT = Path(__file__).resolve().parents[1]
FEST = re.compile(r'축제|불꽃|페스타|문화제|야행|마켓|장터')
FREE = re.compile(r'(입장료\s*)?무료')  # '무료(일부 프로그램 유료)' 같은 값은 뺀다
LEAD_DAYS = 30
HEADER = re.compile(r'기타\s*내용:?|(주요|메인\s*|부대)?\s*(행사|프로그램)(\s*(및|·)\s*프로그램)?:?')


def _text(raw: str | None) -> str:
    return html.unescape(re.sub(r'<br\s*/?>', '\n', raw or '', flags=re.I)).strip()


def _lines(raw: str | None) -> list[str]:
    lines = (re.sub(r'^[-·•\s]*(\d+[.)]\s*)?', '', ln).strip() for ln in _text(raw).split('\n'))
    return [s for s in lines if s and not HEADER.fullmatch(s)]


def to_festival(item: dict, intro: dict, info: list[dict], photo: dict | None) -> dict:
    by = {i.get('infoname'): i.get('infotext') for i in info}
    return {'id': f"tour:{item['contentid']}", 'source': 'tour', 'title': _text(item['title']),
            'start': tourapi._ymd(item['eventstartdate']).isoformat(), 'end': tourapi._ymd(item['eventenddate']).isoformat(),
            'time': _text(intro.get('playtime')) or None, 'place': _text(intro.get('eventplace')) or item.get('addr1'),
            'address': item.get('addr1'), 'price': _text(intro.get('usetimefestival')), 'age': _text(intro.get('agelimit')) or None,
            'program': _lines(intro.get('program') or by.get('행사내용')), 'summary': _text(by.get('행사소개')) or None,
            'place_photo': photo}


def fetch(today: date, get=tourapi._get, photos: dict | None = None) -> list[dict]:
    photos = {} if photos is None else photos
    found, page = [], 1
    while page <= 5:
        body = get('searchFestival2', eventStartDate=f'{today:%Y%m%d}', lDongRegnCd=tourapi.GYEONGGI, numOfRows=100, pageNo=page)
        found += tourapi.items(body)
        if page * 100 >= int(body.get('totalCount') or 0):
            break
        page += 1
    last = today + timedelta(days=LEAD_DAYS)
    out = []
    for it in found:
        if not it.get('addr1', '').startswith('경기') or not FEST.search(it['title']) or tourapi._ymd(it['eventstartdate']) > last:
            continue
        intro = tourapi.items(get('detailIntro2', contentId=it['contentid'], contentTypeId=15))[0]
        if not FREE.fullmatch(_text(intro.get('usetimefestival'))):
            continue
        info = tourapi.items(get('detailInfo2', contentId=it['contentid'], contentTypeId=15))
        out.append(to_festival(it, intro, info, place_photo.lookup(_text(intro.get('eventplace')), photos, get)))
    return sorted(out, key=lambda f: f['start'])


def write(today: date, path: Path = ROOT / 'festivals.json') -> int:
    fs = fetch(today)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps({'updated': today.isoformat(), 'festivals': fs}, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(path)
    return len(fs)


if __name__ == '__main__':
    print(write(date.today()), file=sys.stdout)
