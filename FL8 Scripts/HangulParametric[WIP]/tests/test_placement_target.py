import unittest

from HangulParametric.model import Session
from HangulParametric.svc import placement_target, reference_target, map_reference
from HangulParametric.metrics import metric_rows


def record(x, y):
    return {'boxes': [dict(x=x, y=y, w=100, h=200) for _ in range(3)]}


class PlacementTargetTests(unittest.TestCase):
    def session(self):
        s = Session()
        s.reference_initial = 11
        s.observations = {'암': record(20, 100), '악': record(25, 120),
                          '맘': record(40, 300)}
        s.infer()
        return s

    def test_one_target_design_transfers_relative_movement_without_mutation(self):
        s = self.session()
        before = s.to_data()
        target, info = placement_target(s, '막', 0)
        self.assertEqual((target['x'], target['y']), (45, 320))
        self.assertEqual(info['anchors'], ['맘'])
        self.assertEqual(info['scope'], 'same-vowel')
        self.assertEqual(s.to_data(), before)

    def test_manual_offsets_once_and_source_controls_size(self):
        s = self.session()
        base = s.box('막', 0)
        s.set_box('막', 0, dict(base, x=base['x']+7, y=base['y']-3))
        target, _ = placement_target(s, '막', 0)
        ratios, correction = reference_target(s, '막', 0)
        result = map_reference(target, ratios, correction,
                               lambda u, v: dict(x=10, y=20, w=450, h=550))
        self.assertEqual(result['target'], dict(x=52, y=317, w=450, h=550))
        self.assertEqual(result['delta'], dict(x=42, y=297))

    def test_same_vowel_preferred_over_other_vowel(self):
        s = self.session()
        s.observations.update({'얌': record(100, 200), '먐': record(500, 600)})
        target, info = placement_target(s, '막', 0)
        self.assertEqual(target['x'], 45)
        self.assertEqual(info['anchors'], ['맘'])

    def test_other_family_not_used_and_fallback_is_explicit(self):
        s = self.session()
        del s.observations['맘']
        s.observations['몸'] = record(900, 900)
        target, info = placement_target(s, '막', 0)
        self.assertEqual(target, s.box('막', 0))
        self.assertEqual(info['mode'], 'unanchored')

    def test_observed_target_position_is_unchanged(self):
        s = self.session()
        target, info = placement_target(s, '맘', 0)
        self.assertEqual(target, s.box('맘', 0))
        self.assertEqual(info['mode'], 'target')

    def test_actual_metrics_do_not_replace_reference_or_delta(self):
        s = self.session()
        actual = dict(x=45, y=320, w=450, h=550)
        rows = dict(metric_rows(s, '막', 0, 1, evaluated_box=actual))
        self.assertEqual(rows['상태'], 'SVC 실제')
        self.assertEqual(rows['W'], '450')
        delta = dict(metric_rows(s, '막', 0, 2, evaluated_box=actual))
        self.assertEqual(delta['ΔX'], '+0')
