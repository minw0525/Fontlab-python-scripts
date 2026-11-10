import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


LAUNCHER = Path(__file__).resolve().parents[1] / 'Run_HangulParametric.vfpy'


class LauncherTests(unittest.TestCase):
    def launch(self, window):
        names = ('model', 'inference', 'local_relations', 'mieum_relations', 'svc', 'fontlab_adapter', 'metrics', 'canvas', 'app')
        modules = { 'HangulParametric.' + name: types.ModuleType('HangulParametric.' + name)
                    for name in names }
        app = modules['HangulParametric.app']
        app._window = window
        app.show = Mock()
        with patch.dict(sys.modules, modules), patch('importlib.reload') as reload:
            runpy.run_path(str(LAUNCHER))
        return app, reload, list(modules.values())

    def test_reexecution_closes_before_reloading(self):
        window = Mock()
        window.close.return_value = True
        app, reload, modules = self.launch(window)
        window.close.assert_called_once_with()
        self.assertEqual([call.args[0] for call in reload.call_args_list], modules)
        app.show.assert_called_once_with()

    def test_cancelled_close_keeps_existing_code_and_window(self):
        window = Mock()
        window.close.return_value = False
        app, reload, _ = self.launch(window)
        reload.assert_not_called()
        app.show.assert_not_called()

    def test_closed_window_still_reloads_cached_code(self):
        app, reload, modules = self.launch(None)
        self.assertEqual(reload.call_count, len(modules))
        app.show.assert_called_once_with()
