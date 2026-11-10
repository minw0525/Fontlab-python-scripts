import types
import unittest

from test_master_recovery import adapter_class


class Path:
    def __init__(self, points=()):
        self.points = list(points)

    def addPath(self, other):
        self.points.extend(other.points)

    def isEmpty(self):
        return not self.points


def shape(points=(), children=(), dx=0, dy=0, scale=1):
    transform = types.SimpleNamespace(map=lambda p: Path(
        [(x * scale + dx, y * scale + dy) for x, y in p.points]))
    return types.SimpleNamespace(isComponent=bool(children), includesList=children,
                                 closedPath=Path(points), transform=transform,
                                 ensurePaths=lambda: None)


class ComponentPathTests(unittest.TestCase):
    def setUp(self):
        self.adapter = adapter_class()
        self.adapter.shape_path.__globals__['QtGui'].QPainterPath = Path

    def test_plain_shape_transform(self):
        self.assertEqual(self.adapter.shape_path(shape([(1, 2)], dx=10)).points, [(11, 2)])

    def test_empty_component_path_uses_nested_outlines_and_each_transform_once(self):
        leaf = shape([(1, 2), (4, 6)], dx=-1, dy=-2)
        nested = shape(children=[leaf], scale=2)
        component = shape(children=[nested, shape([(0, 0)])], dx=51, dy=378)
        self.assertEqual(component.closedPath.points, [])
        self.assertEqual(self.adapter.shape_path(component).points,
                         [(51, 378), (57, 386), (51, 378)])

    def test_display_outline_reads_unclassified_components_without_measurement(self):
        adapter = self.adapter.__new__(self.adapter)
        adapter.names = {'먹': 'uniBA39'}
        layer = types.SimpleNamespace(shapes=[shape(children=[shape([(1,2)])],dx=10),shape([(3,4)])])
        adapter.font = types.SimpleNamespace(glyph=lambda _: types.SimpleNamespace(layer=lambda master: layer if master=='Thin' else None))
        self.assertEqual(adapter.display_outline('먹','Thin').points,[(11,2),(3,4)])
        self.assertIsNone(adapter.display_outline('멀','Thin'))
        self.assertIsNone(adapter.display_outline('먹','Bold'))
        layer.shapes=[]
        self.assertIsNone(adapter.display_outline('먹','Thin'))
