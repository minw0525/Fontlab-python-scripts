import json
import unittest

from HangulParametric.model import (JAMO, VOWEL_ORDER, Session, characters, checked_box,
    decode_document, decompose, drag_box, merge_master, ordered_characters, role_indices, union_boxes,
    layout_run, visible_run, hit_role)


def session():
    result = Session()
    for char in '악안막':
        result.observations[char] = {'boxes': [dict(x=20, y=300, w=300, h=400) for _ in range(3)]}
    return result


class ModelTests(unittest.TestCase):
    def test_management_roundtrip_and_no_implicit_legacy_ownership(self):
        s = session()
        s.managed_components = {'막': {'0': 'source'}}
        self.assertEqual(Session.from_data(s.to_data()).managed_components, s.managed_components)
        old = s.to_data()
        del old['managedComponents']
        old['lockedGlyphs'] = []
        self.assertEqual(Session.from_data(old).managed_components, {})

    def test_enclosed_initial_wins_over_selected_vowel(self):
        boxes = [dict(x=50, y=300, w=200, h=200), dict(x=0, y=100, w=600, h=600), None]
        self.assertEqual(hit_role(boxes, 100, 400, current=1), 0)
        self.assertEqual(hit_role(boxes, 500, 400, current=0), 1)
        self.assertIsNone(hit_role(boxes, 900, 400))

    def test_equal_area_keeps_current_role(self):
        b = dict(x=0, y=0, w=200, h=200)
        self.assertEqual(hit_role([b, b, None], 100, 100, current=1), 1)

    def test_all_syllables(self):
        chars = ordered_characters([range(19), range(21), range(28)], vowel_order='unicode')
        self.assertEqual(chars, [chr(n) for n in range(0xAC00, 0xD7A4)])

    def test_requested_vowel_sequence(self):
        chars = ordered_characters([{11}, range(21), {0}])
        self.assertEqual(tuple(JAMO[1][decompose(c)[1]] for c in chars), VOWEL_ORDER)

    def test_empty_is_empty_and_no_final_is_real(self):
        self.assertEqual(ordered_characters([set(), {0}, {0}]), [])
        self.assertEqual(ordered_characters([{0}, {0}, {0}]), ['가'])

    def test_sort_priority(self):
        chars = ordered_characters([{0, 1}, {0, 1}, {1, 4}], (2, 0, 1))
        self.assertEqual([decompose(c)[2] for c in chars], [1] * 4 + [4] * 4)

    def test_strings_are_not_html_or_arbitrary_glyphs(self):
        self.assertEqual(characters('악 악\n안 A <b>ㄱ'), ['악', '안'])

    def test_integer_and_invalid_metrics(self):
        self.assertEqual(checked_box(dict(x=1.7, y=-2.1, w=10.3, h=99.9)), dict(x=2, y=-2, w=10, h=100))
        for w in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                checked_box(dict(x=0, y=0, w=w, h=20))

    def test_resize_opposite_corner(self):
        b = dict(x=20, y=300, w=300, h=400)
        self.assertEqual(drag_box(b, 'nw', 10, 20), dict(x=30, y=300, w=290, h=420))
        self.assertEqual(drag_box(b, 'se', 10, 20), dict(x=20, y=320, w=310, h=380))
        self.assertEqual(drag_box(b, 'move', 10, -20), dict(x=30, y=280, w=300, h=400))

    def test_measurements_immutable_under_edit_and_reset(self):
        s = session()
        s.set_box('악', 0, dict(x=20, y=300, w=310, h=400))
        self.assertEqual(s.observations['악']['boxes'][0]['w'], 300)
        s.reset('악', 0)
        self.assertEqual(s.box('악', 0)['w'], 300)

    def test_scope_only_same_jamo(self):
        s = session()
        origin = s.box('악', 0)
        s.set_box('악', 0, dict(origin, w=310))
        s.apply_delta('악', 0, origin, ['악', '안', '막'])
        self.assertEqual(s.box('안', 0)['w'], 310)
        self.assertEqual(s.box('막', 0)['w'], 300)
        self.assertEqual(s.box('안', 1)['w'], 300)
        s.apply_delta('악', 0, s.box('악', 0), ['악', '안'])
        self.assertEqual(s.box('안', 0)['w'], 310)

    def test_batch_preflight_no_partial_mutation(self):
        s = session()
        origin = s.box('악', 0)
        s.observations['안']['boxes'][0]['w'] = 10
        s.set_box('악', 0, dict(origin, w=200))
        with self.assertRaises(ValueError):
            s.apply_delta('악', 0, origin, ['악', '안'])
        self.assertNotIn('안', s.overrides)

    def test_round_trip_and_other_master_preservation(self):
        s = session()
        s.set_box('악', 0, dict(x=23, y=300, w=301, h=400))
        original = {'schemaVersion': 1, 'extra': 'preserve', 'masters': {'ExtraBold': {'sampleText': '맘'}}}
        encoded = merge_master(original, 'Thin', s)
        decoded = decode_document(encoded)
        self.assertEqual(decoded['masters']['ExtraBold'], original['masters']['ExtraBold'])
        self.assertEqual(decoded['extra'], 'preserve')
        self.assertNotIn('Thin', original['masters'])
        restored = Session.from_data(decoded['masters']['Thin'])
        self.assertEqual(restored.box('악', 0), s.box('악', 0))
        self.assertFalse(restored.dirty)

    def test_bad_documents_not_overwritten(self):
        for raw in ('broken', {'schemaVersion': 99}, {'schemaVersion': 1, 'masters': []}):
            with self.assertRaises((ValueError, json.JSONDecodeError)):
                merge_master(raw, 'Thin', session())

    def test_missing_role_no_fabricated_box(self):
        s = session()
        self.assertIsNone(s.box('맣', 0))
        with self.assertRaises(ValueError):
            s.set_box('맣', 0, dict(x=0, y=0, w=100, h=100))

    def test_beam_components_can_remain_separate(self):
        self.assertEqual(role_indices(4, True, True), [[0], [1, 2], [3]])
        self.assertEqual(role_indices(3, False, True), [[0], [1, 2]])
        with self.assertRaises(ValueError):
            role_indices(4, True)
        self.assertEqual(union_boxes([dict(x=10, y=20, w=100, h=200), dict(x=0, y=0, w=200, h=20)]),
                         dict(x=0, y=0, w=200, h=220))

    def test_large_run_only_returns_viewport_items(self):
        chars = ordered_characters([range(19), range(21), range(28)])
        items, height = layout_run(chars, 108, 0)
        self.assertEqual(len(items), 11172)
        first = visible_run(items, 0, 600, 108, 0, 900)
        last = visible_run(items, height - 600, 600, 108, 2200, 900)
        self.assertLess(len(first), 50)
        self.assertLess(len(last), 50)
        self.assertEqual(first[0][0], chars[0])
        self.assertEqual(last[-1][0], chars[-1])
        self.assertTrue(all(-157 <= y <= 600 for _, _, y in last))

    def test_row_boundaries_ignore_window_width(self):
        chars = ordered_characters([{11}, {0, 2}, range(28)])
        items, _ = layout_run(chars, 108, 0)
        self.assertEqual(len({y for _, _, y in items[:28]}), 1)
        self.assertGreater(items[28][2], items[27][2])
        single, _ = layout_run(chars, 108, 2)
        self.assertEqual(len({y for _, _, y in single}), 1)

    def test_horizontal_viewport_coordinates(self):
        items = [('악', 16, 24), ('안', 124, 24), ('알', 232, 24)]
        visible = visible_run(items, 0, 200, 108, 180, 100)
        self.assertEqual(visible, [('안', -56, 24), ('알', 52, 24)])


if __name__ == '__main__':
    unittest.main()
