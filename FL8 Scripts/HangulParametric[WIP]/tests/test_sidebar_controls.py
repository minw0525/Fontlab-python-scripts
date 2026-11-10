import ast
from pathlib import Path
import unittest
from unittest.mock import Mock
from types import SimpleNamespace


class SidebarControlsTests(unittest.TestCase):
    def test_repertoire_filter_removes_outside_selection(self):
        tree = ast.parse((Path(__file__).resolve().parents[1]/'app.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'RelationWindow')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'refresh')
        ns = {'value': lambda x: x, 'VOWEL_ORDER': (), 'JAMO': ((), (), ()),
              'ordered_characters': lambda *args: ['가', '각', '갂']}
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<refresh>', 'exec'), ns)
        owner = Mock(syncing=False, jamo_buttons=[[], [], []],
                     sort=SimpleNamespace(currentIndex=0), vowels=SimpleNamespace(currentIndex=0),
                     highlight=SimpleNamespace(currentIndex=2), range_only=Mock(checked=True),
                     repertoires=[{'가'}, {'가', '각'}], selected='갂', origin=None,
                     edit_selection={'각', '갂'}, session=Mock(observations={}))
        ns['refresh'](owner)
        self.assertEqual(owner.canvas.characters, ['가', '각'])
        self.assertEqual(owner.edit_selection, {'각'})
        self.assertEqual(owner.selected, '가')
        owner.range_only.checked = False
        ns['refresh'](owner)
        self.assertEqual(owner.canvas.characters, ['가', '각', '갂'])
        owner.highlight.currentIndex = 0
        owner.range_only.checked = True
        ns['refresh'](owner)
        self.assertEqual(owner.canvas.characters, ['가', '각', '갂'])
        owner.range_only.setEnabled.assert_called_with(False)

    def test_cancelled_remeasurement_does_not_refresh_source_note(self):
        tree = ast.parse((Path(__file__).resolve().parents[1]/'app.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'RelationWindow')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'refresh_design_guide')
        ns = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<refresh-guide>', 'exec'), ns)
        owner = Mock()
        owner.analyze.return_value = None
        ns['refresh_design_guide'](owner, '막', 0)
        owner.adapter.refresh_source_guide.assert_not_called()

    def test_wheel_is_ignored_without_calling_spinbox_default(self):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'app.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ScrollSafeSpinBox')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='wheelEvent')
        namespace={}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'<wheel>','exec'),namespace)
        event=Mock()
        namespace['wheelEvent'](None,event)
        event.ignore.assert_called_once_with()
        event.accept.assert_not_called()

    def test_both_editors_use_scroll_safe_controls(self):
        source=(Path(__file__).resolve().parents[1]/'app.py').read_text()
        self.assertEqual(source.count('spin = ScrollSafeSpinBox()'),2)
        self.assertNotIn('self.scope =',source)
        self.assertIn('self.single_edit_group.setVisible(not multiple)',source)
        self.assertIn('self.multi_edit_group.setVisible(multiple)',source)

    def test_every_selected_glyph_highlights_the_selected_role(self):
        source=(Path(__file__).resolve().parents[1]/'canvas.py').read_text()
        self.assertIn('chosen = char in self.owner.edit_selection and role == self.owner.role',source)
        self.assertNotIn('chosen = active and role == self.owner.role',source)

    def test_existing_source_populates_name_without_creation(self):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'app.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='RelationWindow')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='prepare_source')
        namespace={'__package__':'HangulParametric'}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'<prepare>','exec'),namespace)
        owner=Mock(selected='막',role=0,layer_name='Thin')
        owner.adapter.existing_source.return_value='existing-source'
        namespace['prepare_source'](owner)
        owner.source_name.setText.assert_called_once_with('existing-source')
        owner.adapter.prepare_source.assert_not_called()
        owner.show_source_guide.assert_not_called()

    def test_preview_is_integrated_and_apply_targets_selected_glyphs_only(self):
        source=(Path(__file__).resolve().parents[1]/'app.py').read_text()
        self.assertIn("for label in ('표본', '관계 설정'):",source)
        self.assertNotIn('self.derive_scope',source)
        self.assertIn('text = self.edit_selection',source)
        self.assertIn('self.preview_timer.setInterval(350)',source)

    def test_preview_failure_is_reported_without_modifying_font(self):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'app.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='RelationWindow')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='preview_pending')
        namespace={}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'<preview>','exec'),namespace)
        owner=Mock(selected='많',role=0,svc_paths={('많',0):object()},pending_update=None)
        owner.preview_source.side_effect=ValueError('unreachable')
        namespace['preview_pending'](owner)
        self.assertFalse(owner.svc_paths)
        self.assertIn('폰트 미적용',owner.location_label.setText.call_args.args[0])
        owner.bind_source.assert_not_called()

    def test_pending_edit_updates_existing_components_only(self):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'app.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='RelationWindow')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='preview_pending')
        namespace={}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'<update>','exec'),namespace)
        owner=Mock(pending_update=(['막','만'],0,'source'),layer_name='Thin')
        result=([('막','uniB9C9')],[],{})
        owner.adapter.derive_role.return_value=result
        namespace['preview_pending'](owner)
        owner.adapter.derive_role.assert_called_once_with(owner.session,'막만',0,'source','Thin',update_only=True)
        owner.show_apply_result.assert_called_once_with(*result)
        owner.preview_source.assert_not_called()
        self.assertIsNone(owner.pending_update)
