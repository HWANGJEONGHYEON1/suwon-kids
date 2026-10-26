"""AI 한 줄 요약과 포스터 읽기. 원문에 없는 낱말·시각이 섞이면 버린다 (지어낸 출연자 방지)."""
import json
import re

from suwon_kids import ai
from suwon_kids.models import Event

MAX_LEN = 40
JOSA = re.compile(r'(은|는|이|가|을|를|의|에|와|과|도|로|으로|에서)$')
# 원문에 없어도 되는 흔한 낱말
GENERIC = {'무료', '공연', '체험', '가족', '축제', '전시', '행사', '아이', '어린이', '함께', '야간', '주말', '매주',
           '프로그램', '운영', '참여', '가능', '개막', '열림', '진행'}

PROMPT = """아래 행사 안내문을 읽고, 아이 키우는 부모가 눈여겨볼 점을 한국어 한 줄(40자 이내)로 쓰세요.
안내문에 있는 낱말만 쓰고, 안내문에 없는 이름·시간·장소는 절대 쓰지 마세요.
"눈여겨보기", "추천" 같은 말을 덧붙이지 말고 명사로 끝내세요 (예: "가수 ○○ 무료 공연, 체험부스"). 한 줄만 출력하세요.

행사명: {title}
안내문:
{body}"""

POSTER_PROMPT = """이 포스터에 적힌 프로그램을 JSON으로만 출력하세요. 형식:
{"programs": [{"name": "", "date": "", "time": "", "age": ""}]}
포스터에 없는 값은 빈 문자열로 두세요."""
# 두 번째 읽기는 다른 지시로 따로 읽혀, 같은 착각이 두 번 나오지 않게 한다
POSTER_PROMPT_CHECK = """포스터를 처음부터 다시 꼼꼼히 읽고, 글자 그대로 옮겨 적으세요. 추측해서 채우지 마세요.
""" + POSTER_PROMPT


def verified(summary: str, source_text: str) -> bool:
    # 숫자 덩어리(시각·날짜·금액)와 라틴 낱말은 원문에 그대로 있어야 한다
    for t in re.findall(r'\d[\d,.:]*|[A-Za-z][A-Za-z0-9&\'-]*', summary):
        if t.rstrip('.,') not in source_text:
            return False
    for word in re.findall(r'[가-힣]{2,}', summary):
        stem = JOSA.sub('', word) if len(word) > 2 else word
        if stem not in source_text and stem not in GENERIC:
            return False
    return True


def one_line(ev: Event, body: str, gen=ai.generate) -> str | None:
    try:
        s = gen(PROMPT.format(title=ev.title, body=body[:3000])).strip().splitlines()[0].strip(' "\'')
    except Exception:  # AI·네트워크 오류면 요약 없이 제목만
        return None
    if not s or s == ev.title or len(s) > MAX_LEN or not verified(s, f'{ev.title}\n{body}'):
        return None
    return s


def _json(text: str) -> dict | None:
    m = re.search(r'\{.*\}', text, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


def read_poster(image_url: str, cache: dict, gen=ai.generate) -> dict | None:
    if image_url in cache:
        return cache[image_url]
    try:
        a, b = _json(gen(POSTER_PROMPT, image_url)), _json(gen(POSTER_PROMPT_CHECK, image_url))
    except Exception:  # AI 오류든 이미지 받기 오류든 포스터 요약만 빠진다
        return None
    if a is None or a != b:
        return None
    cache[image_url] = a
    return a
