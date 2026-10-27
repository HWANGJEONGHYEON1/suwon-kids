# 수원 아이랑 이번 주

이번 주 수원·근교 행사(수원시 행사축제포털·스타필드 수원·경기아트센터, 근교 아이 공연은 KOPIS, 근교 큰 축제는 TourAPI)를 동네·시별로 모은 페이지: https://hwangjeonghyeon1.github.io/suwon-kids/

- 수동 실행: `python3 deploy.py` (빌드만: `python3 -m suwon_kids.build`)
- 테스트: `python3 -m unittest discover -s tests -t .`
- 매일 05:00 자동 실행: `cp scheduler/com.suwonkids.build.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.suwonkids.build.plist`
- `.env`(커밋 안 함): `GEMINI_API_KEY`, `GEMINI_MODEL`, `KOPIS_KEY`(kopis.or.kr 메일 발급), `TOURAPI_KEY`(data.go.kr 한국관광공사_국문 관광정보 서비스_GW, 디코딩된 키)
- KOPIS 데이터는 출처 표기가 의무다. 페이지 푸터 문구(`render.SOURCES`)를 지우지 말 것
