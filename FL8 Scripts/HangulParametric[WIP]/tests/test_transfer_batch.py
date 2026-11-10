import unittest

from HangulParametric.inference import RelationModel
from HangulParametric.model import Session


def record(width=100):
    return {'boxes': [dict(x=10, y=20, w=width, h=200) for _ in range(3)]}


class TransferBatchTests(unittest.TestCase):
    def test_reference_without_target_samples(self):
        model = RelationModel({'악': record(100), '안': record(200)})
        result = model.predict('막')
        self.assertEqual(result['mode'], 'reference')
        self.assertEqual(result['evidence'][0]['donor'], '악')
        self.assertEqual(result['normalized'][0], {'w': 0, 'h': None})
        self.assertIsNone(model.predict('목'))
        self.assertIsNone(model.predict('마'))

    def test_ranking_and_explicit_reference(self):
        data = {'악': record(), '안': record(), '박': record(150)}
        self.assertEqual(RelationModel(data).predict('막')['evidence'][0]['donor'], '악')
        self.assertEqual(RelationModel(data, 7).predict('막')['evidence'][0]['donor'], '박')
        inferred = RelationModel(data, 7).predict('만')
        self.assertEqual(inferred['referenceChar'], '반')
        self.assertEqual(inferred['basis'], 'unverified')

    def test_reference_roundtrip_and_state(self):
        session = Session()
        session.reference_initial = 11
        session.predictions['막'] = RelationModel({'악': record()}).predict('막')
        restored = Session.from_data(session.to_data())
        self.assertEqual(restored.reference_initial, 11)
        self.assertEqual(restored.state('막'), '기준 전이·미보정')

    def test_preview_atomic_apply_and_undo_preserve_prior_overrides(self):
        session = Session()
        session.observations = {'악': record(), '박': record(150)}
        session.set_box('악', 0, dict(x=30, y=20, w=100, h=200))
        before = session.to_data()
        pending, skipped = session.preview_batch(['악', '박', '막'], 0, dict(x=10, y=0, w=5, h=0))
        self.assertEqual(session.to_data(), before)
        self.assertEqual(skipped, ['막'])
        self.assertEqual(pending['악']['x'], 40)
        self.assertEqual(pending['박']['x'], 20)
        session.commit_batch(pending, 0)
        session.undo_batch()
        self.assertEqual(session.to_data(), before)
        with self.assertRaises(ValueError):
            session.preview_batch(['악', '박'], 0, dict(x=0, y=0, w=-110, h=0))
        self.assertEqual(session.to_data(), before)

    def test_undo_does_not_overwrite_later_edit(self):
        session = Session()
        session.observations = {'악': record()}
        pending, _ = session.preview_batch(['악'], 0, dict(x=1, y=0, w=0, h=0))
        session.commit_batch(pending, 0)
        session.set_box('악', 0, dict(x=50, y=20, w=100, h=200))
        with self.assertRaises(ValueError):
            session.undo_batch()
