"""동네 배정. config/areas.json 위에서부터 첫 일치, 없으면 주소의 수원 구, 그다음 근교 시, 그것도 없으면 '기타'.
"near": true 인 동네(동탄)는 탭 순서에서 수원 구 뒤, 근교 시 앞에 온다."""
import json
import pathlib
import re

from suwon_kids.models import Event

AREAS = json.loads((pathlib.Path(__file__).parent.parent / 'config/areas.json').read_text(encoding='utf-8'))
GU_NAMES = ['장안구', '권선구', '팔달구', '영통구']
GU = re.compile('|'.join(GU_NAMES))
NEAR_CITIES = ['용인', '화성', '안양', '의왕', '오산', '군포']
CITY = re.compile(f"({'|'.join(NEAR_CITIES)})시")
ORDER = ([a['name'] for a in AREAS if not a.get('near')] + GU_NAMES
         + [a['name'] for a in AREAS if a.get('near')] + NEAR_CITIES + ['기타'])


def assign(ev: Event) -> str:
    text = f'{ev.place} {ev.address}'
    for a in AREAS:
        if any(k in text for k in a['keywords']):
            return a['name']
    m = GU.search(text)
    if m:
        return m.group(0)
    m = CITY.search(ev.address)
    return m.group(1) if m else '기타'
