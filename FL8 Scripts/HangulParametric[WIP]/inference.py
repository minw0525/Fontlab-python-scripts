"""Calibrated inference with explicit provisional reference transfer fallback."""

from collections import defaultdict
from statistics import median

from SmartComponentHangulLab.scripts.joint_context_model import select_relation
from .model import BOX_KEYS, checked_box, decompose


def family(char):
    _, vowel, final = decompose(char)
    layout = 'V' if vowel in (8, 12, 13, 17, 18) else 'M' if vowel in (9, 10, 11, 14, 15, 16, 19) else 'H'
    return layout, bool(final)


def source_key(char, role):
    layout, closed = family(char)
    return '{}.{}.{}.{}'.format(role, decompose(char)[role], layout, 'closed' if closed else 'open')


class RelationModel:
    def __init__(self, observations, reference_initial=None):
        self.observations = observations
        self.reference_initial = reference_initial
        self.groups = defaultdict(dict)
        self.fits = {}
        self.profiles = {}
        for char, record in observations.items():
            a, v, f = decompose(char)
            vector = [box[k] for box in record['boxes'] for k in BOX_KEYS]
            # Across vowels: same initial, same layout and final presence.
            self.groups[('vowel', a, family(char), v)][f] = (char, vector)
            # Across initials: matched (vowel, final) contexts within a family.
            self.groups[('initial', family(char), a)][(v, f)] = (char, vector)

    def candidates(self, target_key, context):
        target = self.groups.get(target_key, {})
        out = []
        for key, donor in self.groups.items():
            if key[:-1] != target_key[:-1] or key == target_key or context not in donor:
                continue
            common = sorted(set(target) & set(donor))
            if len(common) < 3:
                continue
            cache_key = (target_key, key)
            if cache_key not in self.fits:
                self.fits[cache_key] = [select_relation(
                    [donor[c][1][i] for c in common], [target[c][1][i] for c in common])
                    for i in range(len(donor[context][1]))]
            fits = self.fits[cache_key]
            held = donor[context][1]
            values = [m['slope'] * v + m['offset'] for m, v in zip(fits, held)]
            identity = [m['strongIdentity'] and min(donor[c][1][i] for c in common) <= held[i]
                        <= max(donor[c][1][i] for c in common) for i, m in enumerate(fits)]
            out.append(dict(donor=donor[context][0], pairs=[[donor[c][0], target[c][0]] for c in common],
                            values=values, fits=fits, identity=identity, kind=target_key[0]))
        return out

    def calibrated(self, char):
        a, v, f = decompose(char)
        evidence = self.candidates(('vowel', a, family(char), v), f)
        evidence += self.candidates(('initial', family(char), a), (v, f))
        if not evidence:
            return None
        values = []
        for i in range(12 if f else 8):
            identities = [e for e in evidence if e['identity'][i]]
            pool = identities if identities and max(e['values'][i] for e in identities) - min(e['values'][i] for e in identities) <= .25 else evidence
            weights = [len(e['pairs']) / (1 + e['fits'][i]['cvMAE']) for e in pool]
            values.append(sum(e['values'][i] * w for e, w in zip(pool, weights)) / sum(weights))
        try:
            boxes = [checked_box(dict(zip(BOX_KEYS, values[i:i+4]))) for i in range(0, len(values), 4)]
        except ValueError:
            return None
        return {'boxes': boxes, 'evidence': [
            {'donor': e['donor'], 'pairs': e['pairs'], 'kind': e['kind'],
             'fitMAE': round(sum(m['cvMAE'] for m in e['fits']) / len(values), 2)} for e in evidence],
            'spread': round(max(max(e['values'][i] for e in evidence) - min(e['values'][i] for e in evidence)
                                for i in range(len(values))), 2)}

    def reference_profile(self, group_family):
        if group_family in self.profiles:
            return self.profiles[group_family]
        groups = {key[2]: group for key, group in self.groups.items()
                  if key[0] == 'initial' and key[1] == group_family}
        reference = self.reference_initial
        if reference is None and groups:
            reference = min(groups, key=lambda a: (-len(groups[a]), a))
        observed = groups.get(reference, {})
        profile = {}
        for context in sorted(set().union(*(set(g) for g in groups.values()))):
            v, f = context
            ref_char = chr(0xAC00 + reference * 588 + v * 28 + f) if reference is not None else None
            if context in observed:
                donor = observed[context][0]
                result = {'boxes': [dict(b) for b in self.observations[donor]['boxes']],
                          'evidence': [{'donor': donor, 'pairs': [], 'kind': 'reference', 'fitMAE': 0}],
                          'spread': 0, 'basis': 'observed'}
            elif not observed:
                continue
            else:
                result = self.calibrated(ref_char)
                if result:
                    result['basis'] = 'calibrated'
                else:
                    # Borrow only within-vowel contrasts anchored in real reference samples.
                    options = []
                    for a, group in groups.items():
                        common = sorted(c for c in set(group) & set(observed) if c[0] == v)
                        if a == reference or context not in group or not common:
                            continue
                        held = group[context][1]
                        values = []
                        for i, value in enumerate(held):
                            values.append(median(observed[c][1][i] * value / group[c][1][i]
                                                 if i % 4 in (2, 3) else
                                                 observed[c][1][i] + value - group[c][1][i]
                                                 for c in common))
                        options.append((len(common), a, values, group[context][0],
                                        [[group[c][0], observed[c][0]] for c in common]))
                    if not options:
                        continue
                    _, _, values, donor, pairs = min(options, key=lambda o: (-o[0], o[1]))
                    try:
                        boxes = [checked_box(dict(zip(BOX_KEYS, values[i:i+4])))
                                 for i in range(0, len(values), 4)]
                    except ValueError:
                        continue
                    result = {'boxes': boxes, 'basis': 'unverified', 'spread': 0,
                              'evidence': [{'donor': donor, 'pairs': pairs, 'kind': 'contrast',
                                            'fitMAE': None}]}
            profile[context] = dict(result, referenceChar=ref_char)
        # Fixed ranges include the completed profile, independent of the target/filter.
        for context, result in profile.items():
            result['normalized'] = []
            for role, box in enumerate(result['boxes']):
                peers = [r['boxes'][role] for c, r in profile.items()
                         if role == 0 or c[role-1] == context[role-1]]
                result['normalized'].append({})
                for metric in ('w', 'h'):
                    low, high = min(b[metric] for b in peers), max(b[metric] for b in peers)
                    result['normalized'][-1][metric] = ((box[metric]-low)/(high-low) if high > low else None)
        self.profiles[group_family] = (reference, profile)
        return reference, profile

    def transfer(self, char):
        _, v, f = decompose(char)
        reference, profile = self.reference_profile(family(char))
        result = profile.get((v, f))
        return dict(result, mode='reference', referenceInitial=reference) if result else None

    def predict(self, char):
        return self.calibrated(char) or self.transfer(char)

    def predict_all(self):
        predictions = {}
        for code in range(0xAC00, 0xD7A4):
            char = chr(code)
            if char not in self.observations:
                result = self.predict(char)
                if result is not None:
                    predictions[char] = result
        return predictions
