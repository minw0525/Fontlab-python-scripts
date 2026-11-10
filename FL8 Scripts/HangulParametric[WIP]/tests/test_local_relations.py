import unittest
from HangulParametric.mieum_relations import estimate
from HangulParametric.local_relations import local_transfer
from HangulParametric.svc import solve_location, source_mapping
from HangulParametric.model import Session
from HangulParametric.metrics import metric_rows


def record(w, h=100, x=0, y=0):
    return {'boxes': [dict(w=w,h=h,x=x,y=y) for _ in range(3)]}


class LocalTransferTests(unittest.TestCase):
    def test_consonants_prefer_same_initial_and_final_vowels_keep_same_vowel(self):
        data = {c: record(w) for c,w in [('반',200),('뱜',200),('뱔',200),
                                       ('안',100),('얀',100),('얌',100),('얄',100)]}
        for role in (0,2):
            result = estimate(data,'뱐',role,11)
            self.assertEqual(result['anchors'],['반'])
            self.assertEqual(result['pairs'],[('안','얀')])
            self.assertEqual(result['changedAxis'],1)
            self.assertEqual(result['box']['w'],200)
        result = estimate(data,'뱐',1,11)
        self.assertIn(result['anchors'][0],('뱜','뱔'))
        self.assertEqual(result['changedAxis'],2)

    def test_one_pair_preferred_vowel_path_discloses_limited_validation(self):
        data = {'반':record(200),'안':record(100),'얀':record(110)}
        for role in (0,2):
            result = estimate(data,'뱐',role,11)
            self.assertEqual(result['box']['w'],220)
            self.assertEqual(result['support'],1)
            self.assertIsNone(result['validationError'])

    def test_priority_does_not_hide_conflicting_valid_path(self):
        data = {c:record(w) for c,w in [('반',240),('뱜',200),('뱔',200),
                                      ('안',100),('얀',100),('얌',100),('얄',100)]}
        result = estimate(data,'뱐',0,11)
        self.assertEqual(result['anchors'],['반'])
        self.assertEqual(result['box']['w'],240)
        self.assertTrue(result['conflicts'])
        s = Session(); s.observations = data
        mapped, _, _, provenance = source_mapping(s,'뱐',0)
        self.assertEqual(mapped['w'],240)
        self.assertEqual(provenance['anchors'],['반'])
        self.assertTrue(provenance['conflicts'])
        self.assertIn(('상태','우선 추론·충돌'),metric_rows(s,'뱐',0,0,strict_closed=True))

    def test_source_extrema_change_requires_new_location_for_same_target(self):
        target = dict(x=30,y=40,w=150,h=250)
        def evaluate(span):
            return lambda u,v: dict(x=5,y=10,w=100+span*u/1000,h=200+100*v/1000)
        old = solve_location(target,evaluate(100))
        new = solve_location(target,evaluate(200))
        self.assertEqual(old['location']['width'],500)
        self.assertEqual(new['location']['width'],250)
        self.assertEqual(new['delta'],dict(x=25,y=30))

    def test_local_final_changes_override_distant_mieum_baseline(self):
        data = {c:record(w) for c,w in [('볼',200),('볽',200),('올',100),('옭',100),
                                       ('옮',100),('옯',100),('봄',400),('옴',300)]}
        for char in ('볾','볿'):
            result = estimate(data,char,0,11)
            self.assertEqual(result['mode'],'local-transfer')
            self.assertEqual(result['box']['w'],200)
            self.assertIn(result['anchors'][0],('볼','볽'))
            self.assertEqual(result['support'],2)

    def test_generalizes_vowel_and_initial_changes(self):
        # Vowel changes affect the same initial; initial changes affect a vowel.
        for data, target, role in [
            ({'감':record(200),'검':record(160),'암':record(100),'엄':record(80),'임':record(70)},'김',0),
            ({'감':record(200),'남':record(160),'검':record(100),'넘':record(80),'덤':record(70)},'담',1)]:
            result = local_transfer(data,target,role)
            self.assertIsNotNone(result)
            self.assertEqual(result['box']['w'],140)

    def test_conflicting_candidates_are_not_averaged(self):
        data = {c:record(w) for c,w in [('볼',200),('볽',200),('올',100),('옭',100),('옮',100),
                                       ('골',100),('곩',100),('곪',150)]}
        result = estimate(data,'볾',0,11)
        self.assertTrue(result['conflicts'])
        self.assertIn(result['box']['w'],(200,300))

    def test_one_pair_and_inconsistent_pairs_cannot_claim_local_support(self):
        for data in [
            {'볼':record(200),'올':record(100),'옮':record(100)},
            {'볼':record(200),'볽':record(300),'올':record(100),'옭':record(100),'옮':record(100)}]:
            self.assertIsNone(local_transfer(data,'볾',0))

    def test_observed_wins_and_layout_does_not_cross(self):
        data = {'볼':record(200),'볽':record(200),'알':record(100),'앍':record(100),'앎':record(100)}
        self.assertIsNone(local_transfer(data,'볾',0))
        data['볾'] = record(350)
        self.assertEqual(estimate(data,'볾',0)['box']['w'],350)

    def test_position_uses_delta_not_size_ratio(self):
        data = {'볼':record(200,x=30),'볽':record(200,x=32),
                '올':record(100,x=10),'옭':record(100,x=12),'옮':record(100,x=15)}
        self.assertEqual(estimate(data,'볾',0)['box']['x'],35)
