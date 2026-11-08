#FLM: MW Script Manager
"""Versioned entry point. Keep one manager runtime per FontLab session."""
from pathlib import Path
import importlib.util
import sys


def launch(package_id=None):
    base = Path(__file__).resolve().parent
    old_bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        for name in ('mwsm_core', 'mwsm_host', 'mwsm_ui'):
            if name not in sys.modules:
                spec = importlib.util.spec_from_file_location(name, str(base / (name + '.py')))
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                try:
                    spec.loader.exec_module(module)
                except Exception:
                    del sys.modules[name]
                    raise
        from mwsm_host import environment, run_package
        from mwsm_ui import show_manager
        env = environment()
        if package_id is None:
            return show_manager(env)
        return run_package(env['user_data'], package_id)
    finally:
        sys.dont_write_bytecode = old_bytecode


if __name__ == '__main__':
    try:
        launch(globals().get('MW_PACKAGE_ID'))
    except Exception as exc:
        from PythonQt import QtGui
        QtGui.QMessageBox.warning(None, 'MW Script Manager', str(exc))
        raise
