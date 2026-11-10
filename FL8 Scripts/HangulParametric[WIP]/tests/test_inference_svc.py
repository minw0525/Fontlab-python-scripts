import unittest

from HangulParametric.model import Session, layout_run, visible_run
from HangulParametric.inference import RelationModel, source_key
from HangulParametric.svc import solve_location, source_plan


def char(a, v, f):
    return chr(0xAC00 + a*588 + v*28 + f)


def record(f, shift=0):
    return {'boxes': [dict(x=10+shift, y=200, w=300, h=450-f*5),
                      dict(x=400, y=200, w=150, h=500-f*5),
                      dict(x=100, y=0, w=450, h=100+f*5)]}


class InferenceTests(unittest.TestCase):
    def test_transfer_preserves_observed_and_all_three_parts(self):
        s = Session()
        for f in (1, 4, 8, 16):
            s.observations[char(11, 0, f)] = record(f)
            if f != 16:
                s.observations[char(6, 0, f)] = record(f, 10)
        predicted = RelationModel(s.observations).predict(char(6, 0, 16))
        self.assertEqual(predicted['boxes'], record(16, 10)['boxes'])
        self.assertTrue(predicted['evidence'])
        self.assertNotIn(char(6, 0, 16), s.observations)

    def test_no_single_final_fallback_or_cross_layout(self):
        observations = {char(11, 0, 1): record(1), char(6, 0, 1): record(1)}
        self.assertIsNone(RelationModel(observations).predict(char(6, 0, 27)))
        self.assertIsNone(RelationModel(observations).predict(char(6, 8, 1)))

    def test_no_training_on_predictions_and_round_trip_deltas(self):
        s = Session()
        c = char(6, 0, 16)
        s.predictions[c] = dict(boxes=record(16)['boxes'], evidence=[])
        base = s.base_box(c, 0)
        s.set_box(c, 0, dict(base, w=base['w']+10))
        loaded = Session.from_data(s.to_data())
        self.assertEqual(loaded.base_box(c, 0), base)
        self.assertEqual(loaded.box(c, 0)['w'], base['w']+10)
        self.assertIsNone(RelationModel(s.observations).predict(c))

    def test_source_family_is_role_specific(self):
        self.assertEqual(source_key('악', 2), source_key('약', 2))
        self.assertNotEqual(source_key('악', 2), source_key('옥', 2))
        self.assertNotEqual(source_key('악', 1), source_key('약', 1))

    def test_corner_guides_have_independent_extremes(self):
        s = Session()
        s.observations = {'악': record(1), '안': record(4)}
        plan = source_plan(s, '악', 0)
        self.assertEqual(plan['corners'][0]['box']['h'], 430)
        self.assertEqual(plan['corners'][2]['box']['h'], 445)
        self.assertEqual(len(plan['corners']), 4)


class LocationTests(unittest.TestCase):
    def test_fontlab_integer_boxes_do_not_stall_the_solver(self):
        def evaluate(u, v):
            self.assertTrue(0 <= u <= 1000 and 0 <= v <= 1000)
            return dict(x=0, y=0, w=round(313+.021*u), h=round(320+.04*v))
        for height in (337,343,360):
            result=solve_location(dict(x=20,y=325,w=334,h=height),evaluate)
            self.assertLessEqual(result['error'],1)
            self.assertEqual(result['box']['h'],height)

    def test_coupled_axes_and_nonzero_origin(self):
        def evaluate(u, v):
            return dict(x=10+u/100, y=-20+v/100, w=100+.2*u+.02*v, h=200+.03*u+.4*v)
        target = evaluate(300, 600)
        target.update(x=80, y=250)
        result = solve_location(target, evaluate)
        self.assertEqual(result['location'], dict(width=300, height=600))
        self.assertEqual(result['delta'], dict(x=67, y=264))

    def test_constant_width_axis(self):
        evaluate = lambda u, v: dict(x=0, y=0, w=100, h=200+.4*v)
        result = solve_location(dict(x=30, y=40, w=100, h=400), evaluate)
        self.assertEqual(result['location']['height'], 500)

    def test_unreachable_target_is_not_clamped_and_applied(self):
        evaluate = lambda u, v: dict(x=0, y=0, w=100+.1*u, h=200+.1*v)
        with self.assertRaises(ValueError):
            solve_location(dict(x=0, y=0, w=500, h=300), evaluate)

    def test_advance_width_controls_positions_and_culling(self):
        widths = {'악': 70, '안': 60, '알': 120}
        items, _ = layout_run('악안알', 100, 0, widths)
        self.assertEqual([x for _, x, _ in items], [16, 86, 146])
        self.assertEqual(visible_run(items, 0, 200, 100, 230, 20, widths), [('알', -84, 24)])


if __name__ == '__main__':
    unittest.main()
