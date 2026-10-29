"""쿠키를 유지하는 간단한 GET."""
import http.cookiejar
import ssl
import urllib.request

# 오래된 TLS 1.2 암호만 쓰는 관공서 서버용(안양시청). 인증서 검사는 그대로, 암호 보안 수준만 1로 낮춘다
LEGACY_TLS = ssl.create_default_context()
LEGACY_TLS.set_ciphers('DEFAULT:@SECLEVEL=1')

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'


def new_jar():
    return http.cookiejar.CookieJar()


def get(url: str, headers: dict | None = None, jar=None, timeout: int = 30, data: bytes | None = None,
        legacy_tls: bool = False) -> bytes:
    handlers = [urllib.request.HTTPCookieProcessor(jar)] if jar is not None else []
    if legacy_tls:
        handlers.append(urllib.request.HTTPSHandler(context=LEGACY_TLS))
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, data=data, headers={'User-Agent': UA, **(headers or {})})
    with opener.open(req, timeout=timeout) as r:
        return r.read()


def post(url: str, data: bytes, headers: dict | None = None, timeout: int = 30) -> bytes:
    return get(url, {'Content-Type': 'application/x-www-form-urlencoded', **(headers or {})}, timeout=timeout, data=data)
