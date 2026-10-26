"""동네 배정. config/areas.json 위에서부터 첫 일치, 없으면 주소의 구, 그것도 없으면 '기타'."""
import json
import pathlib
import re

from suwon_kids.models import Event

AREAS = json.loads((pathlib.Path(__file__).parent.parent / 'config/areas.json').read_text(encoding='utf-8'))
GU = re.compile(r'장안구|권선구|팔달구|영통구')


def assign(ev: Event) -> str:
    text = f'{ev.place} {ev.address}'
    for a in AREAS:
        if any(k in text for k in a['keywords']):
            return a['name']
    m = GU.search(text)
    return m.group(0) if m else '기타'
