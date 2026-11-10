import ast
from pathlib import Path
import types
import unittest
from unittest.mock import Mock

from HangulParametric.model import Session


class DisplayOutlineTests(unittest.TestCase):
    def setUp(self):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'app.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='RelationWindow')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='outline_for_display')
        ns={}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'<display>','exec'),ns)
        self.read=ns['outline_for_display']
        self.owner=types.SimpleNamespace(paths={},display_paths={},session=Session(),adapter=Mock(),layer_name='Thin')

    def test_unmeasured_design_is_gray_and_cached_without_changing_session(self):
        owner=self.owner
        before=owner.session.to_data()
        path=object();owner.adapter.display_outline.return_value=path
        for _ in range(2):
            self.assertEqual(self.read(owner,'먹'),(path,False))
        owner.adapter.display_outline.assert_called_once_with('먹','Thin')
        self.assertEqual(before,owner.session.to_data())
        self.assertFalse(owner.paths)

    def test_only_verified_sample_paths_are_dark(self):
        owner=self.owner
        owner.session.observations['먹']={'boxes':[]}
        path=object();owner.paths['먹']=path
        self.assertEqual(self.read(owner,'먹'),(path,True))
        owner.paths.clear()
        owner.adapter.display_outline.return_value=path
        self.assertEqual(self.read(owner,'먹'),(path,False))

    def test_missing_geometry_is_cached_as_placeholder(self):
        owner=self.owner;owner.adapter.display_outline.return_value=None
        self.assertEqual(self.read(owner,'먹'),(None,False))
        self.assertEqual(self.read(owner,'먹'),(None,False))
        owner.adapter.display_outline.assert_called_once()

    def test_applied_non_sample_path_remains_gray_below_svc_overlay(self):
        owner=self.owner;path=object();owner.paths['먹']=path
        self.assertEqual(self.read(owner,'먹'),(path,False))
        owner.adapter.display_outline.assert_not_called()
