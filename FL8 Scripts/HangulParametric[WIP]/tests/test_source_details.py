import ast
from pathlib import Path
import unittest
from unittest.mock import Mock

from HangulParametric.model import Session
from HangulParametric.svc import source_name, source_plan, source_design_guide, format_source_guide, format_source_note, replace_source_note


class SourceDetailsTests(unittest.TestCase):
    def test_incomplete_legacy_guide_keeps_note_and_adds_current_block(self):
        guide = source_design_guide(Session(), '막', 0)
        old = {'version': 2, 'jamo': 'ㄷ', 'role': 0, 'family': ['H', True]}
        text = replace_source_note('Existing design notes', guide, old)
        self.assertTrue(text.startswith('Existing design notes\n\n'))
        self.assertIn('[HangulParametric]', text)
        self.assertEqual(replace_source_note(text, guide, old), text)

    def test_short_note_uses_one_condition_per_corner_and_distinguishes_nearest(self):
        s = Session()
        s.observations = {c: {'boxes': [dict(x=0,y=0,w=w,h=h)]*3}
                          for c,w,h in [('막',100,300),('맘',200,200)]}
        guide = source_design_guide(s, '막', 0)
        note = format_source_note(guide)
        self.assertEqual(len(note.splitlines()), 7)
        self.assertIn('w0 h0 · W 100 / H 200 · 참고', note)
        self.assertIn('w1000 h0 · W 200 / H 200 · 조건 맘', note)
        self.assertEqual(replace_source_note('before\n'+note+'\nafter', guide),
                         'before\n'+note+'\nafter')

    def test_close_signal_discards_checked_argument(self):
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'app.py').read_text())
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'show_source_guide')
        button = next(n for n in ast.walk(method) if isinstance(n, ast.Call) and
                      isinstance(n.func, ast.Name) and n.func.id == 'button' and
                      isinstance(n.args[0], ast.Constant) and n.args[0].value == '닫기')
        dialog = Mock()
        callback = eval(compile(ast.Expression(button.args[1]), '<close callback>', 'eval'), {'dialog': dialog})
        callback(False)
        dialog.close.assert_called_once_with()

    def test_readable_name_and_master_collision_protection(self):
        self.assertEqual(source_name('막', 0, 'Thin'), '_hp.mieumCho-ko.H.closed.Thin')
        self.assertEqual(source_name('막', 1, 'Thin'), '_hp.aJung-ko.H.closed.Thin')
        self.assertNotEqual(source_name('막', 0, 'Thin A'), source_name('막', 0, 'Thin_A'))

    def test_each_corner_chooses_nearest_measured_donor(self):
        s = Session()
        s.observations = {c: {'boxes': [dict(x=x, y=200, w=w, h=h)] * 3}
                          for c,x,w,h in [('막',20,100,200),('만',30,200,200),
                                         ('말',40,100,300),('맘',50,200,300)]}
        plan = source_plan(s, '막', 0)
        self.assertEqual([c['donor'] for c in plan['corners']], ['막','만','말','맘'])
        guide = source_design_guide(s, '막', 0)
        text = format_source_guide(guide)
        self.assertIn('X 0 / Y 0', text)
        self.assertIn('X 20 / Y 200 / W 100 / H 200', text)
