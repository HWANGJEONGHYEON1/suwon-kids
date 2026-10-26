"""Gemini REST 호출. 키·모델은 저장소 루트 .env (GEMINI_API_KEY, GEMINI_MODEL)."""
import base64
import json
import pathlib
import re
import urllib.error
import urllib.request

from suwon_kids import http

ENV_PATH = pathlib.Path(__file__).parent.parent / '.env'


class AIError(Exception):
    pass


def _env() -> dict:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding='utf-8').splitlines():
            m = re.match(r'\s*([A-Z_]+)=(.*)', line)
            if m:
                env[m.group(1)] = m.group(2).strip().strip('"\'')
    return env


def generate(prompt: str, image_url: str | None = None) -> str:
    env = _env()
    key, model = env.get('GEMINI_API_KEY'), env.get('GEMINI_MODEL', 'gemini-flash-latest')
    if not key:
        raise AIError('GEMINI_API_KEY 없음')
    parts = [{'text': prompt}]
    if image_url:
        mime = 'image/png' if image_url.lower().endswith('.png') else 'image/jpeg'
        try:
            img = http.get(image_url)
        except OSError as e:  # urllib 오류는 모두 OSError
            raise AIError(f'이미지 받기 실패: {type(e).__name__}') from None
        parts.append({'inlineData': {'mimeType': mime, 'data': base64.b64encode(img).decode()}})
    req = urllib.request.Request(
        f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}',
        json.dumps({'contents': [{'parts': parts}], 'generationConfig': {'temperature': 0}}).encode(),
        {'Content-Type': 'application/json'})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=120))
        return ''.join(p.get('text', '') for p in r['candidates'][0]['content']['parts']).strip()
    except urllib.error.HTTPError as e:
        raise AIError(f'HTTP {e.code}') from None
    except (KeyError, IndexError, urllib.error.URLError, TimeoutError) as e:
        raise AIError(type(e).__name__) from None
