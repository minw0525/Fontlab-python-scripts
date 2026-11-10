"""Source design guides and bounded, measured SVC location solving."""

import math
import hashlib
import re
import unicodedata
from statistics import median
from .inference import source_key, RelationModel, family
from .model import BOX_KEYS, JAMO, decompose

CORNERS = ((0, 0), (1000, 0), (0, 1000), (1000, 1000))


def source_name(char, role, master):
    jamo = JAMO[role][decompose(char)[role]]
    letter = unicodedata.name(jamo).replace('HANGUL LETTER ', '', 1).lower().replace(' ', '-')
    master_label = re.sub(r'[^A-Za-z0-9_-]', '_', master)
    if master_label != master:
        master_label += '-' + hashlib.sha1(master.encode('utf8')).hexdigest()[:8]
    layout, closed = family(char)
    return '_hp.{}{}-ko.{}.{}.{}'.format(letter, ('Cho', 'Jung', 'Jong')[role], layout,
                                       'closed' if closed else 'open', master_label)


def reference_target(session, char, role):
    prediction = session.predictions.get(char, {})
    if char in session.observations or prediction.get('mode') != 'reference':
        return None, None
    ratios = prediction.get('normalized', [])
    if role >= len(ratios):
        return None, None
    base, box = session.base_box(char, role), session.box(char, role)
    return ratios[role], {k: box[k]-base[k] for k in ('w', 'h')}


def design_candidates(session, char, role):
    return sorted(c for c, r in session.observations.items()
                  if source_key(c, role) == source_key(char, role)
                  and decompose(c)[0] == decompose(char)[0] and role < len(r['boxes']))


def source_mapping(session, char, role, model=None):
    """One design anchor sets units; without it source corners set units."""
    if decompose(char)[2]:
        from .mieum_relations import estimate
        result = estimate(session.observations, char, role, session.reference_initial)
        mapped = dict(result['box'])
        base, target = session.base_box(char, role), session.box(char, role)
        if base is not None and target is not None:
            mapped = {k: mapped[k] + target[k] - base[k] for k in BOX_KEYS}
        from .model import checked_box
        return checked_box(mapped), None, None, result
    target = session.box(char, role)
    if target is None:
        raise ValueError('관계 근거 없음: ' + char)
    candidates = design_candidates(session, char, role)
    anchor = session.design_anchors.get(source_key(char, role))
    if anchor and anchor not in candidates:
        raise ValueError('기준 디자인을 다시 선택하세요: ' + anchor)
    if not anchor and len(candidates) > 1:
        raise ValueError('대상 실측이 여러 개입니다. 기준 디자인을 선택하세요.')
    anchor = anchor or (candidates[0] if candidates else None)
    if model is None:
        model = RelationModel(session.observations, session.reference_initial)
    _, profile = model.reference_profile(family(char))
    _, v, f = decompose(char)
    reference = profile.get((v, f))
    if reference is None or role >= len(reference['boxes']):
        raise ValueError('기준 관계에 대응 조건이 없습니다: ' + char)
    base = session.base_box(char, role)
    correction = {k: target[k]-base[k] for k in BOX_KEYS}
    if anchor is None:
        return (target, reference['normalized'][role], {k: correction[k] for k in ('w', 'h')},
                dict(mode='unanchored', anchors=[]))
    _, av, af = decompose(anchor)
    origin = profile.get((av, af))
    if origin is None or role >= len(origin['boxes']):
        raise ValueError('선택한 기준 디자인에 대응하는 관계 표본이 없습니다: ' + anchor)
    design = session.observations[anchor]['boxes'][role]
    ref, ref_anchor = reference['boxes'][role], origin['boxes'][role]
    mapped = {k: (design[k] * ref[k] / ref_anchor[k] if k in ('w', 'h')
                  else design[k] + ref[k] - ref_anchor[k]) + correction[k] for k in BOX_KEYS}
    from .model import checked_box
    return checked_box(mapped), None, None, dict(mode='design-anchor', anchors=[anchor])


def placement_target(session, char, role, model=None):
    """Anchor reference movement in observed target designs, never predictions."""
    target = session.box(char, role)
    prediction = session.predictions.get(char, {})
    if char in session.observations or prediction.get('mode') != 'reference' or target is None:
        return target, dict(mode='target', anchors=[])
    if model is None:
        model = RelationModel(session.observations, prediction['referenceInitial'])
    _, profile = model.reference_profile(family(char))
    initial, vowel, final = decompose(char)
    reference = profile.get((vowel, final))
    if reference is None or role >= len(reference['boxes']):
        return target, dict(mode='unanchored', anchors=[])
    candidates = []
    for c, record in sorted(session.observations.items()):
        a, v, f = decompose(c)
        if a != initial or source_key(c, role) != source_key(char, role) or role >= len(record['boxes']):
            continue
        origin = profile.get((v, f))
        if origin is not None and role < len(origin['boxes']):
            candidates.append((c, v, record['boxes'][role], origin['boxes'][role]))
    same_vowel = [c for c in candidates if c[1] == vowel]
    candidates = same_vowel or candidates
    if not candidates:
        return target, dict(mode='unanchored', anchors=[])
    base = session.base_box(char, role)
    mapped = dict(target)
    offsets = {k: [b[k]-ref[k] for _, _, b, ref in candidates] for k in ('x', 'y')}
    for k in ('x', 'y'):
        mapped[k] = reference['boxes'][role][k] + median(offsets[k]) + target[k]-base[k]
    return mapped, dict(mode='anchored', anchors=[c[0] for c in candidates],
                        scope='same-vowel' if same_vowel else 'family',
                        spread={k: max(offsets[k])-min(offsets[k]) for k in offsets})


def map_reference(target, normalized, correction, evaluate):
    uv = [int(round(1000 * (normalized[k] if normalized[k] is not None else 0))) for k in ('w', 'h')]
    if any(not 0 <= n <= 1000 for n in uv):
        raise ValueError('기준 비례가 SVC 범위를 벗어났습니다. 재추론이 필요합니다.')
    measured = evaluate(*uv)
    mapped = dict(target, **{k: measured[k] + correction[k] for k in ('w', 'h')})
    if any(correction.values()):
        result = solve_location(mapped, evaluate)
    else:
        result = dict(location=dict(zip(('width', 'height'), uv)), box=measured, error=0,
                      delta={k: int(round(mapped[k]-measured[k])) for k in ('x', 'y')})
    return dict(result, target=mapped, mode='reference',
                unobservedAxes=[k for k in ('w', 'h') if normalized[k] is None])


def source_design_guide(session, char, role):
    """Describe relative corner conditions separately from target design samples."""
    key = source_key(char, role)
    initial = decompose(char)[0]
    reference_initial, profile = RelationModel(
        session.observations, session.reference_initial).reference_profile(family(char))
    records = []
    for (vowel, final), record in sorted(profile.items()):
        target = chr(0xAC00 + initial*588 + vowel*28 + final)
        if source_key(target, role) == key and role < len(record['boxes']):
            records.append(dict(char=target, ratio=record['normalized'][role],
                                reference=record['referenceChar'], basis=record['basis']))
    missing = []
    closed = bool(decompose(char)[2])
    if closed:
        from .mieum_relations import guide_records
        records, missing = guide_records(session, char, role)
    if not records and not closed:
        raise ValueError('이 자소의 극값 조건을 추정할 관계 표본이 없습니다. 전이 기준과 표본을 확인하세요.')
    designs = [dict(char=c, box=dict(r['boxes'][role])) for c, r in sorted(session.observations.items())
               if source_key(c, role) == key and role < len(r['boxes'])]
    ranges = ({k: [min(r['box'][k] for r in designs), max(r['box'][k] for r in designs)]
               for k in ('w', 'h')} if designs else None)
    constant = [k for k in ('w', 'h') if all(r['ratio'][k] is None for r in records)]
    corners = []
    for u, v in CORNERS:
        width_refs = [r for r in records if r['ratio']['w'] == u / 1000] if 'w' not in constant else []
        height_refs = [r for r in records if r['ratio']['h'] == v / 1000] if 'h' not in constant else []
        exact = [r for r in width_refs if r in height_refs]
        nearest = min(records, key=lambda r: (sum(
            (r['ratio'][k] - n / 1000)**2 for k, n in (('w', u), ('h', v))
            if r['ratio'][k] is not None), r['char'])) if records else None
        corners.append(dict(location={'width': u, 'height': v},
                            exactTargets=exact, widthTargets=width_refs, heightTargets=height_refs,
                            nearest=nearest))
    candidates = design_candidates(session, char, role)
    anchor = session.design_anchors.get(key) or (candidates[0] if len(candidates) == 1 else None)
    recommended = None
    if not closed and anchor in candidates:
        _, av, af = decompose(anchor)
        origin = profile.get((av, af))
        if origin is not None:
            design = session.observations[anchor]['boxes'][role]
            values = [{k: design[k] * profile[decompose(r['char'])[1:]]['boxes'][role][k] /
                       origin['boxes'][role][k] for k in ('w', 'h')} for r in records]
            recommended = {k: [min(b[k] for b in values), max(b[k] for b in values)] for k in ('w', 'h')}
    if closed:
        from .mieum_relations import baseline
        anchor = baseline(char, role)
        recommended = ({k: [min(r['box'][k] for r in records), max(r['box'][k] for r in records)]
                        for k in ('w', 'h')} if records else None)
    return dict(version=2, key=key, role=role, jamo=JAMO[role][decompose(char)[role]],
                family=family(char), reference=reference_initial != initial, referenceInitial=reference_initial,
                ranges=ranges, designs=designs, conditions=records, corners=corners, constantAxes=constant,
                designAnchor=anchor, recommendedRanges=recommended, missing=missing,
                relationPolicy='mieum-closed' if closed else 'open')


def format_source_note(guide):
    """Short, replaceable note; keep the full reasoning in the design dialog."""
    lines = ['[HangulParametric]', '{} · {} · {} · X 0 / Y 0'.format(
        guide['jamo'], ('초성', '중성', '종성')[guide['role']], guide['family'][0])]
    ranges = guide.get('recommendedRanges')
    for corner in guide['corners']:
        loc = corner['location']
        target = (corner['exactTargets'][0] if corner['exactTargets'] else corner['nearest'])
        size = ('W {:g} / H {:g}'.format(round(ranges['w'][loc['width']//1000], 2),
                                       round(ranges['h'][loc['height']//1000], 2))
                if ranges else 'W/H 미정')
        lines.append('w{} h{} · {} · {} {}'.format(
            loc['width'], loc['height'], size,
            '조건' if corner['exactTargets'] else '참고', target['char'] if target else '없음'))
    lines.append('[/HangulParametric]')
    return '\n'.join(lines)


def replace_source_note(note, guide, previous=None):
    start, end = '[HangulParametric]', '[/HangulParametric]'
    block = format_source_note(guide)
    if start in note and end in note[note.index(start):]:
        a = note.index(start)
        b = note.index(end, a) + len(end)
        return note[:a] + block + note[b:]
    legacy = None
    if previous:
        try:
            legacy = format_source_guide(previous)
        except (KeyError, TypeError, IndexError):
            # Older/incomplete snapshots cannot safely identify a generated note.
            pass
    if not note or note == legacy:
        return block
    return note.rstrip() + '\n\n' + block


def format_source_guide(guide):
    if guide.get('version') == 2:
        return format_relation_guide(guide)
    def labels(records):
        return ', '.join('{} [{}{}]'.format(r['char'], r['reference'],
                         ' / 검증 부족' if r['basis'] == 'unverified' else '') for r in records)
    lines = ['{} · {} · {} · {} 소스 디자인 안내'.format(guide['jamo'], ('초성', '중성', '종성')[guide['role']],
             guide['family'][0], '받친글자' if guide['family'][1] else '민글자'),
             '치수: ' + ('기준 계열의 참고값 · 대상 자소의 확정 크기가 아닙니다.' if guide['reference'] else
                       '대상 자소의 현재 목표값 · 수동 보정 포함.'),
             'W {}~{} / H {}~{} unit'.format(*guide['ranges']['w'], *guide['ranges']['h']),
             '변화가 관측되지 않은 축: ' + (', '.join(guide['constantAxes']) or '없음')]
    for c in guide['corners']:
        lines += ['', 'width={width}, height={height} · W {w} / H {h}'.format(**c['location'], **c['box']),
                  '소스 내부 좌표: X 0 / Y 0 (왼쪽 아래 정규화)',
                  '가까운 글자 {}의 참고 공간: X {x} / Y {y} / W {w} / H {h}'.format(c['nearest']['char'], **c['nearest']['box'])]
        if not c['exactTargets']:
            lines.append('참고 X/Y는 출발 글자의 위치입니다. 합성 코너의 유일한 배치 좌표는 아닙니다.')
        if c.get('copiedFrom'):
            lines.append('실제 복사 표본 {}: X {x} / Y {y} / W {w} / H {h}'.format(c['copiedFrom'], **c['copiedBox']))
        if 'layerName' in c:
            lines.append('레이어: ' + c['layerName'])
        if c['exactTargets']:
            lines.append('이 조건의 자소를 디자인: ' + labels(c['exactTargets']))
        else:
            lines += ['두 극값이 동시에 나타나는 글자가 없습니다. 독립 코너 디자인 필요.',
                      '가까운 출발 글자: ' + labels([c['nearest']])]
        lines += ['너비 참고: ' + labels(c['widthTargets']), '높이 참고: ' + labels(c['heightTargets'])]
    lines += ['', '각 글자 전체가 아닌 선택 역할의 자소를 소스 레이어에 넣습니다.',
              '서로 다른 표본을 복사했다면 컨투어 수, 노드 수·순서, 시작점 호환성을 확인하세요.',
              '대상 소스의 실제 극값은 직접 디자인합니다. 기존 윤곽은 이 안내로 변경하지 않습니다.']
    return '\n'.join(lines)


def format_relation_guide(guide):
    def labels(records):
        return ', '.join('{} (관계 표본 {}{})'.format(r['char'], r['reference'],
                         ', 검증 부족' if r['basis'] == 'unverified' else '') for r in records) or '미정'
    lines = ['{} · {} · {} · {} 소스 디자인 안내'.format(
        guide['jamo'], ('초성', '중성', '종성')[guide['role']], guide['family'][0],
        '받친글자' if guide['family'][1] else '민글자'),
        '관계에서 추정한 극값 조건입니다. 기준 자소의 절대 치수는 제작 목표로 사용하지 않습니다.',
        '소스 내부 좌표: X 0 / Y 0 (왼쪽 아래 정규화)',
        '변화가 관측되지 않은 축: ' + (', '.join(guide['constantAxes']) or '없음'),
        '', '대상 자소의 실측 디자인 (전체 극값으로 확정하지 않음):']
    for record in guide['designs']:
        lines.append('{}: X {x} / Y {y} / W {w} / H {h}'.format(record['char'], **record['box']))
    if not guide['designs']:
        lines.append('없음. 아래 조건을 참고해 각 코너의 자소를 디자인하세요.')
    if guide.get('recommendedRanges'):
        lines.append('계산 가능한 실측·관계 조건의 코너 목표 (수동 보정 제외):')
    if guide.get('missing'):
        lines += ['', '근거 부족 {}조건: 아래 극값은 계산 가능한 조건 안의 범위이며 전체 범위를 보장하지 않습니다.'.format(len(guide['missing']))]
        lines += [message for _, message in guide['missing'][:8]]
        if len(guide['missing']) > 8:
            lines.append('나머지 부족 조건은 해당 글자의 SVC 계산 시 표시합니다.')
    for c in guide['corners']:
        lines += ['', 'width={width}, height={height}'.format(**c['location'])]
        if 'layerName' in c:
            lines.append('레이어: ' + c['layerName'])
        if guide.get('recommendedRanges'):
            ranges = guide['recommendedRanges']
            lines.append('X 0 / Y 0 / W {:.2f} / H {:.2f}'.format(
                ranges['w'][c['location']['width']//1000], ranges['h'][c['location']['height']//1000]))
        lines += ['너비 {} 조건: {}'.format('최소' if c['location']['width'] == 0 else '최대', labels(c['widthTargets'])),
                  '높이 {} 조건: {}'.format('최소' if c['location']['height'] == 0 else '최대', labels(c['heightTargets']))]
        if c['exactTargets']:
            lines.append('두 조건이 겹치는 글자: ' + labels(c['exactTargets']))
        else:
            lines.append('두 극값의 공통 조건이 없거나 축 근거가 부족합니다. 독립 코너 디자인 필요.')
        if c.get('copiedFrom'):
            lines.append('실제 복사 표본 {}: X {x} / Y {y} / W {w} / H {h}'.format(c['copiedFrom'], **c['copiedBox']))
            lines.append('원래 크기를 유지한 출발 윤곽입니다. 이 코너 조건에 맞춰 직접 수정하세요.')
    lines += ['', '관측 변화가 없는 축은 최소/최대 조건을 확정할 수 없습니다.',
              '각 글자 전체가 아닌 선택 역할의 자소를 디자인합니다.',
              '네 코너의 컨투어 수, 노드 수·순서, 시작점 호환성을 확인하세요.',
              '기존 소스와 디자인은 변경하지 않습니다.']
    return '\n'.join(lines)


def source_plan(session, char, role):
    guide = source_design_guide(session, char, role)
    key = guide['key']
    samples = guide['designs']
    conditions = {r['char']: r['ratio'] for r in guide['conditions']}
    ranges = guide['ranges']
    corners = []
    for u, v in CORNERS:
        def distance(sample):
            ratios = conditions.get(sample['char'], {})
            known = [(ratios.get(k), n / 1000) for k, n in (('w', u), ('h', v))
                     if ratios.get(k) is not None]
            return (-len(known), sum((a-b)**2 for a, b in known), sample['char'])
        sample = min(samples, key=distance) if samples else None
        box = sample['box'] if sample else None
        corners.append(dict(location={'width': u, 'height': v},
                            box=dict(x=0, y=0, w=box['w'], h=box['h']) if box else None,
                            donor=sample['char'] if sample else None, exact=False))
    return dict(key=key, ranges=ranges, corners=corners, empty=not samples, guide=guide)


def solve_location(target, evaluate, tolerance=1.0):
    """Fit actual evaluated component dimensions; never silently clamp a miss."""
    best = None
    for start in ((0., 0.), (500., 500.), (1000., 1000.)):
        uv = list(start)
        for _ in range(18):
            box = evaluate(*uv)
            residual = [target[k] - box[k] for k in ('w', 'h')]
            error = max(abs(v) for v in residual)
            if best is None or error < best[0]:
                best = (error, list(uv))
            if error <= .1:
                break
            columns = []
            for axis in (0, 1):
                # FontLab can quantize interpolated boxes to whole font units.
                # Expand the probe until it crosses a quantization plateau.
                direction = 1 if uv[axis] <= 500 else -1
                for distance in (1., 10., 50., 100., 250., 1000.):
                    shifted = list(uv)
                    shifted[axis] = max(0., min(1000., uv[axis] + direction * distance))
                    step = shifted[axis] - uv[axis]
                    sample = evaluate(*shifted)
                    if any(abs(sample[k]-box[k]) > 1e-6 for k in ('w', 'h')):
                        break
                columns.append([(sample[k]-box[k])/step for k in ('w', 'h')])
            a, b = columns
            # Damped least squares also handles a constant width or height axis.
            aa = sum(v*v for v in a) + 1e-8
            bb = sum(v*v for v in b) + 1e-8
            ab = sum(x*y for x, y in zip(a, b))
            ar = sum(x*y for x, y in zip(a, residual))
            br = sum(x*y for x, y in zip(b, residual))
            determinant = aa*bb-ab*ab
            delta = [(ar*bb-br*ab)/determinant, (br*aa-ar*ab)/determinant]
            next_uv = [max(0., min(1000., x+d)) for x, d in zip(uv, delta)]
            if max(abs(x-y) for x, y in zip(uv, next_uv)) < .001:
                break
            uv = next_uv
        if best[0] <= .1:
            break
    uv = [int(round(v)) for v in best[1]]
    box = evaluate(*uv)
    error = max(abs(target[k]-box[k]) for k in ('w', 'h'))
    if not math.isfinite(error) or error > tolerance:
        raise ValueError('SVC 크기 재현 오차 {:.2f} unit: 목표 W {}/H {}, 평가 W {:.2f}/H {:.2f}, location {}. 소스 범위·코너 확인 필요'.format(
            error, target['w'], target['h'], box['w'], box['h'], uv))
    return {'location': dict(zip(('width', 'height'), uv)),
            'delta': {k: int(round(target[k]-box[k])) for k in ('x', 'y')},
            'box': {k: box[k] for k in BOX_KEYS}, 'error': error}
