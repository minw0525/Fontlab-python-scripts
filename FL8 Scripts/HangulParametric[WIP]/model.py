"""Pure selection, target-space editing and document validation."""

import copy
import itertools
import json
import math

JAMO = (tuple('ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'),
        tuple('ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'),
        ('없음',) + tuple('ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ'))
VOWEL_ORDER = tuple('ㅏㅑㅓㅕㅣㅐㅒㅔㅖㅗㅛㅡㅜㅠㅘㅚㅝㅟㅢㅙㅞ')
BOX_KEYS = ('x', 'y', 'w', 'h')
LIB_KEY = 'com.Minwoo.HangulParametricDerivation'
SCHEMA = 1


def characters(text):
    return list(dict.fromkeys(c for c in text if '가' <= c <= '힣'))


def decompose(char):
    if len(char) != 1 or not '가' <= char <= '힣':
        raise ValueError('Expected one modern Hangul syllable.')
    n = ord(char) - 0xAC00
    return n // 588, n % 588 // 28, n % 28


def ordered_characters(selections, order=(0, 1, 2), vowel_order='shape'):
    ranks = {JAMO[1].index(c): i for i, c in enumerate(VOWEL_ORDER)}
    rows = itertools.product(*(sorted(s) for s in selections))
    def sort_key(row):
        return tuple(ranks[row[p]] if p == 1 and vowel_order == 'shape' else row[p]
                     for p in order)
    return [chr(0xAC00 + a * 588 + b * 28 + c) for a, b, c in sorted(rows, key=sort_key)]


def checked_box(box):
    if not isinstance(box, dict) or set(box) != set(BOX_KEYS):
        raise ValueError('Invalid box fields.')
    if any(type(box[k]) not in (float, int) or not math.isfinite(box[k]) for k in BOX_KEYS):
        raise ValueError('Invalid box values.')
    result = {k: int(round(box[k])) for k in BOX_KEYS}
    if result['w'] <= 0 or result['h'] <= 0:
        raise ValueError('Box dimensions must be positive.')
    return result


def role_indices(count, has_final, grouped_vowel=False):
    expected = 3 if has_final else 2
    if count < expected or (not grouped_vowel and count != expected):
        raise ValueError('요소 {}개, 예상 {}개. 초중종 구분 필요'.format(count, expected))
    if not grouped_vowel:
        return [[i] for i in range(expected)]
    return [[0], list(range(1, count - 1)), [count - 1]] if has_final else [[0], list(range(1, count))]


def union_boxes(boxes):
    x, y = min(b['x'] for b in boxes), min(b['y'] for b in boxes)
    return checked_box({'x': x, 'y': y,
                        'w': max(b['x'] + b['w'] for b in boxes) - x,
                        'h': max(b['y'] + b['h'] for b in boxes) - y})


def layout_run(chars, cell, break_mode, widths=None, extra_height=0):
    """Logical rows depend on jamo conditions, never on viewport dimensions."""
    items, x, y, previous = [], 16, 24, None
    for char in chars:
        part = decompose(char)
        group = part[:2] if break_mode == 0 else part[:1] if break_mode == 1 else None
        if previous is not None and group != previous:
            x, y = 16, y + cell * 1.45 + extra_height
        items.append((char, x, y))
        x += widths.get(char, cell) if widths is not None else cell
        previous = group
    return items, int(y + cell * 1.45 + extra_height)


def visible_run(items, offset, height, cell, x_offset=0, width=None, widths=None, extra_height=0):
    return [(char, x - x_offset, y - offset) for char, x, y in items
            if y + cell * 1.4 + extra_height >= offset and y <= offset + height
            and (width is None or (x + (widths.get(char, cell) if widths is not None else cell) >= x_offset and x <= x_offset + width))]


def hit_role(boxes, x, y, current=0):
    hits = [r for r, b in enumerate(boxes) if b is not None
            and b['x'] <= x <= b['x'] + b['w'] and b['y'] <= y <= b['y'] + b['h']]
    return min(hits, key=lambda r: (boxes[r]['w'] * boxes[r]['h'], r != current, r)) if hits else None


def drag_box(box, handle, dx, dy):
    """Font coordinates: positive Y points up. Opposite resize corner stays fixed."""
    b = dict(box)
    if handle == 'move':
        b['x'] += dx
        b['y'] += dy
    else:
        if 'e' in handle:
            b['w'] = max(1, box['w'] + dx)
        if 'w' in handle:
            b['w'] = max(1, box['w'] - dx)
            b['x'] = box['x'] + box['w'] - b['w']
        if 'n' in handle:
            b['h'] = max(1, box['h'] + dy)
        if 's' in handle:
            b['h'] = max(1, box['h'] - dy)
            b['y'] = box['y'] + box['h'] - b['h']
    return checked_box(b)


class Session:
    def __init__(self):
        self.sample_text = ''
        self.observations = {}
        self.predictions = {}
        self.sources = {}
        self.source_guides = {}
        self.managed_components = {}
        self.design_anchors = {}
        self.overrides = {}
        self.target_text = ''
        self.grouped_vowel = False
        self.dirty = False
        self.reference_initial = None
        self.batch_undo = None

    def box(self, char, role):
        override = self.overrides.get(char, {}).get(str(role))
        if override is not None:
            return dict(override)
        return self.base_box(char, role)

    def base_box(self, char, role):
        record = self.observations.get(char) or self.predictions.get(char)
        if record and role < len(record['boxes']):
            return dict(record['boxes'][role])
        return None

    def infer(self):
        from .inference import RelationModel
        self.predictions = RelationModel(self.observations, self.reference_initial).predict_all()
        self.dirty = True

    def state(self, char):
        if char not in self.observations and self.predictions.get(char, {}).get('mode') == 'reference':
            return '기준 전이·미보정'
        return '실측' if char in self.observations else '추론' if char in self.predictions else '근거 부족'

    def preview_batch(self, targets, role, delta):
        pending, skipped = {}, []
        for char in dict.fromkeys(targets):
            box = self.box(char, role)
            if box is None:
                skipped.append(char)
            else:
                pending[char] = checked_box({k: box[k] + delta[k] for k in BOX_KEYS})
        return pending, skipped

    def commit_batch(self, pending, role):
        validated = {c: checked_box(b) for c, b in pending.items()}
        if any(self.box(c, role) is None for c in validated):
            raise ValueError('No target space for batch edit.')
        before = {c: copy.deepcopy(self.overrides.get(c, {}).get(str(role))) for c in validated}
        for char, box in validated.items():
            self.set_box(char, role, box)
        self.batch_undo = (role, before, validated)

    def undo_batch(self):
        if self.batch_undo is None:
            return
        role, before, after = self.batch_undo
        if any(self.overrides.get(c, {}).get(str(role)) != b for c, b in after.items()):
            raise ValueError('배치 적용 후 개별 수정이 있어 되돌릴 수 없습니다.')
        for char, box in before.items():
            if box is None:
                self.reset(char, role)
            else:
                self.set_box(char, role, box)
        self.batch_undo = None

    def set_box(self, char, role, box):
        if self.box(char, role) is None:
            raise ValueError('No measured or inferred space for this role.')
        self.overrides.setdefault(char, {})[str(role)] = checked_box(box)
        self.dirty = True

    def reset(self, char, role):
        entry = self.overrides.get(char, {})
        if str(role) in entry:
            del entry[str(role)]
            if not entry:
                self.overrides.pop(char)
            self.dirty = True

    def apply_delta(self, char, role, original, targets):
        current = self.box(char, role)
        delta = {k: current[k] - original[k] for k in BOX_KEYS}
        pending = {}
        for target in targets:
            if target == char or decompose(target)[role] != decompose(char)[role]:
                continue
            box = self.box(target, role)
            if box is not None:
                pending[target] = checked_box({k: box[k] + delta[k] for k in BOX_KEYS})
        for target, box in pending.items():
            self.set_box(target, role, box)
        return len(pending)

    def to_data(self):
        return copy.deepcopy({'sampleText': self.sample_text, 'observations': self.observations,
                              'predictions': self.predictions, 'sources': self.sources,
                              'overrides': self.overrides, 'targetText': self.target_text,
                              'groupedVowel': self.grouped_vowel, 'referenceInitial': self.reference_initial,
                              'sourceGuides': self.source_guides, 'designAnchors': self.design_anchors,
                              'managedComponents': self.managed_components})

    @classmethod
    def from_data(cls, data):
        # PythonQt returns native lib arrays as tuples; use JSON array semantics.
        data = json.loads(json.dumps(data, ensure_ascii=False, allow_nan=False))
        session = cls()
        session.reference_initial = data.get('referenceInitial')
        if session.reference_initial is not None and (type(session.reference_initial) is not int or not 0 <= session.reference_initial < 19):
            raise ValueError('Invalid reference initial.')
        session.sample_text = data.get('sampleText', '')
        session.target_text = data.get('targetText', '')
        session.grouped_vowel = data.get('groupedVowel', False)
        if type(session.grouped_vowel) is not bool:
            raise ValueError('Invalid role mapping mode.')
        if not isinstance(session.sample_text, str) or not isinstance(session.target_text, str):
            raise ValueError('Invalid stored text.')
        for char, record in data.get('observations', {}).items():
            expected = 3 if decompose(char)[2] else 2
            if len(record['boxes']) != expected:
                raise ValueError('Stored role count mismatch: ' + char)
            session.observations[char] = dict(record, boxes=[checked_box(b) for b in record['boxes']])
        for char, record in data.get('predictions', {}).items():
            if len(record['boxes']) != (3 if decompose(char)[2] else 2):
                raise ValueError('Stored prediction role count mismatch: ' + char)
            session.predictions[char] = dict(record, boxes=[checked_box(b) for b in record['boxes']])
        session.sources = dict(data.get('sources', {}))
        session.source_guides = dict(data.get('sourceGuides', {}))
        for char, roles in data.get('managedComponents', {}).items():
            decompose(char)
            if not isinstance(roles, dict) or any(k not in ('0','1','2') or not isinstance(v, str)
                                                 for k,v in roles.items()):
                raise ValueError('Invalid managed component record.')
            session.managed_components[char] = dict(roles)
        session.design_anchors = dict(data.get('designAnchors', {}))
        for char, roles in data.get('overrides', {}).items():
            for role, box in roles.items():
                if role not in ('0', '1', '2'):
                    raise ValueError('Invalid stored role.')
                session.set_box(char, int(role), box)
        session.dirty = False
        return session


def decode_document(raw):
    if raw is None:
        return {'schemaVersion': SCHEMA, 'masters': {}}
    document = json.loads(raw) if isinstance(raw, str) else copy.deepcopy(raw)
    if not isinstance(document, dict) or document.get('schemaVersion') != SCHEMA:
        raise ValueError('Unsupported relation document schema; existing data preserved.')
    if not isinstance(document.get('masters'), dict):
        raise ValueError('Invalid masters document.')
    return document


def merge_master(raw, layer, session):
    document = decode_document(raw)
    document['masters'][layer] = session.to_data()
    return json.dumps(document, ensure_ascii=False, allow_nan=False)
