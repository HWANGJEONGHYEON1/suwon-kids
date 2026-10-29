import unittest

from suwon_kids import place_photo


def body(*items):
    return {'items': {'item': list(items)}}


class PlacePhotoTest(unittest.TestCase):
    def test_candidates_shorten_by_words(self):
        self.assertEqual(place_photo.candidates('경기도어린이박물관 교육실 1 (용인)'),
                         ['경기도어린이박물관 교육실 1', '경기도어린이박물관 교육실', '경기도어린이박물관'])

    def test_short_names_not_searched_and_region_is_gyeonggi(self):
        self.assertEqual(place_photo.candidates('용인시 보정동'), ['용인시 보정동'])
        seen = []
        place_photo.lookup('수원전통문화관', {}, get=lambda op, **kw: seen.append(kw) or {})
        self.assertEqual(seen[0]['lDongRegnCd'], '41')

    def test_only_exact_title_and_type1(self):
        def get(op, keyword, **kw):
            return body({'title': keyword + ' 카페', 'cpyrhtDivCd': 'Type1', 'firstimage': 'a'},
                        {'title': keyword, 'cpyrhtDivCd': 'Type3', 'firstimage': 'b'})
        self.assertIsNone(place_photo.lookup('경기아트센터', {}, get=get))

        def get1(op, keyword, **kw):
            return body({'title': keyword, 'cpyrhtDivCd': 'Type1', 'firstimage': 'http://tong/1.jpg'})
        got = place_photo.lookup('수원전통문화관', {}, get=get1)
        self.assertEqual((got['url'], got['credit']), ('http://tong/1.jpg', '한국관광공사 / 공공누리 제1유형'))

    def test_falls_back_to_shorter_name_and_caches_misses(self):
        asked = []

        def get(op, keyword, **kw):
            asked.append(keyword)
            return body({'title': '일월수목원', 'cpyrhtDivCd': 'Type1', 'firstimage': 'u'}) if keyword == '일월수목원' else {}
        cache = {}
        self.assertEqual(place_photo.lookup('일월수목원 온실', cache, get=get)['url'], 'u')
        self.assertEqual(cache['일월수목원 온실'], None)
        place_photo.lookup('일월수목원 온실', cache, get=lambda *a, **k: self.fail('캐시를 안 씀'))
        self.assertEqual(asked, ['일월수목원 온실', '일월수목원'])


if __name__ == '__main__':
    unittest.main()
