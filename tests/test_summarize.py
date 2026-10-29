import json
import unittest
from datetime import date

from suwon_kids import summarize
from suwon_kids.models import Event

SRC = '제3회 문화도시 수원 페스티벌. 9일 가수 손승연, 10일 가수 임창정 공연. 공연과 체험은 모두 무료.'
EV = Event('suwon:1', 'suwon', '제3회 문화도시 수원 페스티벌', date(2026, 10, 9), date(2026, 10, 10), None, '', '', '', '누구나')


class FakeGen:
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), 0

    def __call__(self, prompt, image_url=None):
        self.calls += 1
        return self.answers.pop(0)


class VerifiedTest(unittest.TestCase):
    def test_verified_ok(self):
        self.assertTrue(summarize.verified('임창정·손승연 무료 공연', SRC))

    def test_verified_invented_name(self):
        self.assertFalse(summarize.verified('아이유 무료 공연', SRC))

    def test_verified_time(self):
        self.assertFalse(summarize.verified('18:30 개막', SRC))


class OneLineTest(unittest.TestCase):
    def test_one_line_ok(self):
        self.assertEqual(summarize.one_line(EV, SRC, gen=FakeGen('임창정·손승연 무료 공연')), '임창정·손승연 무료 공연')

    def test_one_line_rejects_unverified(self):
        self.assertIsNone(summarize.one_line(EV, SRC, gen=FakeGen('아이유 무료 공연')))

    def test_one_line_same_as_title(self):
        self.assertIsNone(summarize.one_line(EV, SRC, gen=FakeGen('제3회 문화도시 수원 페스티벌')))

    def test_one_line_too_long(self):
        self.assertIsNone(summarize.one_line(EV, SRC, gen=FakeGen('공연 ' * 30)))

    def test_one_line_ai_error(self):
        def boom(prompt, image_url=None):
            raise summarize.ai.AIError('quota')
        self.assertIsNone(summarize.one_line(EV, SRC, gen=boom))


POSTER = {'programs': [{'name': '쿠키 만들기', 'date': '11.7', 'time': '14:00', 'age': '5~7세'}],
          'time': '오후 2시/5시', 'venue': '3F 별마당 키즈', 'price': '무료'}


class PosterTest(unittest.TestCase):
    def test_poster_needs_two_matching_reads(self):
        other = {'programs': [{'name': '쿠키 만들기', 'date': '11.7', 'time': '15:00', 'age': '5~7세'}]}
        self.assertIsNone(summarize.read_poster('u1', {}, gen=FakeGen(json.dumps(POSTER), json.dumps(other))))
        self.assertEqual(summarize.read_poster('u2', {}, gen=FakeGen(json.dumps(POSTER), json.dumps(POSTER))), POSTER)

    def test_poster_cache_hit(self):
        gen = FakeGen()
        self.assertEqual(summarize.read_poster('u1', {'u1': POSTER}, gen=gen), POSTER)
        self.assertEqual(gen.calls, 0)

    def test_old_cache_without_common_fields_is_reread(self):
        gen = FakeGen(json.dumps(POSTER), json.dumps(POSTER))
        self.assertEqual(summarize.read_poster('u1', {'u1': {'programs': POSTER['programs']}}, gen=gen), POSTER)
        self.assertEqual(gen.calls, 2)

    def test_reread_failure_keeps_old_cache(self):
        old = {'programs': POSTER['programs']}
        self.assertEqual(summarize.read_poster('u1', {'u1': old}, gen=FakeGen('x', 'y')), old)

    def test_common_field_kept_only_when_both_reads_agree(self):
        other = dict(POSTER, venue='2F 별마당 키즈')
        got = summarize.read_poster('u3', {}, gen=FakeGen(json.dumps(POSTER), json.dumps(other)))
        self.assertEqual(got['programs'], POSTER['programs'])
        self.assertEqual((got['venue'], got['price']), ('', '무료'))

    def test_poster_stores_in_cache(self):
        cache = {}
        summarize.read_poster('u1', cache, gen=FakeGen('```json\n' + json.dumps(POSTER) + '\n```', json.dumps(POSTER)))
        self.assertEqual(cache['u1'], POSTER)


if __name__ == '__main__':
    unittest.main()


class ReviewFixTest(unittest.TestCase):
    def test_verified_latin_name(self):
        self.assertFalse(summarize.verified('BTS 무료 공연', SRC))

    def test_verified_date_and_price(self):
        self.assertFalse(summarize.verified('11.2 불꽃 축제', SRC))
        self.assertFalse(summarize.verified('5,000원 체험', SRC))

    def test_poster_second_read_uses_different_prompt(self):
        prompts = []

        def gen(prompt, image_url=None):
            prompts.append(prompt)
            return json.dumps(POSTER)
        summarize.read_poster('u9', {}, gen=gen)
        self.assertEqual(len(prompts), 2)
        self.assertNotEqual(prompts[0], prompts[1])
