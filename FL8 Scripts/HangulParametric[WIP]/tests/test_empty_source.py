import types
import hashlib
import unittest
from unittest.mock import Mock, patch

from test_master_recovery import adapter_class
from HangulParametric.model import Session
from HangulParametric.svc import format_source_note, format_source_guide


class EmptySourceTests(unittest.TestCase):
    def setUp(self):
        cls = adapter_class()
        self.adapter = cls.__new__(cls)
        self.adapter.require_master = Mock()
        self.adapter.upm = 1000
        self.glyphs = {}
        self.adapter.font = types.SimpleNamespace(
            hasGlyph=lambda name: name in self.glyphs, newGlyph=self.new_glyph,
            glyph=lambda name: self.glyphs[name], update=Mock())
        self.adapter.package = types.SimpleNamespace(deleteGlyph=lambda glyph: self.glyphs.pop(glyph.name))
        self.session = Session()
        self.session.observations = {'악': {'boxes': [dict(x=0, y=0, w=100, h=200)] * 3}}
        self.session.infer()
        fl = cls.prepare_source.__globals__['fl6']
        self.patch = patch.object(fl, 'flLayer', self.new_layer, create=True)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def new_layer(self):
        layer = types.SimpleNamespace(name='', shapes=[], anchors=[])
        layer.addShape = layer.shapes.append
        return layer

    def new_glyph(self, name, names):
        layers = {}
        for layer_name in names:
            layer = self.new_layer()
            layer.name = layer_name
            layers[layer_name] = layer
        glyph = types.SimpleNamespace(name=name, layer=layers.get, layers=lambda: list(layers.values()),
                                      updateObject=Mock())
        glyph.fl = glyph
        glyph.addLayer = lambda layer, to_back: layers.update({layer.name: layer})
        glyph.addAnchor = lambda pos, anchor, layer: layers[layer].anchors.append((anchor, pos))
        self.glyphs[name] = glyph
        return glyph

    def test_empty_corners_anchors_binding_and_mapping_guard(self):
        name, plan = self.adapter.prepare_source(self.session, '막', 0, 'Thin')
        glyph = self.glyphs[name]
        self.assertTrue(plan['empty'])
        self.assertEqual(len(glyph.layers()), 4)
        for layer in glyph.layers():
            self.assertEqual(layer.shapes, [])
            self.assertEqual({a for a, _ in layer.anchors}, {'width', 'height'})
        self.assertEqual(self.session.sources[plan['key']], name)
        self.assertEqual(len(self.session.source_guides[name]['corners']), 4)
        self.assertEqual(glyph.note, format_source_note(self.session.source_guides[name]))
        self.assertIn('X 0 / Y 0', glyph.note)
        self.assertEqual(len(glyph.note.splitlines()), 7)
        with self.assertRaisesRegex(ValueError, '비어 있는'):
            self.adapter.source_layers(name, 'Thin')

    def test_existing_source_is_preserved(self):
        name, _ = self.adapter.prepare_source(self.session, '막', 0, 'Thin')
        existing = self.glyphs[name]
        existing.note = 'User design notes'
        with self.assertRaisesRegex(ValueError, '이미 있습니다'):
            self.adapter.prepare_source(self.session, '막', 0, 'Thin')
        self.assertIs(self.glyphs[name], existing)
        self.assertEqual(existing.note, 'User design notes')

    def test_existing_source_discovery_does_not_require_new_plan_or_modify_session(self):
        from HangulParametric.svc import source_name
        name=source_name('막',0,'Thin')
        self.glyphs[name]=object()
        self.session=Session()
        before=self.session.to_data()
        self.assertEqual(self.adapter.existing_source(self.session,'말',0,'Thin'),name)
        self.assertIsNone(self.adapter.existing_source(self.session,'목',0,'Thin'))
        self.assertEqual(self.session.to_data(),before)

    def test_existing_bound_source_precedes_generated_name(self):
        from HangulParametric.svc import source_name
        name=source_name('막',0,'Thin')
        self.glyphs[name]=object()
        self.glyphs['custom-source']=object()
        self.session.sources['0.6.H.closed']='custom-source'
        self.assertEqual(self.adapter.existing_source(self.session,'막',0,'Thin'),'custom-source')

    def test_legacy_name_is_not_replaced_by_readable_name(self):
        name = '_hp.{}.0.6.H.closed'.format(hashlib.sha1(b'Thin').hexdigest()[:8])
        self.glyphs[name] = object()
        with self.assertRaisesRegex(ValueError, '이미 있습니다'):
            self.adapter.prepare_source(self.session, '막', 0, 'Thin')
        self.assertEqual(list(self.glyphs), [name])

    def test_adapter_clones_each_planned_donor(self):
        self.session = Session()
        for char, width, height in [('막',100,200),('만',200,200),('말',100,300),('맘',200,300)]:
            box = dict(x=20,y=30,w=width,h=height)
            self.session.observations[char] = dict(glyphName=char, boxes=[box]*3, elementIndices=[[0],[1],[2]])
            rect = types.SimpleNamespace(x=lambda:20, y=lambda:30,
                                         width=lambda w=width:w, height=lambda h=height:h)
            transform = types.SimpleNamespace(mapRect=lambda r:r, isAffine=lambda:True,
                                              m11=lambda:1, m12=lambda:0, m21=lambda:0,
                                              m22=lambda:1, dx=lambda:0, dy=lambda:0)
            shape = types.SimpleNamespace(ensurePaths=lambda:None, boundingBox=rect, transform=transform,
                                          cloneTopLevel=lambda c=char:types.SimpleNamespace(donor=c))
            self.glyphs[char] = types.SimpleNamespace(shapes=lambda master,s=shape:[s,s,s])
        gui = type(self.adapter).prepare_source.__globals__['QtGui']
        with patch.object(gui, 'QTransform', lambda *args:args, create=True):
            name, plan = self.adapter.prepare_source(self.session, '막', 0, 'Thin')
        layers = self.glyphs[name].layers()
        self.assertEqual([l.shapes[0].donor for l in layers], ['막','만','말','맘'])
        self.assertEqual([c['copiedFrom'] for c in plan['guide']['corners']], ['막','만','말','맘'])
        self.assertEqual(self.glyphs[name].note, format_source_note(plan['guide']))
        self.assertNotIn('실제 복사 표본', self.glyphs[name].note)

    def test_refresh_updates_only_note_and_guide_preserving_layers(self):
        name, plan = self.adapter.prepare_source(self.session, '막', 0, 'Thin')
        glyph = self.glyphs[name]
        glyph.note = 'My notes\n' + glyph.note
        layers = glyph.layers()
        for layer in layers:
            layer.shapes.append(object())
        shapes = [list(layer.shapes) for layer in layers]
        self.session.observations['맘'] = {'boxes': [dict(x=0,y=0,w=300,h=400)]*3}
        self.adapter.refresh_source_guide(self.session, '막', 0, 'Thin')
        self.assertTrue(glyph.note.startswith('My notes\n'))
        self.assertIn('W 300 / H 400', glyph.note)
        self.assertEqual(glyph.layers(), layers)
        self.assertEqual([layer.shapes for layer in layers], shapes)
        self.assertNotEqual(self.session.source_guides[name], plan['guide'])

    def test_refresh_replaces_legacy_generated_note(self):
        name, plan = self.adapter.prepare_source(self.session, '막', 0, 'Thin')
        self.glyphs[name].note = format_source_guide(plan['guide'])
        self.adapter.refresh_source_guide(self.session, '막', 0, 'Thin')
        self.assertEqual(len(self.glyphs[name].note.splitlines()), 7)

    def test_creation_failure_removes_only_new_glyph_and_does_not_bind(self):
        original = self.new_glyph
        def fail_anchor(name, layers):
            glyph = original(name, layers)
            glyph.addAnchor = Mock(side_effect=RuntimeError('anchor failed'))
            return glyph
        self.adapter.font.newGlyph = fail_anchor
        before = self.session.to_data()
        with self.assertRaisesRegex(RuntimeError, 'anchor failed'):
            self.adapter.prepare_source(self.session, '막', 0, 'Thin')
        self.assertEqual(self.glyphs, {})
        self.assertEqual(self.session.to_data(), before)
