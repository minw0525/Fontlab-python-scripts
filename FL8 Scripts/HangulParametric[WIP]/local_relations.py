"""Role-specific one-condition transfers from measured comparisons."""
from statistics import median
from .model import BOX_KEYS, decompose, checked_box
from .inference import family


def local_transfer(observations, char, role):
    target = decompose(char)
    samples = {decompose(c): (c, r['boxes'][role]) for c, r in observations.items()
               if family(c) == family(char) and role < len(r['boxes'])}
    candidates = []
    for axis in range(3):
        # Preserve the designed jamo; its shape is not interchangeable.
        if axis == role:
            continue
        context = tuple(target[i] for i in range(3) if i != axis)
        groups = {}
        for parts, record in samples.items():
            key = tuple(parts[i] for i in range(3) if i != axis)
            groups.setdefault(key, {})[parts[axis]] = record
        own = groups.get(context, {})
        minimum = 1 if role in (0, 2) and axis == 1 else 2
        if len(own) < minimum:
            continue
        for key, donor in sorted(groups.items()):
            if key == context or target[axis] not in donor:
                continue
            # Change only one additional context coordinate, not both.
            if sum(a != b for a, b in zip(key, context)) != 1:
                continue
            common = sorted(set(own) & set(donor))
            if len(common) < minimum:
                continue
            end, end_box = donor[target[axis]]
            # Local behavior may differ from the mieum baseline. Choose the
            # nearest two measured conditions before validating their transfer.
            common = sorted(common, key=lambda v: (sum(
                abs(donor[v][1][k] - end_box[k]) / max(1., end_box['w' if k in ('x','w') else 'h'])
                for k in BOX_KEYS), v))[:2]
            ratios = {k: [own[v][1][k] / donor[v][1][k] if k in ('w', 'h')
                          else own[v][1][k] - donor[v][1][k] for v in common]
                      for k in BOX_KEYS}
            # Leave each shared condition out; assess the remaining transfer.
            errors = []
            for j, v in enumerate(common):
                if len(common) == 1:
                    break
                for k in BOX_KEYS:
                    factor = median(ratios[k][:j] + ratios[k][j+1:])
                    predicted = donor[v][1][k] * factor if k in ('w', 'h') else donor[v][1][k] + factor
                    tolerance = max(1., own[v][1][k] * .02) if k in ('w', 'h') else 2.
                    errors.append(abs(predicted - own[v][1][k]) / tolerance)
            if max(errors, default=0) > 1:
                continue
            # Select a real nearby origin; do not average incompatible geometry.
            origins = []
            for v in common:
                start, start_box = donor[v]
                origin, box = own[v]
                mapped = {k: box[k] * end_box[k] / start_box[k] if k in ('w', 'h')
                          else box[k] + end_box[k] - start_box[k] for k in BOX_KEYS}
                distance = sum(abs(end_box[k] / start_box[k] - 1) for k in ('w', 'h'))
                origins.append((distance, origin, start, mapped))
            _, origin, start, mapped = min(origins, key=lambda x: (x[0], x[1]))
            candidates.append(dict(box=checked_box(mapped), anchors=[origin], pairs=[(start, end)],
                                   mode='local-transfer', support=len(common),
                                   validationError=max(errors) if errors else None, changedAxis=axis,
                                   comparisons=[(donor[v][0], own[v][0]) for v in common]))
    if not candidates:
        return None
    # For consonants retain both consonants and change only the vowel first.
    # Vowels already retain their identity because axis == role is excluded.
    candidates.sort(key=lambda c: (0 if role in (0, 2) and c['changedAxis'] == 1 else 1,
                                   -c['support'], c['validationError'] or 0,
                                   c['anchors'], c['pairs']))
    best = candidates[0]
    conflicts = []
    for other in candidates[1:]:
        if any(abs(best['box'][k] - other['box'][k]) >
               (max(1., min(best['box'][k], other['box'][k])*.02) if k in ('w','h') else 2.)
               for k in BOX_KEYS):
            conflicts.append(other)
    if conflicts:
        best = dict(best, conflicts=conflicts)
    return best
