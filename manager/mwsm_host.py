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


class QtHttpsBridge:
    """Main-thread Qt network I/O serving the existing Python worker via a queue."""
    def __init__(self):
        import queue
        import threading
        self.owner_thread = threading.get_ident()
        from PythonQt import QtCore, QtNetwork
        self.qt = QtCore
        self.network = QtNetwork
        self.pending = queue.Queue()
        self.active = []
        self.manager = QtNetwork.QNetworkAccessManager()
        self.timer = QtCore.QTimer(self.manager)
        self.timer.connect('timeout()', self.poll)
        self.timer.start(50)

    def __call__(self, url, limit, cancel, progress):
        import threading
        import time
        from mwsm_core import check_url, Cancelled
        if threading.get_ident() == self.owner_thread:
            raise ManagerError('HTTPS 요청은 작업자 스레드에서 실행해야 합니다')
        deadline = time.monotonic() + 120
        for _ in range(6):
            check_url(url)
            job = {'url': url, 'limit': limit, 'cancel': cancel, 'progress': progress,
                   'deadline': deadline, 'done': threading.Event(), 'data': bytearray(), 'error': None}
            self.pending.put(job)
            while not job['done'].wait(0.1):
                if cancel.is_set():
                    raise Cancelled('작업을 취소했습니다')
                if time.monotonic() >= deadline:
                    raise ManagerError('다운로드 제한 시간 초과')
            if job['error']:
                raise job['error']
            if cancel.is_set():
                raise Cancelled('작업을 취소했습니다')
            if job.get('redirect'):
                url = job['redirect']
                continue
            return bytes(job['data'])
        raise ManagerError('리디렉션 횟수 제한 초과')

    def poll(self):
        import queue
        import time
        from mwsm_core import Cancelled
        while True:
            try:
                job = self.pending.get_nowait()
            except queue.Empty:
                break
            try:
                request = self.network.QNetworkRequest(self.qt.QUrl(job['url']))
                # FontLab's PythonQt exposes the Qt 5 legacy attribute.
                request.setAttribute(self.network.QNetworkRequest.FollowRedirectsAttribute, False)
                reply = self.manager.get(request)
                reply.setReadBufferSize(64 * 1024)
                job['reply'] = reply
                self.active.append(job)
                reply.connect('readyRead()', lambda j=job: self.read(j))
                reply.connect('finished()', lambda j=job: self.finish(j))
            except Exception as exc:
                job['error'] = ManagerError('Qt HTTPS 시작 실패: ' + str(exc))
                job['done'].set()
        for job in list(self.active):
            if job['cancel'].is_set() or time.monotonic() >= job['deadline']:
                job['error'] = Cancelled('작업을 취소했습니다') if job['cancel'].is_set() else ManagerError('다운로드 제한 시간 초과')
                job['reply'].abort()

    def read(self, job):
        try:
            data = job['reply'].readAll().data()
            if len(job['data']) + len(data) > job['limit']:
                raise ManagerError('다운로드 크기 제한 초과')
            job['data'].extend(data)
            job['progress']('HTTPS 다운로드 · %.1f MB' % (len(job['data']) / 1048576))
        except Exception as exc:
            job['error'] = ManagerError(str(exc))
            job['reply'].abort()

    def finish(self, job):
        from mwsm_core import check_url
        reply = job['reply']
        try:
            if not job['error']:
                self.read(job)
            if not job['error']:
                status = reply.attribute(self.network.QNetworkRequest.HttpStatusCodeAttribute)
                if reply.error() != self.network.QNetworkReply.NoError:
                    raise ManagerError('HTTPS 다운로드 실패: ' + reply.errorString())
                if status in (301, 302, 303, 307, 308):
                    target = reply.attribute(self.network.QNetworkRequest.RedirectionTargetAttribute)
                    redirect = reply.url().resolved(target).toString()
                    check_url(redirect)
                    job['redirect'] = redirect
                elif status != 200:
                    raise ManagerError('HTTPS 응답 오류: ' + str(status))
        except Exception as exc:
            job['error'] = ManagerError(str(exc))
        finally:
            if job in self.active:
                self.active.remove(job)
            reply.deleteLater()
            job['done'].set()


_https_bridge = None


def prepare_https():
    """Use only the Qt runtime already shipped by FontLab; never relax TLS checks."""
    import urllib.request
    import mwsm_core
    global _https_bridge
    if hasattr(urllib.request, 'HTTPSHandler'):
        return
    from PythonQt import QtNetwork
    if not QtNetwork.QSslSocket.supportsSsl():
        raise ManagerError('Python과 FontLab 내장 Qt 모두 HTTPS를 지원하지 않습니다')
    if _https_bridge is None:
        _https_bridge = QtHttpsBridge()
    mwsm_core.HTTPS_FALLBACK = _https_bridge
