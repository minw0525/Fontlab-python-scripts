import types
import unittest
from unittest.mock import Mock, patch

from test_master_recovery import adapter_class
from HangulParametric.model import Session


BOX = dict(x=10, y=20, w=100, h=200)


class Shape:
    def __init__(self, tag):
        self.tag = tag
        self.isComponent = tag == 'svc'
        self.shapeData = types.SimpleNamespace(componentGlyph='source', componentLayer='Thin#width=500,height=500')
        self.boundingBox = types.SimpleNamespace(**{k: (lambda v=v: v) for k, v in
                                                   zip(('x', 'y', 'width', 'height'), BOX.values())})
        self.transform = types.SimpleNamespace(mapRect=lambda r: r)

    def cloneTopLevel(self):
        return Shape(self.tag)

    def ensurePaths(self):
        pass

    def update(self):
        pass


class Layer:
    def __init__(self, shapes=()):
        self.shapes = list(shapes)
        self.autoLayer = False
        self.recipe = ''
        self.advanceWidth = 700
        self.mask = None

    def addShape(self, shape):
        self.shapes.append(shape)
        return shape

    def insertShape(self, index, shape):
        self.shapes.insert(index, shape)
        return shape

    def removeShape(self, shape, recursive=False):
        self.shapes.remove(shape)

    def getMaskLayer(self, create):
        if self.mask is None and create:
            self.mask = Layer()
        return self.mask


class RoleReplacementTests(unittest.TestCase):
    def setUp(self):
        cls = adapter_class()
        self.adapter = cls.__new__(cls)
        self.adapter.names = {'맘': 'uniB9D8'}
        self.adapter.require_master = Mock()
        self.adapter.source_layers = Mock()
        self.adapter.map_component = Mock(side_effect=lambda *args: (Shape('svc'), {
            'target': BOX, 'location': dict(width=500, height=500)}))
        self.adapter.shape_path = Mock(return_value=types.SimpleNamespace(isEmpty=lambda: False))
        self.layer = Layer([Shape('first'), Shape('vowel'), Shape('final')])
        self.layer.getMaskLayer(True).addShape(Shape('old-mask'))
        self.glyph = types.SimpleNamespace(layer=lambda _: self.layer, updateObject=Mock())
        self.glyph.fl = self.glyph
        self.adapter.font = types.SimpleNamespace(hasGlyph=lambda n: n == 'uniB9D8',
                                                  glyph=lambda n: self.glyph, update=Mock(), newGlyph=Mock())
        self.adapter.package = types.SimpleNamespace(deleteGlyph=Mock())
        self.session = Session()
        self.session.observations = {'암': {'boxes': [dict(BOX) for _ in range(3)]}}
        self.session.managed_components = {'맘': {str(r): 'source' for r in range(3)}}
        self.mapping = patch('HangulParametric.svc.source_mapping', return_value=(BOX, None, None, {}))
        self.mapping.start()
        self.addCleanup(self.mapping.stop)

    def apply(self, role):
        return self.adapter.derive_role(self.session, '맘', role, 'source', 'Thin')

    def test_samples_never_apply_even_with_management_record(self):
        self.session.observations['맘'] = self.session.observations['암']
        self.session.sources['0.6.H.closed'] = 'source'
        original = list(self.layer.shapes)
        for operation in (lambda: self.apply(0),
                          lambda: self.adapter.derive_role(self.session,'맘',0,'source','Thin',update_only=True),
                          lambda: self.adapter.recalculate_applied(self.session,'Thin'),
                          lambda: self.adapter.apply_empty(self.session,'맘','Thin')):
            done, skipped = operation()[:2]
            self.assertFalse(done)
            self.assertEqual(skipped, [('맘','실측 표본 원본 보존')])
            self.assertEqual(self.layer.shapes, original)
            self.assertEqual(len(self.layer.mask.shapes),1)
        self.adapter.map_component.assert_not_called()

    def test_recalculate_bound_components_without_mask_growth(self):
        self.session.sources['0.6.H.closed'] = 'source'
        original = Shape('svc')
        self.layer.shapes[0] = original
        for loc in (250, 750):
            replacement = Shape('svc')
            replacement.shapeData.componentLayer = '#width={},height=500'.format(loc)
            self.adapter.map_component.side_effect = None
            self.adapter.map_component.return_value = (replacement, {
                'target': BOX, 'location': dict(width=loc,height=500)})
            done, skipped, _ = self.adapter.recalculate_applied(self.session, 'Thin')
            self.assertEqual(done, [('맘','uniB9D8')])
            self.assertFalse(skipped)
            self.assertIs(self.layer.shapes[0], original)
            self.assertEqual(original.shapeData.componentLayer, replacement.shapeData.componentLayer)
            self.assertEqual(len(self.layer.mask.shapes), 1)

    def test_legacy_bound_svc_updates_and_records_management(self):
        self.session.managed_components.clear()
        self.session.sources['0.6.H.closed'] = 'source'
        old = Shape('svc')
        old.shapeData.componentLayer = '#width=10,height=20'
        self.layer.shapes[0] = old
        done, skipped, _ = self.adapter.recalculate_applied(self.session,'Thin')
        self.assertTrue(done)
        self.assertFalse(skipped)
        self.assertIs(self.layer.shapes[0],old)
        self.assertEqual(old.shapeData.componentLayer,'Thin#width=500,height=500')
        self.assertEqual(self.session.managed_components['맘']['0'],'source')
        self.assertEqual(len(self.layer.mask.shapes),1)

    def test_unregistered_unbound_component_is_not_adopted(self):
        self.session.managed_components.clear()
        self.layer.shapes[0] = Shape('svc')
        self.assertFalse(self.apply(0)[0])
        self.assertFalse(self.session.managed_components)
        self.adapter.map_component.assert_not_called()

    def test_recalculate_does_not_insert_missing_components(self):
        self.session.sources['0.6.H.closed'] = 'source'
        original = list(self.layer.shapes)
        done, skipped, _ = self.adapter.recalculate_applied(self.session, 'Thin')
        self.assertFalse(done)
        self.assertTrue(skipped)
        self.assertEqual(self.layer.shapes, original)
        self.assertEqual(len(self.layer.mask.shapes), 1)

    def test_unmanaged_contours_preserved_for_every_role(self):
        self.session.managed_components.clear()
        for role in range(3):
            self.layer.shapes = [Shape('first'), Shape('vowel'), Shape('final')]
            before = list(self.layer.shapes)
            mask_count = len(self.layer.mask.shapes)
            applied, skipped, _ = self.apply(role)
            self.assertFalse(applied)
            self.assertIn('미관리', skipped[0][1])
            for i in range(3):
                if i != role:
                    self.assertIs(self.layer.shapes[i], before[i])
            self.assertIs(self.layer.shapes[role], before[role])
            self.assertEqual(len(self.layer.mask.shapes), mask_count)
            self.assertEqual(self.layer.mask.shapes[0].tag, 'old-mask')
            self.assertEqual(self.layer.advanceWidth, 700)
        self.adapter.font.newGlyph.assert_not_called()

    def test_grouped_vowel_contours_are_not_replaced(self):
        self.session.grouped_vowel = True
        self.layer.shapes.insert(2, Shape('vowel-stem'))
        for _ in range(2):
            applied, skipped, _ = self.apply(1)
            self.assertFalse(applied)
            self.assertTrue(skipped)
            self.assertEqual([s.tag for s in self.layer.shapes], ['first', 'vowel', 'vowel-stem', 'final'])
        self.assertEqual([s.tag for s in self.layer.mask.shapes], ['old-mask'])

    def test_same_source_updates_in_place_without_backup(self):
        svc=Shape('svc');svc.shapeData.componentLayer='Thin#width=0,height=0'
        self.layer.shapes[0]=svc
        applied,skipped,_=self.apply(0)
        self.assertTrue(applied);self.assertFalse(skipped)
        self.assertIs(self.layer.shapes[0],svc)
        self.assertEqual(svc.shapeData.componentLayer,'Thin#width=500,height=500')
        self.assertEqual(len(self.layer.mask.shapes),1)
        self.assertEqual(self.adapter.apply_reports['맘']['backedUp'],0)
        self.assertTrue(self.adapter.apply_reports['맘']['updated'])

    def test_failed_update_restores_location_without_replacing_object(self):
        svc=Shape('svc');svc.shapeData.componentLayer='Thin#width=0,height=0'
        self.layer.shapes[0]=svc
        self.adapter.shape_path.return_value.isEmpty=lambda:True
        self.assertFalse(self.apply(0)[0])
        self.assertIs(self.layer.shapes[0],svc)
        self.assertEqual(svc.shapeData.componentLayer,'Thin#width=0,height=0')
        self.assertEqual(len(self.layer.mask.shapes),1)

    def test_update_only_never_replaces_contours_or_other_sources(self):
        for shape in (Shape('first'),Shape('svc')):
            shape.shapeData.componentGlyph='different-source'
            self.layer.shapes[0]=shape
            result=self.adapter.derive_role(self.session,'맘',0,'source','Thin',update_only=True)
            self.assertFalse(result[0]);self.assertTrue(result[1])
            self.assertIs(self.layer.shapes[0],shape)
        self.adapter.map_component.assert_not_called()

    def test_different_source_is_backed_up_and_replaced(self):
        svc=Shape('svc');svc.shapeData.componentGlyph='different-source'
        self.session.managed_components['맘']['0'] = 'different-source'
        self.layer.shapes[0]=svc
        self.assertTrue(self.apply(0)[0])
        self.assertIsNot(self.layer.shapes[0],svc)
        self.assertEqual(len(self.layer.mask.shapes),2)

    def test_post_insert_failure_restores_foreground_and_mask(self):
        self.layer.shapes[0] = Shape('svc')
        self.layer.shapes[0].shapeData.componentGlyph = 'old-source'
        self.session.managed_components['맘']['0'] = 'old-source'
        self.adapter.shape_path.return_value.isEmpty = lambda: True
        applied, skipped, _ = self.apply(0)
        self.assertFalse(applied)
        self.assertTrue(skipped)
        self.assertEqual([s.tag for s in self.layer.shapes], ['svc', 'vowel', 'final'])
        self.assertEqual(self.session.managed_components['맘']['0'],'old-source')
        self.assertEqual([s.tag for s in self.layer.mask.shapes], ['old-mask'])

    def test_partial_mask_failure_does_not_lose_original(self):
        self.layer.shapes[0] = Shape('svc')
        self.layer.shapes[0].shapeData.componentGlyph = 'old-source'
        self.session.managed_components['맘']['0'] = 'old-source'
        original = self.layer.mask.addShape
        def fail(shape):
            original(shape)
            raise RuntimeError('backup failed')
        self.layer.mask.addShape = fail
        applied, skipped, _ = self.apply(0)
        self.assertFalse(applied)
        self.assertTrue(skipped)
        self.assertEqual([s.tag for s in self.layer.shapes], ['svc', 'vowel', 'final'])
        self.assertEqual([s.tag for s in self.layer.mask.shapes], ['old-mask'])

    def test_invalid_roles_and_recipe_do_not_touch_font(self):
        self.layer.shapes.append(Shape('extra'))
        self.assertFalse(self.apply(0)[0])
        self.layer.shapes.pop()
        self.layer.autoLayer = True
        self.assertFalse(self.apply(0)[0])
        self.assertEqual([s.tag for s in self.layer.mask.shapes], ['old-mask'])
        self.adapter.map_component.assert_not_called()

    def test_empty_existing_target_is_filled_without_mask_or_extra_result(self):
        donor = types.SimpleNamespace(shapes=lambda _: [Shape('first'), Shape('vowel'), Shape('final')])
        self.session.observations['암'].update(glyphName='donor', elementIndices=[[0], [1], [2]])
        self.adapter.font.glyph = lambda n: donor if n == 'donor' else self.glyph
        self.layer.shapes = []
        applied, skipped, _ = self.apply(1)
        self.assertTrue(applied)
        self.assertFalse(skipped)
        self.assertEqual([s.tag for s in self.layer.shapes], ['first', 'svc', 'final'])
        self.assertEqual(self.session.managed_components['맘']['1'],'source')
        self.assertEqual([s.tag for s in self.layer.mask.shapes], ['old-mask'])
        self.adapter.font.newGlyph.assert_not_called()

    def test_empty_target_failure_restores_empty_foreground(self):
        donor = types.SimpleNamespace(shapes=lambda _: [Shape('first'), Shape('vowel'), Shape('final')])
        self.session.observations['암'].update(glyphName='donor', elementIndices=[[0], [1], [2]])
        self.adapter.font.glyph = lambda n: donor if n == 'donor' else self.glyph
        self.layer.shapes = []
        self.adapter.shape_path.return_value.isEmpty = lambda: True
        self.assertFalse(self.apply(1)[0])
        self.assertEqual(self.layer.shapes, [])
        self.assertEqual([s.tag for s in self.layer.mask.shapes], ['old-mask'])
