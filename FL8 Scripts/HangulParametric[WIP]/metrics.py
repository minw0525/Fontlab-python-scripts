"""Read-only per-glyph metric rows in font units or reference proportions."""

from .model import BOX_KEYS, decompose


def metric_rows(session, char, role, mode, box=None, evaluated_box=None, strict_closed=False):
    if strict_closed and decompose(char)[2]:
        from .mieum_relations import estimate
        try:
            relation = estimate(session.observations, char, role, session.reference_initial)
        except ValueError as error:
            return [('상태', '관계 충돌' if str(error).startswith('관계 충돌:') else '근거 부족')]
        if mode == 0:
            anchor = session.observations[relation['anchors'][0]]['boxes'][role]
            return [('W', '×{:.3f}'.format(relation['box']['w']/anchor['w'])),
                    ('H', '×{:.3f}'.format(relation['box']['h']/anchor['h'])),
                    ('기준', relation['anchors'][0]),
                    ('관계', ' '.join(a+'→'+b for a,b in relation['pairs']) or '직접 실측'),
                    ('상태', '우선 추론·충돌' if relation.get('conflicts') else '실측' if relation['mode'] == 'observed' else
                     ('전이·검증 제한' if relation['support'] == 1 else '실측 대비 전이') if relation['mode'] == 'local-transfer' else
                     '모음 간 전이' if relation.get('crossVowel') else 'ㅁ 기준 추정')]
        if mode == 1:
            current = evaluated_box or box or relation['box']
            return [(k.upper(), str(round(current[k]))) for k in BOX_KEYS] + [
                ('상태', '우선 추론·충돌' if relation.get('conflicts') else 'SVC 실제' if evaluated_box is not None else 'ㅁ 기준 목표')]
    base = session.base_box(char, role)
    box = box if box is not None else session.box(char, role)
    if base is None or box is None:
        return [('상태', '역할 없음' if role == 2 and not decompose(char)[2] else '근거 부족')]
    prediction = session.predictions.get(char, {}) if char not in session.observations else {}
    reference = prediction.get('mode') == 'reference'
    state = '검증 부족' if prediction.get('basis') == 'unverified' else '전이' if reference else session.state(char)
    if mode == 0:
        ratios = prediction.get('normalized', [])
        if role < len(ratios):
            normalized = ratios[role]
        else:
            from .inference import source_key
            peers = [session.base_box(c, role) for c in session.observations
                     if source_key(c, role) == source_key(char, role)]
            normalized = {}
            for k in ('w', 'h'):
                low = min((b[k] for b in peers), default=base[k])
                high = max((b[k] for b in peers), default=base[k])
                normalized[k] = (base[k]-low)/(high-low) if high > low else None
        rows = [(label, '{:.1f}%'.format(normalized[k]*100) if normalized.get(k) is not None else '미정')
                for k, label in (('w', 'W'), ('h', 'H'))]
        rows += [('기준', prediction.get('referenceChar', char)),
                 ('표본', ' '.join(e['donor'] for e in prediction.get('evidence', [])) or char)]
    elif mode == 1:
        if evaluated_box is not None:
            box = evaluated_box
        rows = [(k.upper(), str(round(box[k]))) for k in BOX_KEYS]
        state = 'SVC 실제' if evaluated_box is not None else '관계 참고' if reference else '목표 공간'
    else:
        rows = [('Δ'+k.upper(), '{:+d}'.format(round(box[k]-base[k]))) for k in BOX_KEYS]
    return rows + [('상태', state)]
