"""행사 장소 사진: 한국관광공사 TourAPI 에서 경기도 안의, 장소 이름이 '정확히 같은' 관광지 사진만, 공공누리 제1유형(상업 이용·변경 가능)만.
인스타 릴스 카드 배경에 쓰려고 events.json 에 넣는다. 3유형(변경 금지)·이름이 다른 결과는 쓰지 않는다."""
import re

from suwon_kids.sources import tourapi

CREDIT = '한국관광공사 / 공공누리 제1유형'


def candidates(place: str) -> list[str]:
    """'경기도어린이박물관 교육실 1 (용인)' → ['경기도어린이박물관 교육실 1', '경기도어린이박물관 교육실', '경기도어린이박물관']"""
    words = re.sub(r'\s*[(\[].*?[)\]]', '', (place or '').split(',')[0]).split()
    return [' '.join(words[:n]) for n in range(len(words), 0, -1) if len(' '.join(words[:n]).replace(' ', '')) >= 4]  # '용인시'처럼 짧은 이름은 엉뚱한 곳이 걸린다


def lookup(place: str, cache: dict, get=tourapi._get) -> dict | None:
    """{'url', 'credit', 'title'} 또는 None. 찾은 것·못 찾은 것 모두 cache 에 둔다(장소당 한 번만 묻는다)."""
    for name in candidates(place):
        if name in cache:
            if cache[name]:
                return cache[name]
            continue
        found = None
        for it in tourapi.items(get('searchKeyword2', keyword=name, lDongRegnCd=tourapi.GYEONGGI, numOfRows=10, pageNo=1, arrange='A')):
            if (it.get('title') or '').strip() == name and it.get('cpyrhtDivCd') == 'Type1' and it.get('firstimage'):
                found = {'url': it['firstimage'], 'credit': CREDIT, 'title': name}
                break
        cache[name] = found
        if found:
            return found
    return None
