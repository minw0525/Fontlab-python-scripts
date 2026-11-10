"""Closed-syllable transfers with explicit mieum context baselines."""

from .model import BOX_KEYS, checked_box, decompose
from .inference import family, source_key

CHO_MIEUM = 6
JONG_MIEUM = 16


def syllable(initial, vowel, final):
    return chr(0xAC00 + initial * 588 + vowel * 28 + final)


def baseline(char, role):
    a, v, f = decompose(char)
    if not f:
        return None
    return syllable(a if role == 0 else CHO_MIEUM, v,
                    f if role == 2 else JONG_MIEUM)


def estimate(observations, char, role, reference_initial=None):
    """Transfer measured pairs within a layout; never train on predictions."""
    a, v, f = decompose(char)
    if not f:
        raise ValueError('민글자는 받친글자 관계로 계산하지 않습니다: ' + char)
    if role not in (0, 1, 2):
        raise ValueError('Invalid role')
    if char in observations:
        return dict(box=dict(observations[char]['boxes'][role]), anchors=[char], pairs=[], mode='observed')
    from .local_relations import local_transfer
    local = local_transfer(observations, char, role)
    if local is not None:
        return local
    anchor = baseline(char, role)
    center = syllable(CHO_MIEUM, v, JONG_MIEUM)
    pairs = []
    # Fix the reference initial for the family, not separately for each syllable.
    counts = {}
    for c in observations:
        if family(c) == family(char):
            initial = decompose(c)[0]
            counts[initial] = counts.get(initial, 0) + 1
    ref = reference_initial
    if ref is None and counts:
        ref = min(counts, key=lambda i: (-counts[i], i))
    if role == 0:
        if f != JONG_MIEUM:
            if ref is None:
                raise ValueError('종성 변화의 관계 표본이 없습니다. {} 기준 표본을 디자인하세요.'.format(anchor))
            pairs.append((syllable(ref, v, JONG_MIEUM), syllable(ref, v, f)))
    elif role == 2:
        if a != CHO_MIEUM:
            pairs.append((center, syllable(a, v, JONG_MIEUM)))
    else:
        if a != CHO_MIEUM:
            pairs.append((center, syllable(a, v, JONG_MIEUM)))
        if f != JONG_MIEUM:
            pairs.append((center, syllable(CHO_MIEUM, v, f)))
    required = list(dict.fromkeys([anchor] + [c for pair in pairs for c in pair]))
    missing = [c for c in required if c not in observations]
    if missing and ref is not None:
        donor = syllable(ref, v, f)
        # Prefer this vowel's measured calibration; otherwise use a stable pair
        # in the same layout. The target-vowel donor must still be measured.
        for cv in sorted(range(21), key=lambda cv: (cv != v, cv)):
            start, end = syllable(ref, cv, JONG_MIEUM), syllable(a, cv, JONG_MIEUM)
            frame = syllable(CHO_MIEUM, cv, JONG_MIEUM)
            required_pair = (donor, start, end) + ((frame,) if role in (1, 2) else ())
            if family(end) == family(char) and all(c in observations for c in required_pair):
                if role == 0:
                    origin, pair = end, (start, donor)
                else:
                    origin, pair = donor, (start, end)
                left = observations[pair[0]]['boxes'][role]
                right = observations[pair[1]]['boxes'][role]
                original = observations[origin]['boxes'][role]
                box = {k: original[k] * right[k] / left[k] if k in ('w', 'h')
                       else original[k] + right[k] - left[k] for k in BOX_KEYS}
                return dict(box=checked_box(box), anchors=[origin], pairs=[pair],
                            mode='mieum-context', frame=frame, crossVowel=cv != v)
    if missing:
        raise ValueError('근거 부족: {} · 필요한 기준/관계 글자: {}. 해당 자소를 디자인·분리한 뒤 표본에 추가하세요.'.format(
            char, ', '.join(missing)))
    box = dict(observations[anchor]['boxes'][role])
    for start, end in pairs:
        left, right = observations[start]['boxes'][role], observations[end]['boxes'][role]
        for k in BOX_KEYS:
            box[k] = box[k] * right[k] / left[k] if k in ('w', 'h') else box[k] + right[k] - left[k]
    return dict(box=checked_box(box), anchors=[anchor], pairs=pairs, mode='mieum-context')


def guide_records(session, char, role):
    """Only same-source, closed conditions participate in the corner proposal."""
    key = source_key(char, role)
    records, missing = [], []
    for code in range(0xAC00, 0xD7A4):
        c = chr(code)
        if source_key(c, role) != key:
            continue
        try:
            result = estimate(session.observations, c, role, session.reference_initial)
            if result.get('conflicts'):
                missing.append((c, '관계 충돌: {} · 코너 극값 산정에서 제외'.format(c)))
                continue
        except ValueError as error:
            missing.append((c, str(error)))
            continue
        records.append(dict(char=c, box=result['box'], reference=result['anchors'][0],
                            basis=result['mode'], pairs=result['pairs']))
    for r in records:
        r['ratio'] = {}
        for k in ('w', 'h'):
            low, high = min(s['box'][k] for s in records), max(s['box'][k] for s in records)
            r['ratio'][k] = (r['box'][k]-low)/(high-low) if high > low else None
    return records, missing
