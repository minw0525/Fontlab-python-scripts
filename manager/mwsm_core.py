"""Standard-library-only, transactional package storage. No FontLab imports."""
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
import uuid

REPOSITORY = 'minw0525/Fontlab-python-scripts'
RAW = 'https://raw.githubusercontent.com/' + REPOSITORY + '/'
CATALOG_URL = RAW + 'main/manifest.json'
RUNTIME_VERSION = '0.2.2'
HTTPS_FALLBACK = None
MAX_FILE = 32 * 1024 * 1024
MAX_PACKAGE = 100 * 1024 * 1024
MARKER = '# MW Script Manager owned wrapper v1\n'


class ManagerError(Exception):
    pass


class Cancelled(ManagerError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def version_number(version):
    if re.fullmatch(r'(?:0|[1-9][0-9]*)[.](?:0|[1-9][0-9]*)[.](?:0|[1-9][0-9]*)', version):
        return tuple(map(int, version.split('.')))
    return None


def is_newer_version(candidate, installed):
    new, old = version_number(candidate), version_number(installed)
    return new is not None and old is not None and new > old


def token(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', value):
        raise ManagerError('잘못된 ID 또는 버전: %r' % value)
    relative(value)
    return value


def relative(value):
    if not isinstance(value, str) or not value or len(value) > 240:
        raise ManagerError('잘못된 경로')
    parts = value.split('/')
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {x + str(i) for x in ('COM', 'LPT') for i in range(1, 10)}
    for part in parts:
        if (part in ('', '.', '..') or part.endswith((' ', '.')) or
                any(c in part for c in '\\:<>"|?*') or any(ord(c) < 32 for c in part) or
                part.split('.')[0].upper() in reserved):
            raise ManagerError('허용하지 않는 경로: ' + value)
    return value


def path_key(value):
    return unicodedata.normalize('NFC', value).casefold()


def safe_path(root, value):
    relative(value)
    root = Path(root)
    target = root.joinpath(*value.split('/'))
    # Walk all ancestors, including root: reject symlinks and Windows junctions.
    for p in [target] + list(target.parents):
        try:
            info = p.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            raise ManagerError('심볼릭 링크 경로는 사용할 수 없습니다: ' + str(p))
        if getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ManagerError('Windows reparse 경로는 사용할 수 없습니다: ' + str(p))
    return target


def validate_package(p, manager=False):
    if not isinstance(p, dict):
        raise ManagerError('패키지 형식 오류')
    token(p.get('version'))
    if not re.fullmatch('[0-9a-f]{40}', str(p.get('source_ref', ''))):
        raise ManagerError('source_ref는 40자리 고정 commit SHA여야 합니다')
    if not manager:
        token(p.get('id'))
        if not isinstance(p.get('name'), str) or not p['name'].strip():
            raise ManagerError('스크립트 이름이 없습니다')
        if not isinstance(p.get('requirements', []), list) or not all(isinstance(x, str) for x in p.get('requirements', [])):
            raise ManagerError('requirements 형식 오류')
        if not isinstance(p.get('platforms', []), list) or not set(p.get('platforms', [])) <= {'macos', 'windows'}:
            raise ManagerError('platforms 형식 오류')
    files = p.get('files')
    if not isinstance(files, list) or not 0 < len(files) <= 500:
        raise ManagerError('파일 목록이 없거나 너무 큽니다')
    targets = set()
    for f in files:
        if not isinstance(f, dict):
            raise ManagerError('파일 메타데이터 오류')
        for key in ('source', 'target'):
            path = relative(f.get(key))
            if PurePosixPath(path).suffix.lower() not in {'.py', '.txt', '.json', '.csv'} or '__pycache__' in path.split('/') or '.DS_Store' in path.split('/'):
                raise ManagerError('배포할 수 없는 파일: ' + path)
        expected_prefix = 'manager/' if manager else 'FL8 Scripts/'
        if not f['source'].startswith(expected_prefix):
            raise ManagerError('소스 영역이 올바르지 않습니다')
        key = path_key(f['target'])
        if key in targets or any(key.startswith(t + '/') or t.startswith(key + '/') for t in targets):
            raise ManagerError('중복되거나 충돌하는 파일 경로')
        targets.add(key)
        if not re.fullmatch('[0-9a-f]{64}', str(f.get('sha256', ''))):
            raise ManagerError('SHA-256 형식 오류')
    entry = p.get('entrypoint', 'main.py' if manager else '')
    relative(entry)
    if entry not in {f['target'] for f in files} or not entry.endswith('.py'):
        raise ManagerError('진입 파일이 목록에 없습니다')
    if manager and not {'main.py', 'mwsm_core.py', 'mwsm_host.py', 'mwsm_ui.py'} <= {f['target'] for f in files}:
        raise ManagerError('매니저 필수 파일이 없습니다')
    return p


def validate_manifest(m):
    if not isinstance(m, dict) or m.get('schema_version') != 1 or m.get('repository') != REPOSITORY:
        raise ManagerError('지원하지 않는 매니페스트 또는 저장소')
    validate_package(m.get('manager'), True)
    if not isinstance(m.get('scripts'), list):
        raise ManagerError('스크립트 목록 오류')
    ids = set()
    for p in m['scripts']:
        validate_package(p)
        key = path_key(p['id'])
        if key in ids:
            raise ManagerError('중복 스크립트 ID')
        ids.add(key)
    return m


def source_url(p, f):
    return RAW + p['source_ref'] + '/' + urllib.parse.quote(f['source'], safe='/')


def check_url(url):
    u = urllib.parse.urlsplit(url)
    if u.scheme != 'https' or u.hostname not in {'raw.githubusercontent.com', 'github.com'} or u.username or u.password or u.port not in (None, 443):
        raise ManagerError('허용하지 않는 다운로드 URL')


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Downloader:
    def __init__(self, cancel=None, progress=None):
        self.cancel = cancel or threading.Event()
        self.progress = progress or (lambda message: None)

    def __call__(self, url, limit=MAX_FILE):
        check_url(url)
        self.check_cancel()
        if not hasattr(urllib.request, 'HTTPSHandler') and HTTPS_FALLBACK is not None:
            return HTTPS_FALLBACK(url, limit, self.cancel, self.progress)
        if not hasattr(urllib.request, 'HTTPSHandler'):
            raise ManagerError('FontLab 내장 Python의 SSL 기능을 사용할 수 없습니다. '
                               'FontLab 설치/업데이트 상태를 확인하세요. 기존 설치는 유지됩니다.')
        start = time.monotonic()
        request = urllib.request.Request(url, headers={'User-Agent': 'FL8-MW-Script-Manager/0.1'})
        chunks, size = [], 0
        try:
            with urllib.request.build_opener(SafeRedirect()).open(request, timeout=15) as response:
                check_url(response.geturl())
                if int(response.headers.get('Content-Length', '0')) > limit:
                    raise ManagerError('다운로드 크기 제한 초과')
                while True:
                    self.check_cancel()
                    if time.monotonic() - start > 120:
                        raise ManagerError('다운로드 제한 시간 초과')
                    block = response.read(64 * 1024)
                    if not block:
                        break
                    size += len(block)
                    if size > limit:
                        raise ManagerError('다운로드 크기 제한 초과')
                    chunks.append(block)
                    self.progress('%s · %.1f MB' % (urllib.parse.unquote(url.rsplit('/', 1)[-1]), size / 1048576))
        except ManagerError:
            raise
        except Exception as exc:
            raise ManagerError('HTTPS 다운로드 실패 (네트워크/TLS/404/요청 제한 확인): ' + str(exc)) from exc
        self.check_cancel()
        return b''.join(chunks)

    def check_cancel(self):
        if self.cancel.is_set():
            raise Cancelled('작업을 취소했습니다')


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def atomic_write(path, data):
    path = Path(path)
    safe_path(path.parent, path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.mw-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def empty_state():
    return {'schema_version': 1, 'manager': None, 'packages': {}, 'history': {}}


def validate_state(s):
    if not isinstance(s, dict) or s.get('schema_version') != 1 or not isinstance(s.get('packages'), dict) or not isinstance(s.get('history'), dict):
        raise ManagerError('state.json 형식 오류')
    records = [(True, s.get('manager'))] + [(False, p) for p in s['packages'].values()]
    for manager, record in records:
        if record is None and manager:
            continue
        if not isinstance(record, dict) or not isinstance(record.get('versions'), dict):
            raise ManagerError('설치 상태 레코드 오류')
        active = token(record.get('active_version'))
        if active not in record['versions']:
            raise ManagerError('활성 버전 기록 누락')
        for version, p in record['versions'].items():
            validate_package(p, manager)
            if version != p['version']:
                raise ManagerError('버전 기록 불일치')
        previous = record.get('previous_version')
        if previous is not None and previous not in record['versions']:
            raise ManagerError('이전 버전 기록 누락')
        if not isinstance(record.get('auto_update'), bool) or not isinstance(record.get('pinned'), bool):
            raise ManagerError('업데이트 설정 오류')
    for key, record in s['packages'].items():
        token(key)
        if any(p['id'] != key for p in record['versions'].values()):
            raise ManagerError('ID 기록 불일치')
    return s


def wrapper(package_id=None, header=None):
    name = 'MW Script Manager' if package_id is None else 'MW · ' + token(package_id)
    header = header or '#FLM: ' + name
    if not header.startswith('#FLM:') or any(ord(c) < 32 for c in header):
        raise ManagerError('잘못된 메뉴 이름')
    return (header + '\n' + MARKER +
            'from pathlib import Path\nimport json, runpy\nfrom fontlab import flPreferences\n'
            '_mw_root = Path(flPreferences.instance().dataPath) / "script_manager"\n'
            '_mw_state = json.loads((_mw_root / "state.json").read_text(encoding="utf-8"))\n'
            '_mw_version = _mw_state["manager"]["active_version"]\n'
            'if not isinstance(_mw_version, str) or not _mw_version or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for c in _mw_version) or _mw_version in (".", ".."):\n'
            '    raise RuntimeError("Invalid manager version")\n'
            '_mw_main = _mw_root / "manager" / _mw_version / "main.py"\n'
            'runpy.run_path(str(_mw_main), init_globals={"MW_PACKAGE_ID": ' + repr(package_id) + '}, run_name="__main__")\n').encode('utf-8')


class Store:
    def __init__(self, user_data, downloader=None):
        # The host-selected root may itself be redirected (macOS /var, OneDrive).
        # Resolve that trusted root once; reject links anywhere inside our storage.
        self.user_data = Path(user_data).expanduser().resolve()
        if not self.user_data.is_dir():
            raise ManagerError('FontLab 사용자 데이터 폴더가 없습니다')
        self.root = safe_path(self.user_data, 'script_manager')
        self.fetch = downloader or Downloader()
        self.root.mkdir(exist_ok=True)
        for name in ('staging', 'logs'):
            safe_path(self.root, name).mkdir(exist_ok=True)

    def read_state(self):
        path = safe_path(self.root, 'state.json')
        if not path.exists():
            if safe_path(self.root, 'state.backup.json').exists() or any((self.root / n).exists() for n in ('packages', 'manager')):
                raise ManagerError('state.json이 없습니다. 백업 복구를 사용하세요')
            return empty_state()
        try:
            return validate_state(json.loads(path.read_text(encoding='utf-8')))
        except Exception as exc:
            raise ManagerError('state.json 손상: 백업 복구가 필요합니다. ' + str(exc)) from exc

    def save_state(self, state):
        validate_state(state)
        path = safe_path(self.root, 'state.json')
        if path.exists():
            previous = self.read_state()
            atomic_write(safe_path(self.root, 'state.backup.json'), json_bytes(previous))
        atomic_write(path, json_bytes(state))

    @contextlib.contextmanager
    def locked(self):
        path = safe_path(self.root, 'operation.lock')
        stream = path.open('a+b')
        try:
            if sys.platform == 'win32':
                import msvcrt
                stream.seek(0)
                if not stream.read(1):
                    stream.write(b'0')
                    stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            stream.close()
            raise ManagerError('다른 작업이 진행 중입니다') from exc
        try:
            self.recover_transactions()
            yield
        finally:
            stream.close()  # OS releases the lock, including after a crashed process.

    def journal(self, stage, state, moves, created_wrapper=None, wrapper_content=None):
        # Even a same-version repair needs a distinct commit marker.
        state['transaction_id'] = uuid.uuid4().hex
        def local(path):
            return path.relative_to(self.user_data).as_posix()
        data = {'state_sha256': digest(json_bytes(state)),
                'moves': [[local(a), local(b)] for a, b in moves],
                'wrapper': local(created_wrapper) if created_wrapper else None,
                'wrapper_sha256': digest(wrapper_content) if wrapper_content is not None else None,
                'wrapper_previous_sha256': digest(created_wrapper.read_bytes()) if created_wrapper and created_wrapper.is_file() else None}
        atomic_write(stage / 'transaction.json', json_bytes(data))

    def recover_transactions(self):
        """Finish committed work or undo interrupted renames before accepting a writer."""
        for stage in safe_path(self.root, 'staging').iterdir():
            safe_path(self.root, stage.relative_to(self.root).as_posix())
            receipt = stage / 'transaction.json'
            if not receipt.exists():
                # An interrupted download has not touched active files.
                if stage.is_dir() and stage.name.startswith(('install-', 'remove-', 'wrapper-')):
                    shutil.rmtree(stage)
                continue
            receipt = safe_path(stage, 'transaction.json')
            data = json.loads(receipt.read_text(encoding='utf-8'))
            current = safe_path(self.root, 'state.json')
            committed = current.exists() and digest(current.read_bytes()) == data['state_sha256']
            if not committed:
                name = data.get('wrapper')
                if name:
                    path = safe_path(self.user_data, name)
                    package_id = None if name == 'Scripts/MW Script Manager.py' else path.stem
                    if name != 'Scripts/MW Script Manager.py' and not name.startswith('Scripts/MW Scripts/'):
                        raise ManagerError('복구 래퍼 경로 오류')
                    if path.exists():
                        actual = digest(path.read_bytes())
                        moved = any(source == name and safe_path(self.user_data, dest).exists() for source, dest in data['moves'])
                        if actual == data.get('wrapper_previous_sha256') and not moved:
                            pass  # Crash before the original wrapper was moved aside.
                        elif actual == (data.get('wrapper_sha256') or digest(wrapper(package_id))):
                            path.unlink()
                        else:
                            raise ManagerError('복구 대상 래퍼가 수정되었습니다')
                for source, dest in reversed(data['moves']):
                    # Journals may only rename managed storage or a generated wrapper.
                    for name in (source, dest):
                        if not name.startswith(('script_manager/staging/', 'script_manager/packages/', 'script_manager/manager/', 'Scripts/MW Scripts/')):
                            raise ManagerError('복구 기록의 경로가 올바르지 않습니다')
                    source, dest = safe_path(self.user_data, source), safe_path(self.user_data, dest)
                    if not source.exists() and dest.exists():
                        source.parent.mkdir(parents=True, exist_ok=True)
                        os.replace(dest, source)
            shutil.rmtree(stage)
            self.log('recovered interrupted transaction ' + stage.name)

    def log(self, message):
        try:
            path = safe_path(self.root, 'logs/install.log')
            if path.exists() and path.stat().st_size > 1024 * 1024:
                os.replace(path, safe_path(self.root, 'logs/install.previous.log'))
            with path.open('a', encoding='utf-8') as out:
                out.write(time.strftime('%Y-%m-%d %H:%M:%S ') + message + '\n')
        except (OSError, ManagerError):
            pass  # A completed transaction must not become an error because logging failed.

    def catalog(self, manual=True):
        path = safe_path(self.root, 'manifest-cache.json')
        cached = None
        if path.exists():
            try:
                cached = json.loads(path.read_text(encoding='utf-8'))
                validate_manifest(cached['manifest'])
            except (ValueError, KeyError, TypeError, ManagerError):
                cached = None
        if not manual and cached and 0 <= time.time() - cached['checked_at'] < 86400:
            return cached['manifest'], None
        try:
            m = validate_manifest(json.loads(self.fetch(CATALOG_URL, 2 * 1024 * 1024)))
            atomic_write(path, json_bytes({'checked_at': time.time(), 'manifest': m}))
            return m, None
        except Cancelled:
            raise
        except Exception as exc:
            if cached:
                return cached['manifest'], '오프라인/카탈로그 오류 · 캐시 표시: ' + str(exc)
            raise ManagerError('카탈로그를 읽지 못했습니다: ' + str(exc)) from exc

    def version_dir(self, p, manager=False):
        prefix = 'manager' if manager else 'packages/' + token(p['id'])
        return safe_path(self.root, prefix + '/' + token(p['version']))

    def wrapper_path(self, package_id=None):
        if package_id is None:
            return safe_path(self.user_data, 'Scripts/MW Script Manager.py')
        record = self.read_state()['packages'].get(package_id, {})
        filename = record.get('wrapper', {}).get('filename', token(package_id) + '.py')
        return self.named_wrapper_path(filename)

    def named_wrapper_path(self, filename):
        relative(filename)
        if '/' in filename or not filename.endswith('.py'):
            raise ManagerError('잘못된 실행 파일명')
        return safe_path(self.user_data, 'Scripts/MW Scripts/' + filename)

    def wrapper_metadata(self, p, entry):
        filename = PurePosixPath(p['entrypoint']).name
        header = next((line for line in entry.decode('utf-8-sig').splitlines()
                       if line.startswith('#FLM:')), '#FLM: ' + p['name'])
        wrapper(p['id'], header)  # Validate a single-line menu label.
        return {'filename': filename, 'header': header, 'source_version': p['version']}

    def migrate_wrappers(self):
        """Restore source names without downloading or changing package versions."""
        changed = []
        with self.locked():
            state = self.read_state()
            for key, record in state['packages'].items():
                if record.get('wrapper', {}).get('source_version') == record['active_version']:
                    continue
                p = record['versions'][record['active_version']]
                self.verify(p)
                meta = self.wrapper_metadata(p, safe_path(self.version_dir(p), p['entrypoint']).read_bytes())
                if record.get('wrapper') == meta:
                    continue
                old = self.check_wrapper(key, allow_missing=True)
                target = self.named_wrapper_path(meta['filename'])
                if target != old and target.exists():
                    raise ManagerError('기존 파일과 충돌합니다: ' + str(target))
                for other, other_record in state['packages'].items():
                    if other != key and path_key(other_record.get('wrapper', {}).get('filename', other + '.py')) == path_key(meta['filename']):
                        raise ManagerError('다른 패키지가 사용 중인 파일명: ' + meta['filename'])
                content = wrapper(key, meta['header'])
                stage = Path(tempfile.mkdtemp(prefix='wrapper-', dir=str(self.root / 'staging')))
                saved = stage / 'old.py'
                new_state = copy.deepcopy(state)
                new_state['packages'][key]['wrapper'] = meta
                self.journal(stage, new_state, [(old, saved)] if old.exists() else [], target, content)
                committed = created = False
                try:
                    if old.exists():
                        os.replace(old, saved)
                    atomic_write(target, content)
                    created = True
                    self.save_state(new_state)
                    committed = True
                    state = new_state
                    changed.append(key)
                finally:
                    if not committed:
                        if created:
                            target.unlink()
                        if saved.exists():
                            os.replace(saved, old)
                    shutil.rmtree(stage, ignore_errors=True)
            return changed

    def verify(self, p, manager=False):
        base = self.version_dir(p, manager)
        expected = {f['target']: f['sha256'] for f in p['files']}
        if not base.is_dir():
            raise ManagerError('설치 파일이 없습니다: ' + str(base))
        for f in p['files']:
            target = safe_path(base, f['target'])
            if not target.is_file() or digest(target.read_bytes()) != f['sha256']:
                raise ManagerError('로컬 수정 또는 손상: ' + str(target))
        for path in base.rglob('*'):
            safe_path(base, path.relative_to(base).as_posix())
            if path.is_file() and path.relative_to(base).as_posix() not in expected:
                raise ManagerError('등록되지 않은 파일이 있습니다: ' + str(path))

    def check_wrapper(self, package_id, allow_missing=False):
        path = self.wrapper_path(package_id)
        record = self.read_state()['packages'].get(package_id, {}) if package_id else {}
        content = wrapper(package_id, record.get('wrapper', {}).get('header'))
        if path.exists():
            if not path.is_file() or path.read_bytes() != content:
                raise ManagerError('기존 파일과 충돌합니다 (자동 덮어쓰기 금지): ' + str(path))
        elif not allow_missing:
            raise ManagerError('실행 래퍼가 없습니다: ' + str(path))
        return path

    def install(self, p, manager=False, repair=False):
        validate_package(p, manager)
        package_id = None if manager else p['id']
        with self.locked():
            state = self.read_state()
            if not (self.root / 'state.json').exists():
                self.save_state(state)
            record = state['manager'] if manager else state['packages'].get(package_id)
            if record and p['version'] != record['active_version'] and not is_newer_version(p['version'], record['active_version']):
                raise ManagerError('설치 버전보다 높은 버전만 업데이트할 수 있습니다.')
            key = ('manager' if manager else 'packages/' + package_id) + '/' + p['version']
            fingerprint = digest(json_bytes(sorted(p['files'], key=lambda f: f['target'])))
            if key in state['history'] and state['history'][key] != fingerprint:
                raise ManagerError('같은 ID/버전의 파일 해시가 바뀐 배포입니다: ' + key)
            if record and not (manager and repair):
                self.verify(record['versions'][record['active_version']], manager)
            target_wrapper = self.check_wrapper(package_id, allow_missing=True)
            if record is None and target_wrapper.exists():
                raise ManagerError('소유 기록 없는 동명 실행 파일: ' + str(target_wrapper))
            old_wrapper = target_wrapper
            if not manager:
                target_wrapper = self.named_wrapper_path(PurePosixPath(p['entrypoint']).name)
                if target_wrapper != old_wrapper and target_wrapper.exists():
                    raise ManagerError('기존 파일과 충돌합니다: ' + str(target_wrapper))
                for other, other_record in state['packages'].items():
                    if other != package_id and path_key(other_record.get('wrapper', {}).get('filename', other + '.py')) == path_key(target_wrapper.name):
                        raise ManagerError('다른 패키지가 사용 중인 파일명: ' + target_wrapper.name)
            dest = self.version_dir(p, manager)
            if dest.exists() and (not record or p['version'] not in record['versions']):
                raise ManagerError('소유 기록 없는 버전 폴더: ' + str(dest))
            stage = Path(tempfile.mkdtemp(prefix='install-', dir=str(self.root / 'staging')))
            displaced = None
            wrapper_backup = None
            created_dest = created_wrapper = committed = False
            try:
                payload = stage / 'payload'
                payload.mkdir()
                size = 0
                for f in p['files']:
                    data = self.fetch(source_url(p, f), MAX_FILE)
                    size += len(data)
                    if size > MAX_PACKAGE or len(data) > MAX_FILE:
                        raise ManagerError('패키지 크기 제한 초과')
                    if digest(data) != f['sha256']:
                        raise ManagerError('SHA-256 불일치: ' + f['source'])
                    out = safe_path(payload, f['target'])
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(data)
                if hasattr(self.fetch, 'check_cancel'):
                    self.fetch.check_cancel()
                new = copy.deepcopy(record) if record else {'versions': {}, 'auto_update': True, 'pinned': False}
                old = new.get('active_version')
                if old != p['version']:
                    new['previous_version'] = old
                new['active_version'] = p['version']
                new['versions'][p['version']] = copy.deepcopy(p)
                meta = None if manager else self.wrapper_metadata(p, safe_path(payload, p['entrypoint']).read_bytes())
                content = wrapper(package_id, meta['header'] if meta else None)
                if meta:
                    new['wrapper'] = meta
                state['history'][key] = fingerprint
                if manager:
                    state['manager'] = new
                else:
                    state['packages'][package_id] = new
                moves = []
                if dest.exists() and manager and repair:
                    moves.append((dest, stage / 'previous'))
                if not dest.exists() or (manager and repair):
                    moves.append((payload, dest))
                replace_wrapper = not old_wrapper.exists() or old_wrapper != target_wrapper or old_wrapper.read_bytes() != content
                if replace_wrapper and old_wrapper.exists():
                    moves.append((old_wrapper, stage / 'wrapper.py'))
                self.journal(stage, state, moves, target_wrapper if replace_wrapper else None, content)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    if manager and repair:
                        displaced = stage / 'previous'
                        os.replace(dest, displaced)
                    else:
                        self.verify(p, manager)
                if not dest.exists():
                    os.replace(payload, dest)
                    created_dest = True
                if replace_wrapper:
                    if old_wrapper.exists():
                        wrapper_backup = stage / 'wrapper.py'
                        os.replace(old_wrapper, wrapper_backup)
                    atomic_write(target_wrapper, content)
                    created_wrapper = True
                self.save_state(state)
                committed = True
                self.log('install ' + key)
            finally:
                if not committed:
                    if created_wrapper:
                        target_wrapper.unlink()
                    if wrapper_backup is not None and wrapper_backup.exists():
                        os.replace(wrapper_backup, old_wrapper)
                    if created_dest:
                        shutil.rmtree(dest)
                    if displaced is not None and displaced.exists():
                        os.replace(displaced, dest)
                shutil.rmtree(stage, ignore_errors=True)

    def settings(self, package_id, auto_update, pinned):
        with self.locked():
            state = self.read_state()
            record = state['packages'][package_id]
            record.update(auto_update=bool(auto_update), pinned=bool(pinned))
            self.save_state(state)

    def updates(self, catalog, automatic=False):
        state = self.read_state()
        return [p for p in catalog['scripts'] if p['id'] in state['packages']
                and is_newer_version(p['version'], state['packages'][p['id']]['active_version'])
                and not state['packages'][p['id']]['pinned']
                and (not automatic or state['packages'][p['id']]['auto_update'])]

    def rollback(self, package_id):
        with self.locked():
            state = self.read_state()
            record = state['packages'][package_id]
            previous = record.get('previous_version')
            if not previous:
                raise ManagerError('이전 버전이 없습니다')
            self.check_wrapper(package_id)
            self.verify(record['versions'][previous])
            record['previous_version'], record['active_version'] = record['active_version'], previous
            record['auto_update'] = False
            self.save_state(state)
            self.log('rollback ' + package_id + '/' + previous)
        self.migrate_wrappers()

    def remove(self, package_id):
        with self.locked():
            state = self.read_state()
            record = state['packages'][package_id]
            target_wrapper = self.check_wrapper(package_id, allow_missing=True)
            for p in record['versions'].values():
                self.verify(p)
            base = safe_path(self.root, 'packages/' + token(package_id))
            if {p.name for p in base.iterdir()} != set(record['versions']):
                raise ManagerError('패키지 폴더에 소유하지 않은 데이터가 있습니다')
            stage = Path(tempfile.mkdtemp(prefix='remove-', dir=str(self.root / 'staging')))
            moved = []
            committed = False
            try:
                del state['packages'][package_id]
                self.journal(stage, state, [(source, stage / name) for source, name in
                             ((target_wrapper, 'wrapper.py'), (base, 'package')) if source.exists()])
                for source, name in ((target_wrapper, 'wrapper.py'), (base, 'package')):
                    if source.exists():
                        dest = stage / name
                        os.replace(source, dest)
                        moved.append((source, dest))
                self.save_state(state)
                committed = True
                self.log('remove ' + package_id)
            finally:
                if not committed:
                    for source, dest in reversed(moved):
                        os.replace(dest, source)
                shutil.rmtree(stage, ignore_errors=True)

    def recover(self):
        with self.locked():
            backup = safe_path(self.root, 'state.backup.json')
            state = validate_state(json.loads(backup.read_text(encoding='utf-8')))
            for manager, record in [(True, state['manager'])] + [(False, r) for r in state['packages'].values()]:
                if record:
                    self.verify(record['versions'][record['active_version']], manager)
            current = safe_path(self.root, 'state.json')
            if current.exists():
                atomic_write(safe_path(self.root, 'state.damaged-%d.json' % time.time_ns()), current.read_bytes())
            atomic_write(current, json_bytes(state))
            self.log('state restored from verified backup')
