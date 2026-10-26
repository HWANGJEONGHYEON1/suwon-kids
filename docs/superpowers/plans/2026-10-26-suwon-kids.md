# 수원 아이랑 이번 주 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 수원시 행사 포털·스타필드 수원 행사를 매일 모아 "이번 주 수원, 애랑 갈 만한 곳" 정적 페이지를 GitHub Pages로 내고, 매주 목요일 네이버 블로그(deert303) 글 초안을 텔레그램 승인 후 발행한다.

**Architecture:** `~/Documents/suwon-kids`는 수집 → 거르기 → 동네 묶기 → AI 한 줄 요약 → `site/events.json`·`site/index.html` 생성 → git push(Pages)까지 하는 파이썬 파이프라인이다. `~/Documents/ai-hub/content-factory/automation/suwon_kids_post.py`가 그 `events.json`을 읽어 주간 글을 만들고 기존 텔레그램 버튼 봇(`fi_bot.py`)·`naver_fast.publish()`로 발행한다. 두 저장소는 파일(`events.json`)로만 연결되고 서로 import하지 않는다.

**Tech Stack:** Python 3.15 표준 라이브러리만 (`urllib`, `http.cookiejar`, `json`, `html`, `unittest`). Gemini REST(무료 키). launchd. GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-10-26-suwon-kids-events-design.md`

## Global Constraints

- 외부 패키지 설치 없음. 테스트는 `python3 -m unittest` (pytest 미설치)
- 공개 저장소다. 키·토큰·쿠키를 커밋하지 않는다. `GEMINI_API_KEY`·`GEMINI_MODEL`은 `.gitignore`된 `suwon-kids/.env`
- `suwon-kids`는 `ai-hub` 모듈을 import하지 않는다. `ai-hub` 쪽도 `suwon-kids`를 import하지 않고 `events.json`만 읽는다
- 이번 주 = 실행일(Asia/Seoul) ~ 그 주 일요일. 하루라도 걸치는 행사만
- 기간이 30일을 넘는 행사는 "상시" 묶음 (설계의 "몇 달짜리"를 30일로 정함)
- 제목 제외어: `모집`, `수강생`, `경로`, `채용`, `참가자`
- 주최 예외: 주최기관에 `수원` 또는 `경기` 포함 AND 제목에 `축제|페스티벌|페스타|문화제|야행|마켓|장터` 포함 → 대상·제목 필터 무시, 기간 필터는 적용
- AI 요약의 출연자·시간은 원문에 글자 그대로 있어야 한다. 없으면 요약을 버리고 제목만
- 동네: `스타필드 수원`(화서역 주변·대유평공원 포함), `행궁동`(화성행궁·통닭거리·화서문·장안문 포함), `광교`(광교호수공원 포함), 그 밖은 `장안구`·`권선구`·`팔달구`·`영통구`
- 페이지 제목 문구: `이번 주 수원, 애랑 갈 만한 곳`. 태그(유모차·주차·붐빔) 없음
- 블로그: `blog='blog.naver.com/deert303'`, `account='u1'`. 수익화 링크 없음. 텔레그램 주제 `blog`. 승인 마감 금요일 12:00, 넘기면 그 주 건너뜀
- 앱 주소: `https://hwangjeonghyeon1.github.io/suwon-kids/`
- launchd는 python을 직접 실행한다 (`/bin/sh`로 감싸지 않는다)

## Review Focus

1. 수집 실패(포털 오류, 스타필드 쿠키 없이 `data: []`) → 이전 `events.json`을 빈 목록으로 덮어쓰지 않고 그대로 둔 채 실패 기록 (Task 7 테스트)
2. 날짜 형식 `2026-10-09(금)`, `endDt` 없음, 스타필드 `evtStrtDtTxt`의 연도 넘김(`12.26(토), 1.2(토)`) → 올바른 날짜로 해석 (Task 1·2 테스트)
3. 일요일 실행 → 이번 주는 그날 하루, 월요일 실행 → 월~일 (Task 3 테스트)
4. 제목의 `<br>`, `<고문서로 만나는…>` 같은 꺾쇠 → 페이지에서 글자로 보이고 HTML로 해석되지 않음 (Task 7 테스트)
5. AI가 원문에 없는 출연자 이름을 요약에 넣음 → 요약 버림 (Task 5 테스트)

---

## 파일 구조 (`~/Documents/suwon-kids`)

```
suwon_kids/
  models.py          Event 데이터 형식
  http.py            쿠키 유지 GET (urllib + cookiejar)
  sources/suwon_portal.py   시 포털 목록·상세
  sources/starfield.py      스타필드 이벤트
  sources/gyeonggi.py       경기아트센터·경기문화재단 (Task 8, 선택)
  week.py            이번 주 범위, 기간 판정
  filters.py         대상·제목·주최 예외
  areas.py           동네 배정
  ai.py              Gemini 호출
  summarize.py       한 줄 요약 + 원문 대조, 포스터 읽기
  dedupe.py          중복 합치기
  render.py          index.html
  build.py           전체 실행 진입점
config/areas.json    동네 규칙
site/                배포물 (index.html, events.json)
state/posters.json   읽은 포스터 캐시 (커밋함, 키 없음)
tests/               unittest + fixtures/
scheduler/com.suwonkids.build.plist
.env (gitignore)
```

---

### Task 1: 뼈대 + 시 포털 목록 수집

**Files:**
- Create: `suwon_kids/__init__.py`, `suwon_kids/models.py`, `suwon_kids/http.py`, `suwon_kids/sources/__init__.py`, `suwon_kids/sources/suwon_portal.py`, `.gitignore`(`.env`, `__pycache__/`)
- Test: `tests/test_suwon_portal.py`, `tests/fixtures/portal_list.json`

**Interfaces:**
- Produces:
  - `@dataclass Event(id: str, source: str, title: str, start: date, end: date, time: str|None, place: str, address: str, url: str, target: str, host: str|None = None, summary: str|None = None, area: str|None = None, image: str|None = None)`
  - `http.get(url: str, headers: dict|None = None, jar=None) -> bytes`, `http.new_jar()`
  - `suwon_portal.fetch_list(max_pages: int = 10) -> list[dict]` (원본 행)
  - `suwon_portal.to_event(row: dict) -> Event` (`id='suwon:'+ctrSeqNo`, `url='https://www.suwon.go.kr/culture/ingCultureView.do?ctrSeqNo=N'`)
  - `suwon_portal.parse_date(s: str|None) -> date|None`

- [ ] **Step 1:** 실제 응답에서 3행을 뽑아 fixture 저장: `curl -s "https://www.suwon.go.kr/culture/smartSearchListJson.do?q_rowPerPage=3&q_currPage=1" > tests/fixtures/portal_list.json`. 이 중 1행의 `endDt`를 `null`로 바꾼다
- [ ] **Step 2:** 테스트 작성
  - `test_parse_date`: `parse_date('2026-10-09(금)') == date(2026,10,9)`, `parse_date(None) is None`, `parse_date('') is None`
  - `test_to_event_fields`: fixture 첫 행 → `id` 시작이 `'suwon:'`, `title == row['cultureNm'].strip()`, `place == row['ctrLocation']`
  - `test_end_missing_uses_start`: `endDt` 없는 행 → `ev.end == ev.start`
- [ ] **Step 3:** `python3 -m unittest tests.test_suwon_portal -v` → 실패 확인
- [ ] **Step 4:** 구현. `fetch_list`는 `q_currPage` 1부터 `totalPage` 또는 `max_pages`까지
- [ ] **Step 5:** 테스트 통과 확인, 그리고 실데이터 확인: `python3 -c "from suwon_kids.sources import suwon_portal as p; print(len(p.fetch_list(1)))"` → `200`
- [ ] **Step 6:** 커밋 `feat: 시 포털 목록 수집`

### Task 2: 스타필드 이벤트 수집

**Files:**
- Create: `suwon_kids/sources/starfield.py`
- Test: `tests/test_starfield.py`, `tests/fixtures/starfield_list.json`

**Interfaces:**
- Consumes: `http.get`, `http.new_jar`, `Event`
- Produces:
  - `starfield.fetch() -> list[dict]` — 먼저 `https://www.starfield.co.kr/suwon/eventBenefit/events`를 같은 jar로 GET, 그다음 `https://www.starfield.co.kr/api/suwon/event/eventList.do?evt_gbn=event&lang=ko&pageIndex=1`을 `Referer`(이벤트 페이지)·`X-Requested-With: XMLHttpRequest`로 GET. `data`가 비면 `RuntimeError('starfield empty')`
  - `starfield.parse_dates(txt: str, posted: date) -> list[date]` — `'11.7(토), 11.14(토)'` 형식. 연도는 `posted`의 연도, 월이 `posted` 월보다 3 이상 작으면 다음 해
  - `starfield.to_events(row: dict) -> list[Event]` — 날짜 하나당 Event 하나 (`id='starfield:'+evt_seq+':'+YYYYMMDD`, `place='스타필드 수원'`, `title`은 `<br>` 제거·공백 정리, `image='https://www.starfield.co.kr'+img_uri`, `url='https://www.starfield.co.kr/suwon/eventBenefit/events'`, `target='누구나'`). `evtStrtDtTxt`가 날짜로 안 읽히면 `evt_post_strt_dt`~`evt_post_end_dt` 한 건

- [ ] **Step 1:** 이 대화에서 확인한 실제 응답 3건(11월 키즈프로그램, 별마당 10월 강연&공연 `<br>` 포함, 10월 키즈프로그램)으로 fixture 작성
- [ ] **Step 2:** 테스트
  - `test_parse_dates_basic`: `parse_dates('11.7(토), 11.14(토)', date(2026,10,26)) == [date(2026,11,7), date(2026,11,14)]`
  - `test_parse_dates_year_wrap`: `parse_dates('12.26(토), 1.2(토)', date(2026,12,1)) == [date(2026,12,26), date(2027,1,2)]`
  - `test_title_strips_br`: 별마당 행 → 제목에 `<br>` 없음, `'별마당 도서관 10월 강연&공연 안내'`
  - `test_one_event_per_date`: 11월 키즈 행 → 4건
- [ ] **Step 3:** 실패 확인 → 구현 → 통과 확인
- [ ] **Step 4:** 실데이터: `python3 -c "from suwon_kids.sources import starfield as s; print(len(s.fetch()))"` → 1 이상
- [ ] **Step 5:** 커밋 `feat: 스타필드 이벤트 수집`

### Task 3: 이번 주 범위와 거르기 (주최 예외 포함)

**Files:**
- Create: `suwon_kids/week.py`, `suwon_kids/filters.py`; Modify: `suwon_kids/sources/suwon_portal.py` (상세)
- Test: `tests/test_week.py`, `tests/test_filters.py`, `tests/fixtures/portal_detail.html`

**Interfaces:**
- Produces:
  - `week.this_week(today: date) -> tuple[date, date]` (오늘, 그 주 일요일)
  - `week.overlaps(ev: Event, rng) -> bool`, `week.is_long(ev: Event) -> bool` (기간 > 30일)
  - `suwon_portal.fetch_detail(seq: str) -> dict` → `{'host': str, 'body': str}` (상세 페이지의 `주최기관`, `행사개요`+`행사내용` 글자)
  - `suwon_portal.parse_detail(html: str) -> dict` (같은 형식, 네트워크 없이)
  - `filters.is_host_exception(title: str, host: str|None) -> bool`
  - `filters.keep(ev: Event) -> bool` (Global Constraints의 대상·제외어·예외 규칙. `ev.host`를 쓴다)

- [ ] **Step 1:** `curl -s "https://www.suwon.go.kr/culture/ingCultureView.do?ctrSeqNo=2155" > tests/fixtures/portal_detail.html` (통닭거리 축제)
- [ ] **Step 2:** 테스트
  - `test_this_week_monday`: `this_week(date(2026,10,26)) == (date(2026,10,26), date(2026,11,1))`
  - `test_this_week_sunday`: `this_week(date(2026,11,1)) == (date(2026,11,1), date(2026,11,1))`
  - `test_overlaps_edge`: 끝이 오늘인 행사 True, 시작이 다음 주 월요일인 행사 False
  - `test_is_long`: 31일짜리 True, 30일짜리 False
  - `test_parse_detail_host`: fixture → `host`에 `'수원'` 포함, `body` 비어 있지 않음
  - `test_keep_adult_only_dropped`: `target='성인'` → False
  - `test_keep_recruit_dropped`: 제목 `'… 참가자 모집'`, `target='누구나'` → False
  - `test_host_exception`: 제목 `'2026 수원 통닭거리 축제'`, `target='성인'`, `host='수원특례시'` → `keep` True
  - `test_host_exception_needs_festival_word`: 제목 `'시민 강좌'`, `host='수원특례시'`, `target='성인'` → False
- [ ] **Step 3:** 실패 확인 → 구현 → 통과 확인
- [ ] **Step 4:** 커밋 `feat: 이번 주 범위와 거르기`

### Task 4: 동네 배정과 중복 합치기

**Files:**
- Create: `config/areas.json`, `suwon_kids/areas.py`, `suwon_kids/dedupe.py`
- Test: `tests/test_areas.py`, `tests/test_dedupe.py`

**Interfaces:**
- Produces:
  - `config/areas.json`: `[{"name": "스타필드 수원", "keywords": ["스타필드", "화서역", "대유평", "111CM"]}, {"name": "행궁동", "keywords": ["행궁", "통닭거리", "화서문", "장안문", "화홍", "공방거리", "팔달문"]}, {"name": "광교", "keywords": ["광교"]}]` — 위에서부터 첫 일치. 없으면 주소의 `장안구|권선구|팔달구|영통구`, 그것도 없으면 `'기타'`
  - `areas.assign(ev: Event) -> str` (`place`+`address`에서 찾음)
  - `dedupe.merge(events: list[Event]) -> list[Event]` — 제목에서 공백·연도(`20\d\d`)·괄호를 뺀 글자가 같고 기간이 겹치면 하나로. 남기는 쪽은 `source=='suwon'` 우선

- [ ] **Step 1:** 테스트
  - `test_area_starfield`: `place='대유평공원 및 111CM 야외 일원'` → `'스타필드 수원'`
  - `test_area_haenggung`: `place='화성행궁광장'` → `'행궁동'`
  - `test_area_gwanggyo`: `place='광교호수공원'` → `'광교'`
  - `test_area_gu_fallback`: `address='경기도 수원시 권선구 당수로 130'` → `'권선구'`
  - `test_dedupe_same_title_overlap`: 같은 제목·겹치는 기간 2건(`suwon`, `starfield`) → 1건, `source=='suwon'`
  - `test_dedupe_keeps_different_dates`: 같은 제목·안 겹치는 기간 → 2건
- [ ] **Step 2:** 실패 확인 → 구현 → 통과 확인
- [ ] **Step 3:** 커밋 `feat: 동네 배정과 중복 합치기`

### Task 5: AI 한 줄 요약과 원문 대조, 포스터 읽기

**Files:**
- Create: `suwon_kids/ai.py`, `suwon_kids/summarize.py`, `state/posters.json`(`{}`)
- Test: `tests/test_summarize.py`

**Interfaces:**
- Produces:
  - `ai.generate(prompt: str, image_url: str|None = None) -> str` — `.env`의 `GEMINI_API_KEY`·`GEMINI_MODEL`로 `generateContent`. 이미지는 내려받아 `inlineData`로. 실패 시 `AIError`
  - `summarize.verified(summary: str, source_text: str) -> bool` — 요약 속 사람 이름 후보(2~4글자 한글 낱말 중 `·`나 `,`로 나열된 것)와 시각(`\d{1,2}:\d{2}`, `\d{1,2}시`)이 모두 `source_text`에 그대로 있으면 True
  - `summarize.one_line(ev: Event, body: str, gen=ai.generate) -> str|None` — 40자 이내 한 줄. `verified` 실패면 None
  - `summarize.read_poster(image_url: str, cache: dict, gen=ai.generate) -> dict|None` — `{'programs': [{'name', 'date', 'time', 'age'}]}`. 같은 이미지를 두 번 읽어 결과가 같을 때만 반환. 캐시 키는 `image_url`, 캐시에 있으면 AI 호출 안 함

- [ ] **Step 1:** `.env`에 키를 둔다 (`~/Documents/ai-hub/shared/config/.env`의 `GEMINI_API_KEY` 값을 복사. 값은 대화에 출력하지 않는다). `GEMINI_MODEL`은 `curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$KEY"` 결과에서 무료 등급 flash 계열(텍스트+이미지 입력) 이름을 골라 적는다
- [ ] **Step 2:** 테스트 (`gen`은 가짜 함수 주입, 네트워크 없음)
  - `test_verified_ok`: 요약 `'임창정·손승연 무료 공연'`, 원문에 두 이름 있음 → True
  - `test_verified_invented_name`: 요약 `'아이유 무료 공연'`, 원문에 없음 → False
  - `test_verified_time`: 요약 `'18:30 개막'`, 원문에 `18:30` 없음 → False
  - `test_one_line_rejects_unverified`: 가짜 gen이 원문에 없는 이름을 내면 → None
  - `test_poster_needs_two_matching_reads`: 가짜 gen이 두 번 다른 답 → None; 같은 답 → dict
  - `test_poster_cache_hit`: 캐시에 있으면 gen 호출 0회
- [ ] **Step 3:** 실패 확인 → 구현 → 통과 확인
- [ ] **Step 4:** 실호출 1회: 통닭거리 축제 상세 본문으로 `one_line` 실행해 결과 한 줄 확인
- [ ] **Step 5:** 커밋 `feat: AI 한 줄 요약과 원문 대조` (`.env`가 커밋에 없는지 `git status`로 확인)

### Task 6: 페이지 렌더

**Files:**
- Create: `suwon_kids/render.py`
- Test: `tests/test_render.py`

**Interfaces:**
- Produces: `render.page(events: list[Event], long_events: list[Event], updated: datetime) -> str`
  - 시안 `area-v2.html` 구조: 제목 `이번 주 수원, 애랑 갈 만한 곳`, 동네 섹션 순서 `스타필드 수원`, `행궁동`, `광교`, 그다음 구·`기타`. 행사 없는 동네는 생략
  - 카드: 제목, 날짜(`10.31(토)` 형식, 여러 날이면 `10.30(금)~11.1(일)`), `time`, `summary`. 카드 전체가 `ev.url` 링크
  - 맨 아래 `상시 전시·행사` 섹션, 마지막에 `마지막 갱신 2026-10-26 05:00`
  - 모든 글자는 `html.escape`. 외부 스크립트 없음, 인라인 CSS, 모바일 폭 기준

- [ ] **Step 1:** 테스트
  - `test_escapes_brackets`: 제목 `'테마전시 <고문서로 만나는 조선의 일상>'` → 결과에 `&lt;고문서` 포함, `<고문서` 없음
  - `test_empty_area_hidden`: 광교 행사 없음 → `'>광교<'` 없음
  - `test_area_order`: 행궁동·스타필드 행사 → `스타필드 수원`이 `행궁동`보다 앞
  - `test_no_tags`: 결과에 `유모차`, `주차` 없음
- [ ] **Step 2:** 실패 확인 → 구현 → 통과 확인
- [ ] **Step 3:** 커밋 `feat: 페이지 렌더`

### Task 7: 전체 실행(build)과 실패 시 보존

**Files:**
- Create: `suwon_kids/build.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: 위 모든 Produces
- Produces:
  - `build.run(today: date, out_dir: Path, sources: dict[str, Callable[[], list[Event]]], detail=suwon_portal.fetch_detail, gen=ai.generate) -> dict` — 반환 `{'ok': bool, 'counts': {source: n}, 'errors': {source: msg}}`
  - 흐름: 출처별 수집(한 출처 실패해도 나머지 계속) → `overlaps` → 시 포털 후보만 `detail`로 host·body 채움 → `keep` → `areas.assign` → `merge` → `one_line` → 30일 초과는 상시로 → `site/events.json`(`{"updated": ISO, "week": [start, end], "events": [...], "long": [...]}`), `site/index.html`
  - **모든 출처가 실패하거나 결과가 0건이면 `out_dir`의 기존 파일을 건드리지 않고 `ok=False`**
  - 명령: `python3 -m suwon_kids.build` (오늘 날짜, `site/`)

- [ ] **Step 1:** 테스트 (가짜 sources·detail·gen)
  - `test_all_sources_fail_keeps_old`: 기존 `events.json` 내용 `X`, 모든 source가 예외 → 파일 내용 그대로 `X`, `ok is False`
  - `test_one_source_fails_others_written`: starfield 예외, suwon 1건 → `events.json`에 1건, `errors`에 `'starfield'`
  - `test_events_json_shape`: 키 `updated`, `week`, `events`, `long`; event에 `title`, `start`, `end`, `area`, `url`, `summary`
- [ ] **Step 2:** 실패 확인 → 구현 → 통과 확인
- [ ] **Step 3:** 실데이터: `python3 -m suwon_kids.build` → `site/index.html`을 브라우저로 열어 동네별로 이번 주 행사가 보이는지 확인. 스크린샷을 사용자에게 보낸다
- [ ] **Step 4:** 커밋 `feat: 전체 빌드`

### Task 8: 경기아트센터·경기문화재단 (선택)

**Files:**
- Create: `suwon_kids/sources/gyeonggi.py`; Modify: `suwon_kids/build.py` (sources에 추가)
- Test: `tests/test_gyeonggi.py`, `tests/fixtures/ggac_*.html|json`

**Interfaces:**
- Produces: `gyeonggi.fetch_ggac() -> list[Event]`, `gyeonggi.fetch_ggcf() -> list[Event]` (수원 소재 행사만, `host`는 `'경기아트센터'`/`'경기문화재단'`)

- [ ] **Step 1:** `https://www.ggac.or.kr/`, `https://www.ggcf.kr/`의 공연·행사 목록 위치와 JSON 요청을 브라우저 네트워크 탭으로 찾는다. 30분 안에 못 찾거나 로그인·차단이 필요하면 이 Task를 건너뛰고 이유를 기록한다 (설계 7-1)
- [ ] **Step 2:** 찾았으면 fixture 저장 → 파싱 테스트(제목·날짜·장소) → 구현 → 통과
- [ ] **Step 3:** 커밋 `feat: 경기 출처 수집` 또는 건너뜀 기록을 이 계획 파일에 추가

### Task 9: 공개 저장소·Pages·매일 자동 실행

**Files:**
- Create: `deploy.py`, `scheduler/com.suwonkids.build.plist`, `README.md`(실행·재설치 3줄)

**Interfaces:**
- Produces: `python3 deploy.py` — `build.run` 실행, `ok`면 `site/`·`state/`만 `git add` → 바뀐 게 있으면 `git commit -m "data: YYYY-MM-DD"` → `git push`. `ok=False`면 커밋하지 않고 종료 코드 1, `logs/build-YYYY-MM-DD.log`에 오류

- [ ] **Step 1:** 커밋 전 `git ls-files | grep -E '\.env$'` 결과 없음 확인
- [ ] **Step 2:** `gh repo create HWANGJEONGHYEON1/suwon-kids --public --source . --push` (사용자 승인 받음 2026-10-26)
- [ ] **Step 3:** Pages 켜기: `gh api -X POST repos/HWANGJEONGHYEON1/suwon-kids/pages -f "source[branch]=main" -f "source[path]=/"`. Pages는 루트(`/`)나 `/docs`만 고를 수 있으므로 `deploy.py`가 `site/index.html`·`site/events.json`을 저장소 루트의 `index.html`·`events.json`으로 복사하고 둘 다 커밋한다
- [ ] **Step 4:** `curl -sI https://hwangjeonghyeon1.github.io/suwon-kids/` → `200`, `curl -s https://hwangjeonghyeon1.github.io/suwon-kids/events.json`의 `updated`가 오늘
- [ ] **Step 5:** plist: 매일 05:00, `ProgramArguments`=`[/usr/local/opt/python@3.15/bin/python3.15, /Users/hwangjeonghyeon/Documents/suwon-kids/deploy.py]`, `WorkingDirectory`=저장소. `cp scheduler/com.suwonkids.build.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.suwonkids.build.plist && launchctl start com.suwonkids.build` → 로그에 성공, 새 커밋 push 확인
- [ ] **Step 6:** 커밋·push `chore: 배포와 매일 실행`

### Task 10: 블로그 주간 글 (ai-hub)

**Files (`~/Documents/ai-hub`):**
- Create: `content-factory/automation/suwon_kids_post.py`, `content-factory/automation/test_suwon_kids_post.py`, `shared/scheduler/com.aihub.suwon-kids-post.plist`
- Modify: `content-factory/automation/yt/fi_bot.py` — `ACTIONS`에 `'kids': ('../suwon_kids_post.py', '--approve', '주간 글 승인 → deert303 발행')`, `ROOTS`에 `'kids': (HUB / 'content-factory/blog/suwon-kids', 'blog')`
- Modify: `content-factory/CLAUDE.md` 자동 발행 절에 한 줄

**Interfaces:**
- Consumes: `https://hwangjeonghyeon1.github.io/suwon-kids/events.json` (없으면 `~/Documents/suwon-kids/site/events.json`), `fi_bot.send(text, action, folder, label, topic)`, `naver_fast.publish(post, category, images, publish_now, blog='blog.naver.com/deert303', account='u1')`
- Produces:
  - `select(events: list[dict], sat: date, sun: date) -> list[dict]` — 토·일에 걸치는 행사, 주최 예외 축제 먼저, 동네별 최대 2개, 최대 8개
  - `write_post(picked: list[dict], sat: date) -> dict` — `{'title': '이번 주말 수원, 아이랑 갈 만한 곳 (M.D~M.D)', 'body': ...}`. 동네별 소제목, 행사마다 제목·날짜·시간·한 줄 요약·원문 링크, 끝에 `전체 일정은 여기서: https://hwangjeonghyeon1.github.io/suwon-kids/`. 쿠팡·쇼핑커넥트 링크 없음
  - `--draft`: 폴더 `content-factory/blog/suwon-kids/YYYY-MM-DD/`에 `research.json`(선정 행사)·`post.md` 저장 → `fi_bot.send(원고 앞부분, 'kids', 폴더, '발행 승인', topic='blog')`
  - `--approve <폴더>`: 지금이 그 주 금요일 12:00 이후면 발행하지 않고 텔레그램에 "마감 지나 건너뜀". 아니면 `naver_fast.publish(..., publish_now=True)` → 결과 URL을 텔레그램 `blog` 주제로
  - 카테고리: deert303의 기존 카테고리 중 하나. 구현 시 `naver_fast.publish(..., check_only=True)`로 카테고리 선택이 되는지 확인하고, 맞는 카테고리가 없으면 사용자에게 묻는다

- [ ] **Step 1:** 테스트
  - `test_select_weekend_only`: 수요일만 하는 행사 제외
  - `test_select_host_festival_first`: 주최 예외 축제가 첫 번째
  - `test_select_max_two_per_area`, `test_select_max_eight`
  - `test_post_has_app_link_no_affiliate`: 본문에 앱 주소 있음, `coupang`·`쇼핑커넥트` 없음
  - `test_approve_after_deadline_skips`: 금요일 12:01 → `publish` 호출 0회 (가짜 publish 주입)
- [ ] **Step 2:** `python3 -m unittest content-factory/automation/test_suwon_kids_post.py` 실패 확인 → 구현 → 통과
- [ ] **Step 3:** `--draft` 실제 실행 → 텔레그램 `blog` 주제에 원고와 [발행 승인] 버튼 도착 확인. **발행 버튼은 누르지 않는다** (사용자가 누른다)
- [ ] **Step 4:** plist: 목요일 18:00 `--draft`. `launchctl load` 후 `launchctl list | grep suwon-kids-post`
- [ ] **Step 5:** `fi_bot` 재시작(`launchctl kickstart -k gui/$(id -u)/com.aihub.hub-bot`) 후 기존 봇 테스트 통과 확인
- [ ] **Step 6:** 커밋·push `content-factory: 수원 아이랑 주간 글 초안·승인 발행`
