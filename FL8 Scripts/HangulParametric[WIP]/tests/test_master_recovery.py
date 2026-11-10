import copy
import importlib.util
from pathlib import Path
import types
import unittest
from unittest.mock import patch

from HangulParametric.model import LIB_KEY, Session, decode_document


def adapter_class():
    modules = {name: types.ModuleType(name) for name in (
        'fontlab', 'typerig', 'typerig.proxy', 'typerig.proxy.fl',
        'typerig.proxy.fl.objects', 'typerig.proxy.fl.objects.font', 'typerig.proxy.fl.gui')}
    modules['typerig.proxy.fl.objects.font'].pFont = object
    modules['typerig.proxy.fl.gui'].QtGui = types.SimpleNamespace()
    path = Path(__file__).resolve().parents[1] / 'fontlab_adapter.py'
    spec = importlib.util.spec_from_file_location('HangulParametric._recovery_test_adapter', path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict('sys.modules', modules):
        spec.loader.exec_module(module)
    return module.FontAdapter


Adapter = adapter_class()


class MasterRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.adapter = Adapter.__new__(Adapter)
        self.adapter.check_active = lambda: None
        self.adapter.masters = lambda: ['Thin', 'Bold']
        self.adapter.package = types.SimpleNamespace(packageLib={LIB_KEY: -0.0, 'other': {'keep': True}})
        self.session = Session()
        self.session.sample_text = '마'
        self.session.observations = {'마': {'glyphName': 'uniB9C8', 'elementIndices': [[0], [1]],
                                           'boxes': [dict(x=10, y=20, w=100, h=200)] * 2}}
        self.session.predictions = {'먀': {'boxes': [dict(x=10, y=20, w=100, h=200)] * 2}}
        self.session.target_text = '먀'
        self.session.set_box('먀', 0, dict(x=15, y=20, w=100, h=200))

    def test_missing_master_blocks_before_font_access(self):
        for master in (None, '', 'Unknown'):
            operations = (
                lambda: self.adapter.measure('마', master),
                lambda: self.adapter.read_advances(master),
                lambda: self.adapter.prepare_source(self.session, '마', 0, master),
                lambda: self.adapter.source_layers('_source', master),
                lambda: self.adapter.map_component('_source', master, {}),
                lambda: self.adapter.apply_empty(self.session, '먀', master),
                lambda: self.adapter.save(master, self.session),
                lambda: self.adapter.load(master),
                lambda: self.adapter.recover_settings(master, self.session))
            for operation in operations:
                with self.subTest(master=master, operation=operation):
                    with self.assertRaisesRegex(ValueError, '마스터'):
                        operation()

    def test_recovery_preserves_entire_current_session(self):
        self.adapter.measure = lambda *args: (copy.deepcopy(self.session.observations), {}, [])
        before = self.session.to_data()
        self.adapter.recover_settings('Thin', self.session)
        lib = self.adapter.package.packageLib
        self.assertEqual(self.adapter.load('Thin').to_data(), before)
        self.assertEqual(lib['other'], {'keep': True})
        backups = [v for k, v in lib.items() if k.startswith(LIB_KEY + '.unreadable.')]
        self.assertEqual(backups, [-0.0])
        self.assertFalse(self.session.dirty)

    def test_different_master_metrics_do_not_destroy_session_or_lib(self):
        current = copy.deepcopy(self.session.observations)
        current['마']['boxes'][0]['w'] += 1
        self.adapter.measure = lambda *args: (current, {}, [])
        before = copy.deepcopy(self.adapter.package.packageLib)
        with self.assertRaisesRegex(ValueError, '일치하지'):
            self.adapter.recover_settings('Bold', self.session)
        self.assertEqual(self.adapter.package.packageLib, before)
        self.assertTrue(self.session.dirty)

    def test_missing_glyph_refuses_recovery(self):
        self.adapter.measure = lambda *args: ({}, {}, ['마: missing'])
        with self.assertRaisesRegex(ValueError, '일치하지'):
            self.adapter.recover_settings('Thin', self.session)
        self.assertEqual(self.adapter.package.packageLib[LIB_KEY], -0.0)

    def test_valid_document_is_never_reset(self):
        self.adapter.package.packageLib[LIB_KEY] = decode_document(None)
        with self.assertRaisesRegex(ValueError, '정상 설정'):
            self.adapter.recover_settings('Thin', self.session)

    def test_native_tuple_arrays_restore_as_json_lists(self):
        data = self.session.to_data()
        data['observations']['마']['elementIndices'] = ((0,), (1,))
        data['predictions']['먀']['evidence'] = ({'pairs': (('악', '막'),)},)
        restored = Session.from_data(data)
        self.assertEqual(restored.observations['마']['elementIndices'], [[0], [1]])
        self.assertEqual(restored.predictions['먀']['evidence'], [{'pairs': [['악', '막']]}])

    def test_empty_session_can_recover_and_bind(self):
        self.adapter.measure = lambda *args: ({}, {}, [])
        session = Session()
        self.adapter.recover_settings('Thin', session)
        self.assertEqual(self.adapter.load('Thin').to_data(), session.to_data())


if __name__ == '__main__':
    unittest.main()
