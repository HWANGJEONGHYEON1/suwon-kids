"""쿠키를 유지하는 간단한 GET."""
import http.cookiejar
import urllib.request

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'


def new_jar():
    return http.cookiejar.CookieJar()


def get(url: str, headers: dict | None = None, jar=None, timeout: int = 30) -> bytes:
    handlers = [urllib.request.HTTPCookieProcessor(jar)] if jar is not None else []
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers={'User-Agent': UA, **(headers or {})})
    with opener.open(req, timeout=timeout) as r:
        return r.read()
