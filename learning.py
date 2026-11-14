"""출제용 문항과 교육 콘텐츠. 외부 네트워크 없이 실행됩니다."""
import json
from pathlib import Path

UNITS = json.loads(Path(__file__).with_name('content.json').read_text(encoding='utf-8'))
SOURCES = [
 ('한국세무사회 자격시험 안내', 'https://license.kacpta.or.kr/'),
 ('한국회계기준원 회계기준 열람', 'https://kasb.kifrs.com/'),
 ('국세청 부가가치세 개요', 'https://nts.go.kr/nts/cm/cntnts/cntntsView.do?cntntsId=7693&mi=2272'),
 ('국세청 원천징수 개요', 'https://i.nts.go.kr/nts/cm/cntnts/cntntsView.do?cntntsId=7701&mi=2413'),
]

def questions(unit):
    seed = sum(ord(ch) for ch in unit['id'])
    result = []
    for i, card in enumerate(unit['cards']):
        false = (seed + i) % 2 == 0
        result.append(dict(id=f"{unit['id']}-ox{i}", unit=unit['id'], type='OX',
            prompt=f"{card['others'][0] if false else card['term']} · {card['definition']}",
            options=['O', 'X'], correct=1 if false else 0,
            explain=f"{card['term']} · {card['definition']}"))
    for i, card in enumerate(unit['cards']):
        opts = [card['term']] + card['others']
        offset = (seed + i) % 4
        opts = opts[offset:] + opts[:offset]
        result.append(dict(id=f"{unit['id']}-mc{i}", unit=unit['id'], type='4지선다',
            prompt='다음 설명에 알맞은 것은? ' + card['definition'], options=opts,
            correct=opts.index(card['term']), explain=f"{card['term']} · {card['definition']}"))
    result.append(dict(id=f"{unit['id']}-mc3", unit=unit['id'], type='4지선다',
        prompt=unit['practice'], options=unit['options'], correct=unit['correct'], explain=unit['explain']))
    cards = unit['cards']
    opts = [f"{cards[0]['others'][0]} — {cards[0]['definition']}",
            f"{cards[1]['others'][0]} — {cards[1]['definition']}",
            f"{cards[2]['term']} — {cards[2]['definition']}",
            f"{cards[2]['others'][0]} — {cards[2]['definition']}"]
    offset = seed % 4
    result.append(dict(id=f"{unit['id']}-mc4", unit=unit['id'], type='4지선다',
        prompt='이 단원의 핵심을 바르게 연결한 것은?', options=opts[offset:] + opts[:offset],
        correct=(2-offset) % 4, explain=f"{cards[2]['term']} · {cards[2]['definition']}"))
    return result

QUESTIONS = {q['id']: q for unit in UNITS for q in questions(unit)}
UNIT_MAP = {u['id']:u for u in UNITS}
STAGES = {'learn':'배우기', 'practice':'해 보기', 'check':'확인하기'}

def first_latest(attempts):
    first, latest = {}, {}
    for row in sorted(attempts, key=lambda r:r['id']):
        key = (row['student'], row['question'])
        first.setdefault(key, row)
        latest[key] = row
    return list(first.values()), list(latest.values())

def percent(n, d):
    return round(100*n/d, 1) if d else 0
