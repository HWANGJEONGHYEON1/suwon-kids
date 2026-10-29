from dataclasses import dataclass, asdict
from datetime import date


@dataclass
class Event:
    id: str
    source: str
    title: str
    start: date
    end: date
    time: str | None
    place: str
    address: str
    url: str
    target: str
    host: str | None = None
    summary: str | None = None
    area: str | None = None
    image: str | None = None
    age: str | None = None      # 관람 연령 (KOPIS)
    price: str | None = None    # 가격 안내 (KOPIS)
    booking: str | None = None  # 예매 링크 (KOPIS)
    place_photo: dict | None = None  # {'url','credit','title'} 장소 사진 (TourAPI 공공누리 1유형만, place_photo.py)
    program: str | None = None  # 할 거리: 상세 페이지 '주요내용'·공연 시간 등 원문 그대로 (수원시·경기아트센터)

    def to_json(self) -> dict:
        d = asdict(self)
        d['start'], d['end'] = self.start.isoformat(), self.end.isoformat()
        return d
