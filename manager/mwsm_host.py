"""FontLab UI-thread integration and explicit script execution."""
import importlib.util
from pathlib import Path
import platform
import runpy
import sys

from mwsm_core import ManagerError, Store, safe_path


def environment():
    import fontlab
    from PythonQt import QtCore, QtGui
    try:
        value = fontlab.flPreferences.instance().dataPath
    except Exception as exc:
        raise ManagerError('사용자 데이터 경로 API를 사용할 수 없습니다: ' + str(exc)) from exc
    if not value or not Path(str(value)).expanduser().is_dir():
        raise ManagerError('FontLab 사용자 데이터 경로가 유효하지 않습니다')
    for name in ('QDialog', 'QTableWidget', 'QProgressBar'):
        if not hasattr(QtGui, name):
            raise ManagerError('필수 PythonQt 기능 없음: ' + name)
    return {'user_data': str(Path(str(value)).expanduser()), 'python': sys.version,
            'platform': platform.platform(), 'qt': QtCore.qVersion(),
            'fontlab': str(getattr(fontlab, '__version__', '버전 API 미제공'))}


def refresh_scripts():
    try:
        from fontlab import flWorkspace
        main = flWorkspace.instance().mainWindow
        if main is not None:
            for obj in main.children():
                tip = getattr(obj, 'statusTip', '')
                if callable(tip):
                    tip = tip()
                if tip == '@mainwindow.actionRefreshScripts':
                    obj.trigger()
                    return True
    except Exception:
        pass
    return False


def compatibility(p):
    current = {'darwin': 'macos', 'win32': 'windows'}.get(sys.platform, sys.platform)
    if p.get('platforms') and current not in p['platforms']:
        return '지원하지 않는 OS: ' + current
    missing = []
    for requirement in p.get('requirements', []):
        module = 'typerig' if requirement == 'TypeRig' else requirement
        try:
            if importlib.util.find_spec(module) is None:
                missing.append(requirement)
        except (ImportError, ValueError, AttributeError):
            missing.append(requirement)
    return '필요 라이브러리: ' + ', '.join(missing) if missing else None


# Retain GUI globals, and refuse to hot-reload modules still referenced by Qt objects.
_sessions = {}


def run_package(user_data, package_id):
    store = Store(user_data)
    with store.locked():
        pass
    state = store.read_state()
    record = state['packages'].get(package_id)
    if record is None:
        raise ManagerError('설치되지 않은 스크립트입니다')
    p = record['versions'][record['active_version']]
    reason = compatibility(p)
    if reason:
        raise ManagerError(reason)
    store.verify(p)
    base = store.version_dir(p)
    parent = base.parent.resolve()
    for module in list(sys.modules.values()):
        location = getattr(module, '__file__', None)
        if location:
            location = Path(location).resolve()
            if parent in location.parents and base.resolve() not in location.parents:
                raise ManagerError('이 패키지의 이전 모듈이 사용 중입니다. FontLab을 재시작하세요')
    prior = _sessions.get(package_id)
    if prior and prior[0] != p['version']:
        raise ManagerError('업데이트된 스크립트를 실행하려면 FontLab을 재시작하세요')
    # Avoid collisions with unrelated packages using the same top-level module name.
    local_names = {f['target'].split('/')[0].removesuffix('.py') for f in p['files']}
    for name in local_names:
        module = sys.modules.get(name)
        if module is not None:
            location = getattr(module, '__file__', None)
            if not location or base.resolve() not in Path(location).resolve().parents:
                raise ManagerError('이미 로드된 다른 모듈과 충돌합니다: ' + name)
    original = sys.path[:]
    old_bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(base))
        result = runpy.run_path(str(safe_path(base, p['entrypoint'])), run_name='__main__')
        _sessions[package_id] = (p['version'], result)
        return result
    finally:
        sys.path[:] = original
        sys.dont_write_bytecode = old_bytecode
