import unittest

from HangulParametric.model import Session
from HangulParametric.inference import source_key
from HangulParametric.mieum_relations import baseline, estimate, guide_records
from HangulParametric.svc import source_mapping, source_design_guide
from HangulParametric.metrics import metric_rows


def record(w, h, x=10, y=20):
    return dict(boxes=[dict(x=x, y=y, w=w, h=h) for _ in range(3)])


class MieumRelationTests(unittest.TestCase):
    def test_fixed_baselines_for_three_roles(self):
        self.assertEqual([baseline('각',r) for r in range(3)], ['감','맘','막'])
        self.assertIsNone(baseline('가',0))

    def test_initial_uses_final_mieum_pair(self):
        data={'암':record(100,100),'악':record(120,130,15,25),'맘':record(300,400)}
        r=estimate(data,'막',0,11)
        self.assertEqual(r['box'],dict(x=15,y=25,w=360,h=520))
        self.assertEqual(r['pairs'],[('암','악')])

    def test_final_uses_initial_mieum_and_same_final_design(self):
        data={'맘':record(100,100),'감':record(120,130),'막':record(300,400)}
        r=estimate(data,'각',2)
        self.assertEqual(r['box']['h'],520)
        self.assertEqual(r['anchors'],['막'])
        self.assertEqual(r['pairs'],[('맘','감')])

    def test_vowel_uses_mieum_frame_for_both_effects(self):
        data={'맘':record(100,100),'감':record(120,130),'막':record(150,160)}
        r=estimate(data,'각',1)
        self.assertEqual(r['box']['w'],180)
        self.assertEqual(r['box']['h'],208)
        self.assertEqual(r['anchors'],['맘'])

    def test_missing_reference_pair_cannot_use_predicted_or_other_final(self):
        data={'안':record(100,100),'악':record(120,130),'맘':record(300,400)}
        with self.assertRaisesRegex(ValueError,'암'):
            estimate(data,'막',0,11)

    def test_mixed_shapes_cannot_supply_horizontal_baseline(self):
        data={'암':record(100,100),'악':record(120,130),'뫔':record(300,400),'뭼':record(400,500)}
        with self.assertRaisesRegex(ValueError,'맘'):
            estimate(data,'막',0,11)
        s=Session();s.observations=data;s.reference_initial=11
        guide=source_design_guide(s,'막',0)
        self.assertEqual(guide['designs'],[])
        self.assertTrue(guide['missing'])
        self.assertNotEqual(source_key('맘',2),source_key('뫔',2))

    def test_open_syllables_never_enter_closed_model(self):
        with self.assertRaisesRegex(ValueError,'민글자'):
            estimate({'맘':record(100,100)},'마',0)

    def test_vowel_specific_mieum_frame_cannot_be_replaced(self):
        data={'암':record(100,100),'악':record(120,130),'맴':record(300,400)}
        with self.assertRaisesRegex(ValueError,'맘'):
            estimate(data,'막',0,11)

    def test_closed_metrics_show_missing_instead_of_old_reference(self):
        s=Session();s.observations={'암':record(100,100),'악':record(120,130)};s.infer()
        self.assertEqual(metric_rows(s,'막',0,0,strict_closed=True),[('상태','근거 부족')])

    def test_mapping_works_without_old_predictions(self):
        s=Session();s.reference_initial=11
        s.observations={'암':record(100,100),'악':record(120,130),'맘':record(300,400)}
        self.assertEqual(source_mapping(s,'막',0)[0]['h'],520)

    def test_reference_syllables_and_mam_support_all_three_roles(self):
        data={'암':record(100,100),'악':record(120,130,15,25),'맘':record(300,400)}
        for role in range(3):
            r=estimate(data,'막',role,11)
            self.assertEqual(r['box'],dict(x=15,y=25,w=360,h=520))
            if role:
                self.assertEqual(r['anchors'],['악'])
                self.assertEqual(r['pairs'],[('암','맘')])

    def test_transfer_still_requires_same_vowel_and_final_mieum_pair(self):
        for missing in ('암','맘','악'):
            data={'암':record(100,100),'악':record(120,130),'맘':record(300,400),
                  '옴':record(100,100),'옥':record(120,130),'몸':record(300,400)}
            del data[missing]
            for role in (1,2):
                with self.assertRaises(ValueError):
                    estimate(data,'막',role,11)

    def test_transfer_preserves_measured_target(self):
        data={'암':record(100,100),'악':record(120,130),'맘':record(300,400),
              '막':record(500,600)}
        self.assertEqual(estimate(data,'막',2,11)['box']['h'],600)

    def test_other_vowel_uses_measured_change_not_reference_absolute_size(self):
        data={'암':record(100,100),'맘':record(300,400),
              '억':record(80,120,15,25),'얼':record(90,110,20,30)}
        for role in range(3):
            r=estimate(data,'먹',role,11)
            self.assertEqual(r['box'],dict(x=15,y=25,w=240,h=480))
            self.assertTrue(r['crossVowel'])
            self.assertEqual(estimate(data,'멀',role,11)['box']['w'],270)
        self.assertEqual(estimate(data,'먹',0,11)['pairs'],[('암','억')])
        self.assertEqual(estimate(data,'먹',1,11)['pairs'],[('암','맘')])

    def test_same_vowel_calibration_takes_priority_and_measured_target_wins(self):
        data={'암':record(100,100),'맘':record(300,400),
              '엄':record(80,100),'멈':record(200,300),'억':record(80,120)}
        self.assertEqual(estimate(data,'먹',0,11)['box']['w'],200)
        data['먹']=record(210,350)
        for role in range(3):
            self.assertEqual(estimate(data,'먹',role,11)['mode'],'observed')

    def test_cross_vowel_requires_real_pair_and_target_donor(self):
        for missing in ('암','맘','억'):
            data={'암':record(100,100),'맘':record(300,400),'억':record(80,120)}
            del data[missing]
            for role in range(3):
                with self.assertRaises(ValueError):
                    estimate(data,'먹',role,11)

    def test_corner_minimum_includes_other_vowels_and_is_selection_independent(self):
        s=Session();s.reference_initial=11
        s.observations={'암':record(100,100),'맘':record(300,400),
                        '악':record(100,120),'억':record(80,120),'역':record(80,110)}
        guides=[source_design_guide(s,c,0) for c in ('막','먹')]
        self.assertEqual(guides[0]['corners'],guides[1]['corners'])
        minimum={r['char'] for r in guides[0]['corners'][0]['widthTargets']}
        self.assertEqual(minimum,{'먹','멱'})
        self.assertEqual(guides[0]['recommendedRanges']['w'][0],240)

    def test_cross_vowel_metrics_disclose_transfer(self):
        s=Session();s.reference_initial=11
        s.observations={'암':record(100,100),'맘':record(300,400),'억':record(80,120)}
        self.assertIn(('상태','모음 간 전이'),metric_rows(s,'먹',0,0,strict_closed=True))
