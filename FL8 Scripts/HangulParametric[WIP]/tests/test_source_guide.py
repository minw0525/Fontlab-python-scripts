import unittest

from HangulParametric.model import Session
from HangulParametric.svc import source_design_guide, format_source_guide, source_plan


def record(w, h):
    return {'boxes': [dict(x=0, y=0, w=w, h=h) for _ in range(3)]}


class SourceGuideTests(unittest.TestCase):
    def test_reference_without_target_contours_and_synthetic_corners(self):
        s = Session()
        s.observations = {'악': record(100, 300), '안': record(200, 200)}
        s.reference_initial = 11
        s.infer()
        before = s.to_data()
        guide = source_design_guide(s, '막', 0)
        self.assertTrue(guide['reference'])
        corner = guide['corners'][0]
        self.assertEqual(corner['exactTargets'], [])
        self.assertEqual(corner['widthTargets'], [])
        self.assertEqual(corner['heightTargets'], [])
        self.assertTrue(guide['missing'])
        self.assertIn('맘', format_source_guide(guide))
        self.assertIn('독립 코너 디자인 필요', format_source_guide(guide))
        self.assertEqual(s.to_data(), before)
        plan = source_plan(s, '막', 0)
        self.assertTrue(plan['empty'])
        self.assertTrue(all(c['donor'] is None for c in plan['corners']))
        self.assertEqual(len(plan['corners']), 4)

    def test_measured_targets_match_generation_and_constant_axes(self):
        s = Session()
        s.observations = {'막': record(100, 200), '만': record(100, 300)}
        guide = source_design_guide(s, '막', 0)
        self.assertFalse(guide['reference'])
        self.assertEqual(guide['constantAxes'], ['w'])
        self.assertEqual(source_plan(s, '막', 0)['ranges'], guide['ranges'])
        self.assertFalse(source_plan(s, '막', 0)['empty'])

    def test_saved_source_guide_roundtrip(self):
        s = Session()
        s.observations = {'악': record(100, 200)}
        s.infer()
        guide = source_design_guide(s, '막', 0)
        guide['corners'][0]['layerName'] = 'Thin:width=0,height=0'
        s.source_guides['_test'] = guide
        loaded = Session.from_data(s.to_data())
        self.assertEqual(loaded.source_guides['_test']['corners'], guide['corners'])

    def test_role_and_layout_boundaries(self):
        s = Session()
        s.observations = {'악': record(100, 200), '약': record(150, 250), '옥': record(500, 600)}
        s.infer()
        guide = source_design_guide(s, '막', 1)
        self.assertEqual(guide['ranges']['w'], [100, 100])
        self.assertEqual(guide['corners'][0]['exactTargets'], [])
        self.assertEqual(guide['constantAxes'], ['w', 'h'])

    def test_no_target_design_has_conditions_not_reference_dimensions(self):
        s = Session()
        s.reference_initial = 11
        s.observations = {'악': record(123, 345), '안': record(234, 456)}
        guide = source_design_guide(s, '막', 0)
        text = format_source_guide(guide)
        self.assertIsNone(guide['ranges'])
        self.assertNotIn('123', text)
        self.assertNotIn('345', text)
        self.assertIn('막', text)
        self.assertTrue(all(c['box'] is None for c in source_plan(s, '막', 0)['corners']))

    def test_one_target_sample_is_a_design_not_a_range_estimate(self):
        s = Session()
        s.reference_initial = 11
        s.observations = {'악': record(100, 300), '안': record(200, 200),
                          '암': record(150, 250), '맘': record(420, 510)}
        s.infer()
        before = s.to_data()
        self.assertEqual(source_design_guide(s, '막', 0), source_design_guide(s, '맘', 0))
        plan = source_plan(s, '막', 0)
        self.assertEqual([c['donor'] for c in plan['corners']], ['맘'] * 4)
        self.assertTrue(all(c['box']['w'] == 420 and c['box']['h'] == 510 for c in plan['corners']))
        self.assertEqual(plan['guide']['corners'][0]['widthTargets'][0]['char'], '막')
        self.assertEqual(plan['guide']['corners'][0]['heightTargets'][0]['char'], '만')
        self.assertEqual(s.to_data(), before)

    def test_manual_override_does_not_resize_source_donor(self):
        s = Session()
        s.observations = {'맘': record(420, 510)}
        s.set_box('맘', 0, dict(x=20, y=30, w=100, h=200))
        plan = source_plan(s, '맘', 0)
        self.assertEqual(plan['corners'][0]['box'], dict(x=0, y=0, w=420, h=510))
