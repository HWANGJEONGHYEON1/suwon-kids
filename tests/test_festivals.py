import unittest
from datetime import date

from suwon_kids import festivals


def fake(items, intros):
    def get(op, **kw):
        if op == 'searchFestival2':
            return {'totalCount': len(items), 'items': {'item': items}}
        if op == 'detailIntro2':
            return {'items': {'item': [intros[kw['contentId']]]}}
        if op == 'detailInfo2':
            return {'items': {'item': [{'infoname': '행사소개', 'infotext': '소개<br>글'}]}}
        return {'items': {'item': []}}  # 장소 사진 없음
    return get


def it(i, title, start='20261107', addr='경기도 김포시'):
    return {'contentid': i, 'title': title, 'eventstartdate': start, 'eventenddate': start, 'addr1': addr}


class FestivalsTest(unittest.TestCase):
    def test_keeps_only_free_gyeonggi_festivals_within_lead(self):
        items = [it('1', '가을 불꽃축제'), it('2', '유료 축제'), it('3', '일부 유료 축제'), it('4', '상설공연'),
                 it('5', '경주 축제', addr='경상북도 경주시'), it('6', '먼 축제', '20270101')]
        intros = {'1': {'usetimefestival': '무료', 'eventplace': '호수공원', 'program': '- 불꽃쇼<br>- 먹거리'},
                  '2': {'usetimefestival': '10,000원'}, '3': {'usetimefestival': '무료(일부 프로그램 유료)'},
                  '4': {'usetimefestival': '무료'}, '5': {'usetimefestival': '무료'}, '6': {'usetimefestival': '무료'}}
        got = festivals.fetch(date(2026, 11, 2), fake(items, intros))
        self.assertEqual([f['title'] for f in got], ['가을 불꽃축제'])
        self.assertEqual(got[0]['program'], ['불꽃쇼', '먹거리'])
        self.assertEqual((got[0]['place'], got[0]['start'], got[0]['summary']), ('호수공원', '2026-11-07', '소개\n글'))

    def test_admission_free_counts(self):
        got = festivals.fetch(date(2026, 11, 2), fake([it('1', '김장문화축제')], {'1': {'usetimefestival': '입장료 무료'}}))
        self.assertEqual(got[0]['price'], '입장료 무료')

    def test_program_numbers_and_headers_are_stripped(self):
        self.assertEqual(festivals._lines('1. 주요 프로그램<br>1. 불꽃쇼: 19:30<br>- 먹거리'), ['불꽃쇼: 19:30', '먹거리'])


if __name__ == '__main__':
    unittest.main()
