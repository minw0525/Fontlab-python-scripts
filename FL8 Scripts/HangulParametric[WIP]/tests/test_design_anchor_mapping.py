import ast
from pathlib import Path
import unittest

from HangulParametric.model import Session
from HangulParametric.inference import source_key
from HangulParametric.svc import source_mapping, source_design_guide


def record(w, h, x=20, y=100):
    return {'boxes': [dict(x=x, y=y, w=w, h=h) for _ in range(3)]}


class DesignAnchorMappingTests(unittest.TestCase):
    def session(self):
        s = Session()
        s.reference_initial = 11
        s.observations = {'암': record(200,250), '악': record(240,300,25,120),
                          '맘': record(300,350,40,300)}
        s.infer()
        return s

    def test_ratio_sets_target_size_and_delta_sets_position(self):
        s = self.session()
        target, normalized, correction, info = source_mapping(s, '막', 0)
        self.assertEqual(target, dict(x=45,y=320,w=360,h=420))
        self.assertIsNone(normalized)
        self.assertIsNone(correction)
        self.assertEqual(info['anchors'], ['맘'])

    def test_overrides_apply_once(self):
        s = self.session()
        b = s.box('막', 0)
        s.set_box('막', 0, dict(b,x=b['x']+3,w=b['w']+7))
        target, _, _, _ = source_mapping(s, '막', 0)
        self.assertEqual(target['x'],48)
        self.assertEqual(target['w'],367)

    def test_measured_target_is_preserved_with_multiple_designs(self):
        s = self.session()
        s.observations['막'] = record(900,900)
        s.design_anchors[source_key('맘',0)] = '맘'
        loaded = Session.from_data(s.to_data())
        self.assertEqual(source_mapping(loaded,'막',0)[0]['h'],900)
        self.assertEqual(source_mapping(loaded,'맘',0)[0]['h'],350)

    def test_missing_mieum_design_requests_exact_baseline(self):
        s = self.session()
        del s.observations['맘']
        with self.assertRaisesRegex(ValueError, '맘'):
            source_mapping(s,'막',0)

    def test_legacy_arbitrary_design_is_ignored_for_closed_syllables(self):
        s = self.session()
        s.design_anchors[source_key('맘',0)] = '만'
        self.assertEqual(source_mapping(s,'막',0)[3]['anchors'], ['맘'])

    def test_corner_dimensions_use_target_anchor_not_reference_units(self):
        s = self.session()
        guide = source_design_guide(s,'막',0)
        self.assertEqual(guide['recommendedRanges'], dict(w=[300,360],h=[350,420]))

    def test_window_is_mac_tool_without_global_stays_on_top(self):
        tree = ast.parse((Path(__file__).resolve().parents[1]/'app.py').read_text())
        init = next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='__init__')
        attrs = [n.attr for n in ast.walk(init) if isinstance(n,ast.Attribute)]
        self.assertIn('Tool',attrs)
        self.assertNotIn('WindowStaysOnTopHint',attrs)
