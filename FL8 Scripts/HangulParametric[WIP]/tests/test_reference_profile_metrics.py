import unittest

from HangulParametric.inference import RelationModel
from HangulParametric.metrics import metric_rows
from HangulParametric.model import Session, layout_run, visible_run
from HangulParametric.svc import map_reference, reference_target


def sample(width, x=20):
    return {'boxes': [dict(x=x, y=30, w=width, h=200) for _ in range(3)]}


class ReferenceProfileTests(unittest.TestCase):
    def model(self):
        return RelationModel({'악': sample(100), '안': sample(130), '알': sample(120),
                              '삭': sample(300, 50), '삮': sample(330, 57), '삯': sample(270, 45)}, 11)

    def test_missing_context_uses_contrast_not_donor_box(self):
        model = self.model()
        result = model.predict('맊')
        self.assertEqual(result['boxes'][0]['w'], 110)
        self.assertEqual(result['boxes'][0]['x'], 27)
        self.assertEqual(result['referenceChar'], '앆')
        self.assertEqual(result['basis'], 'unverified')
        self.assertEqual(result['evidence'][0]['pairs'], [['삭', '악']])
        self.assertEqual(model.predict('맋')['boxes'][0]['w'], 90)
        self.assertEqual(model.predict('막')['normalized'][0]['w'], .25)
        self.assertEqual(result['normalized'][0]['w'], .5)

    def test_fixed_reference_no_unanchored_or_recursive_transfer(self):
        model = RelationModel({'악': sample(100), '안': sample(120),
                               '삮': sample(300), '손': sample(400)}, 11)
        self.assertIsNone(model.predict('맊'))
        self.assertIsNone(model.predict('몬'))
        self.assertEqual(model.predict('막')['referenceInitial'], 11)

    def test_filter_and_prediction_order_do_not_change_ranges(self):
        model = self.model()
        first = model.predict('막')
        model.predict('맋')
        self.assertEqual(first, model.predict('막'))
        reverse = RelationModel(dict(reversed(list(model.observations.items()))), 11)
        self.assertEqual(first, reverse.predict('막'))

    def test_supported_mapping_uses_validation(self):
        data = {'악': sample(100), '안': sample(120), '알': sample(140),
                '삭': sample(300), '산': sample(320), '살': sample(340), '삮': sample(330)}
        result = RelationModel(data, 11).predict('맊')
        self.assertEqual(result['boxes'][0]['w'], 130)
        self.assertEqual(result['basis'], 'calibrated')

    def test_svc_size_comes_from_target_source_and_unit_correction(self):
        evaluate = lambda u, v: dict(x=0, y=0, w=500+u*.2, h=300+v*.1)
        session = Session()
        session.predictions['맊'] = self.model().predict('맊')
        base = session.box('맊', 0)
        ratios, delta = reference_target(session, '맊', 0)
        mapped = map_reference(base, ratios, delta, evaluate)
        self.assertEqual(mapped['location']['width'], 500)
        self.assertEqual(mapped['target']['w'], 600)
        self.assertEqual(mapped['target']['x'], 27)
        session.set_box('맊', 0, dict(base, w=base['w']+10))
        ratios, delta = reference_target(session, '맊', 0)
        mapped = map_reference(session.box('맊', 0), ratios, delta, evaluate)
        self.assertAlmostEqual(mapped['target']['w'], 610)

    def test_metric_rows_distinguish_units_and_proportions(self):
        session = Session()
        session.predictions['맊'] = self.model().predict('맊')
        rows = dict(metric_rows(session, '맊', 0, 0))
        self.assertEqual(rows['W'], '50.0%')
        self.assertEqual(rows['상태'], '검증 부족')
        self.assertEqual(dict(metric_rows(session, '맊', 0, 1))['상태'], '관계 참고')
        preview = dict(session.box('맊', 0), x=37)
        self.assertEqual(dict(metric_rows(session, '맊', 0, 2, preview))['ΔX'], '+10')
        self.assertEqual(metric_rows(session, '마', 2, 0), [('상태', '역할 없음')])

    def test_metrics_take_row_space_and_remain_visible_below_glyph(self):
        items, height = layout_run('막먁', 100, 0, extra_height=100)
        self.assertEqual(items[1][2]-items[0][2], 245)
        self.assertEqual(visible_run(items, 180, 30, 100, extra_height=100), [('막', 16, -156)])
