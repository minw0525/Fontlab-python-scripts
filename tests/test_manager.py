import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'manager'))
from mwsm_core import (Cancelled, Downloader, ManagerError, Store, REPOSITORY,
                       digest, json_bytes, relative, safe_path, source_url,
                       validate_manifest, validate_package, wrapper)


def package(version='1.0.0', key='sample', files=None):
    files = files or {'Run.py': b'print("hello")\n'}
    p = {'id': key, 'name': key, 'version': version, 'source_ref': 'a' * 40,
         'entrypoint': next(iter(files)), 'requirements': [], 'platforms': [],
         'files': [{'source': 'FL8 Scripts/' + name, 'target': name, 'sha256': digest(data)} for name, data in files.items()]}
    return p, {source_url(p, f): files[f['target']] for f in p['files']}


def manager_package(version='0.1.0'):
    p = {'version': version, 'source_ref': 'b' * 40, 'files': []}
    data = {}
    for name in ('main.py', 'mwsm_core.py', 'mwsm_host.py', 'mwsm_ui.py'):
        contents = (ROOT / 'manager' / name).read_bytes()
        f = {'source': 'manager/' + name, 'target': name, 'sha256': digest(contents)}
        p['files'].append(f)
        data[source_url(p, f)] = contents
    return p, data


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='한글 MW ')
        self.root = Path(self.temp.name)
        self.payload = {}
        self.calls = []
        def fetch(url, limit):
            self.calls.append(url)
            data = self.payload[url]
            if isinstance(data, Exception):
                raise data
            return data
        self.store = Store(self.root, fetch)

    def tearDown(self):
        self.temp.cleanup()

    def add(self, version='1.0.0', key='sample', files=None):
        p, data = package(version, key, files)
        self.payload.update(data)
        return p

    def install(self, version='1.0.0', key='sample', files=None):
        p = self.add(version, key, files)
        self.store.install(p)
        return p

    def test_selective_multifile_install_and_idempotence(self):
        p = self.install(files={'Run.py': b'import helper\n', 'helper/__init__.py': b'', 'helper/data.txt': b'data'})
        self.assertEqual(len(self.calls), 3)
        self.store.install(p)
        state = self.store.read_state()
        self.assertEqual(list(state['packages']), ['sample'])
        self.assertEqual(len(state['packages']['sample']['versions']), 1)
        self.assertEqual(self.store.wrapper_path('sample').parent.name, 'MW Scripts')
        self.assertEqual(self.store.wrapper_path('sample').read_bytes(), wrapper('sample', '#FLM: sample'))
        self.assertEqual(list((self.store.root / 'staging').iterdir()), [])

    def test_hash_failure_preserves_existing_state(self):
        self.install()
        before = (self.store.root / 'state.json').read_bytes()
        p = self.add('2.0.0', files={'Run.py': b'changed', 'data.txt': b'asset'})
        self.payload[source_url(p, p['files'][1])] = b'wrong'
        with self.assertRaisesRegex(ManagerError, 'SHA-256'):
            self.store.install(p)
        self.assertEqual(before, (self.store.root / 'state.json').read_bytes())
        self.assertFalse(self.store.version_dir(p).exists())

    def test_network_failure_and_cancel_preserve_state(self):
        self.install()
        for error in (OSError('404'), Cancelled('cancelled')):
            p = self.add('2.0.0')
            self.payload[source_url(p, p['files'][0])] = error
            with self.assertRaises(type(error)):
                self.store.install(p)
            self.assertEqual(self.store.read_state()['packages']['sample']['active_version'], '1.0.0')

    def test_state_commit_failure_rolls_back_new_files(self):
        self.install()
        p = self.add('2.0.0')
        with patch.object(self.store, 'save_state', side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):
                self.store.install(p)
        self.assertFalse(self.store.version_dir(p).exists())
        self.assertEqual(self.store.read_state()['packages']['sample']['active_version'], '1.0.0')

    def test_initial_commit_failure_removes_wrapper(self):
        p = self.add()
        with patch.object(self.store, 'save_state', side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):
                self.store.install(p)
        self.assertFalse(self.store.wrapper_path('sample').exists())

    def test_same_version_changed_content_rejected_even_after_remove(self):
        self.install()
        self.store.remove('sample')
        p = self.add(files={'Run.py': b'new content'})
        with self.assertRaisesRegex(ManagerError, '해시가 바뀐'):
            self.store.install(p)

    def test_existing_wrapper_not_overwritten(self):
        p = self.add()
        target = self.store.wrapper_path('sample')
        target.parent.mkdir(parents=True)
        target.write_text('# user script')
        with self.assertRaisesRegex(ManagerError, '충돌'):
            self.store.install(p)
        self.assertEqual(target.read_text(), '# user script')
        self.assertEqual(self.calls, [])

    def test_owned_looking_wrapper_without_state_rejected(self):
        p = self.add()
        target = self.store.wrapper_path('sample')
        target.parent.mkdir(parents=True)
        target.write_bytes(wrapper('sample'))
        with self.assertRaisesRegex(ManagerError, '소유 기록'):
            self.store.install(p)

    def test_local_modifications_block_remove_and_update(self):
        p = self.install()
        local = self.store.version_dir(p) / 'Run.py'
        local.write_text('# user change')
        for action in (lambda: self.store.remove('sample'), lambda: self.store.install(self.add('2.0.0'))):
            with self.assertRaisesRegex(ManagerError, '로컬 수정'):
                action()
        self.assertTrue(local.exists())

    def test_extra_files_block_remove(self):
        p = self.install()
        (self.store.version_dir(p) / 'notes.txt').write_text('user')
        with self.assertRaisesRegex(ManagerError, '등록되지 않은'):
            self.store.remove('sample')

    def test_remove_failure_restores_files(self):
        p = self.install()
        with patch.object(self.store, 'save_state', side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):
                self.store.remove('sample')
        self.store.verify(p)
        self.assertTrue(self.store.wrapper_path('sample').exists())

    def test_rollback_pauses_auto_updates(self):
        first = self.install()
        second = self.install('2.0.0')
        self.store.rollback('sample')
        record = self.store.read_state()['packages']['sample']
        self.assertEqual(record['active_version'], first['version'])
        self.assertFalse(record['auto_update'])
        self.assertEqual(self.store.updates({'scripts': [second]}, automatic=True), [])

    def test_auto_updates_only_installed_unpinned_enabled(self):
        self.install()
        latest = self.add('2.0.0')
        new = self.add(key='new')
        catalog = {'scripts': [latest, new]}
        self.assertEqual(self.store.updates(catalog, True), [latest])
        self.store.settings('sample', True, True)
        self.assertEqual(self.store.updates(catalog, True), [])
        self.assertEqual(self.store.updates(catalog), [])

    def test_corrupt_state_explicit_backup_recovery(self):
        self.install()
        self.store.settings('sample', False, False)
        (self.store.root / 'state.json').write_text('{broken')
        with self.assertRaisesRegex(ManagerError, '손상'):
            self.store.read_state()
        self.store.recover()
        self.assertEqual(self.store.read_state()['packages']['sample']['active_version'], '1.0.0')
        self.assertTrue(list(self.store.root.glob('state.damaged-*.json')))

    def test_symlink_escape_blocked(self):
        self.store.save_state(self.store.read_state())
        outside = self.root / 'outside'
        outside.mkdir()
        (self.store.root / 'packages').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ManagerError, '링크'):
            self.store.install(self.add())
        self.assertEqual(list(outside.iterdir()), [])

    def test_operation_lock_blocks_second_writer(self):
        with self.store.locked():
            with self.assertRaisesRegex(ManagerError, '다른 작업'):
                self.store.install(self.add())

    def test_process_crash_before_state_commit_restores_install(self):
        self.install()
        second = self.add('2.0.0')
        code = '''import sys, os
sys.path.insert(0, sys.argv[1])
from mwsm_core import Store
import json
p=json.loads(sys.argv[3])
s=Store(sys.argv[2], lambda url, limit: b'print("hello")\\n')
s.save_state=lambda state: os._exit(73)
s.install(p)
'''
        result = subprocess.run([sys.executable, '-c', code, str(ROOT / 'manager'), str(self.root), json.dumps(second)])
        self.assertEqual(result.returncode, 73)
        with self.store.locked():
            pass
        self.assertFalse(self.store.version_dir(second).exists())
        self.assertEqual(self.store.read_state()['packages']['sample']['active_version'], '1.0.0')

    def test_process_crash_during_removal_restores_files(self):
        p = self.install()
        code = '''import sys, os
sys.path.insert(0, sys.argv[1])
from mwsm_core import Store
s=Store(sys.argv[2])
s.save_state=lambda state: os._exit(73)
s.remove('sample')
'''
        result = subprocess.run([sys.executable, '-c', code, str(ROOT / 'manager'), str(self.root)])
        self.assertEqual(result.returncode, 73)
        with self.store.locked():
            pass
        self.store.verify(p)
        self.assertTrue(self.store.wrapper_path('sample').exists())

    def test_manager_repair_preserves_packages(self):
        self.install()
        p, data = manager_package()
        self.payload.update(data)
        self.store.install(p, manager=True)
        (self.store.version_dir(p, True) / 'main.py').unlink()
        self.store.install(p, manager=True, repair=True)
        self.store.verify(p, True)
        self.assertIn('sample', self.store.read_state()['packages'])

    def test_offline_cache_and_invalid_catalog(self):
        p = self.add()
        m, data = manager_package()
        catalog = {'schema_version': 1, 'repository': REPOSITORY, 'manager': m, 'scripts': [p]}
        from mwsm_core import CATALOG_URL
        self.payload[CATALOG_URL] = json_bytes(catalog)
        self.assertIsNone(self.store.catalog()[1])
        self.payload[CATALOG_URL] = b'{}'
        result, warning = self.store.catalog()
        self.assertEqual(result, catalog)
        self.assertIn('캐시', warning)

    def test_runtime_file_path_assets_and_module_cache(self):
        from mwsm_host import run_package, _sessions
        p = self.install(files={'Run.py': b'from helper import text\nresult = text()\n',
                                'helper/__init__.py': b'from pathlib import Path\ndef text():\n return Path(__file__).with_name("data.txt").read_text()\n',
                                'helper/data.txt': '한글'.encode()})
        original = sys.path[:]
        try:
            result = run_package(self.root, 'sample')
            self.assertEqual(result['result'], '한글')
            self.assertEqual(result['__file__'], str(self.store.version_dir(p) / 'Run.py'))
            self.assertEqual(sys.path, original)
            self.store.verify(p)  # No bytecode was added.
            self.install('2.0.0', files={'Run.py': b'print("next")'})
            with self.assertRaisesRegex(ManagerError, '재시작'):
                run_package(self.root, 'sample')
        finally:
            sys.modules.pop('helper', None)
            _sessions.clear()

    def legacy_install(self, files=None):
        p = self.install(files=files or {'Original Script.py': b'#FLM: MW: Original Script\nprint(1)\n'})
        state = self.store.read_state()
        current = self.store.wrapper_path('sample')
        legacy = current.parent / 'sample.py'
        current.unlink()
        legacy.write_bytes(wrapper('sample'))
        del state['packages']['sample']['wrapper']
        self.store.save_state(state)
        return p, legacy

    def test_preserves_original_filename_and_flm(self):
        p = self.install(files={'Original Script.py': b'#FLM: MW: Original Menu Name\nprint(1)\n'})
        path = self.store.wrapper_path('sample')
        self.assertEqual(path.name, 'Original Script.py')
        self.assertEqual(path.read_text().splitlines()[0], '#FLM: MW: Original Menu Name')
        self.assertEqual((self.store.version_dir(p) / 'Original Script.py').read_bytes(), b'#FLM: MW: Original Menu Name\nprint(1)\n')

    def test_legacy_wrapper_migration_is_idempotent(self):
        p, old = self.legacy_install()
        before = self.store.read_state()['packages']['sample']['versions']
        self.assertEqual(self.store.migrate_wrappers(), ['sample'])
        self.assertFalse(old.exists())
        target = self.store.wrapper_path('sample')
        self.assertEqual(target.name, 'Original Script.py')
        self.assertEqual(target.read_text().splitlines()[0], '#FLM: MW: Original Script')
        self.assertEqual(self.store.migrate_wrappers(), [])
        self.assertEqual(self.store.read_state()['packages']['sample']['versions'], before)

    def test_migration_keeps_conflicting_user_file_and_old_wrapper(self):
        p, old = self.legacy_install()
        target = old.with_name('Original Script.py')
        target.write_text('# user file')
        with self.assertRaisesRegex(ManagerError, '충돌'):
            self.store.migrate_wrappers()
        self.assertEqual(target.read_text(), '# user file')
        self.assertEqual(old.read_bytes(), wrapper('sample'))
        self.assertNotIn('wrapper', self.store.read_state()['packages']['sample'])

    def test_migration_refuses_modified_owned_wrapper(self):
        p, old = self.legacy_install()
        old.write_bytes(old.read_bytes() + b'# user change\n')
        with self.assertRaisesRegex(ManagerError, '충돌'):
            self.store.migrate_wrappers()
        self.assertTrue(old.exists())

    def test_migration_commit_failure_restores_old_wrapper(self):
        p, old = self.legacy_install()
        with patch.object(self.store, 'save_state', side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):
                self.store.migrate_wrappers()
        self.assertEqual(old.read_bytes(), wrapper('sample'))
        self.assertFalse(old.with_name('Original Script.py').exists())

    def test_migration_crash_same_filename_restores_old_header(self):
        p, old = self.legacy_install(files={'sample.py': b'#FLM: MW: Original\n'})
        code = '''import sys, os
sys.path.insert(0, sys.argv[1])
from mwsm_core import Store
s=Store(sys.argv[2])
s.save_state=lambda state: os._exit(73)
s.migrate_wrappers()
'''
        result = subprocess.run([sys.executable, '-c', code, str(ROOT / 'manager'), str(self.root)])
        self.assertEqual(result.returncode, 73)
        with self.store.locked():
            pass
        self.assertEqual(old.read_bytes(), wrapper('sample'))
        self.assertNotIn('wrapper', self.store.read_state()['packages']['sample'])

    def test_migration_crash_before_first_rename_keeps_original(self):
        p, old = self.legacy_install(files={'sample.py': b'#FLM: MW: Original\n'})
        code = """import sys, os
sys.path.insert(0, sys.argv[1])
from mwsm_core import Store
s=Store(sys.argv[2])
original=s.journal
def interrupted(*args, **kwargs):
 original(*args, **kwargs)
 os._exit(73)
s.journal=interrupted
s.migrate_wrappers()
"""
        result = subprocess.run([sys.executable, '-c', code, str(ROOT / 'manager'), str(self.root)])
        self.assertEqual(result.returncode, 73)
        with self.store.locked():
            pass
        self.assertEqual(old.read_bytes(), wrapper('sample'))

    def test_new_install_does_not_overwrite_original_named_user_file(self):
        p = self.add()
        target = self.store.named_wrapper_path('Run.py')
        target.parent.mkdir(parents=True)
        target.write_text('# user')
        with self.assertRaisesRegex(ManagerError, '충돌'):
            self.store.install(p)
        self.assertEqual(target.read_text(), '# user')
        self.assertFalse(self.store.read_state()['packages'])

    def test_update_and_rollback_restore_entrypoint_name(self):
        self.install(files={'First.py': b'#FLM: MW: First\n'})
        self.install('2.0.0', files={'Second.py': b'#FLM: MW: Second\n'})
        second = self.store.wrapper_path('sample')
        self.assertEqual(second.name, 'Second.py')
        self.assertFalse(second.with_name('First.py').exists())
        self.store.rollback('sample')
        self.assertEqual(self.store.wrapper_path('sample').name, 'First.py')
        self.assertFalse(second.exists())


class ValidationTests(unittest.TestCase):
    def test_unsafe_paths(self):
        for path in ('../x.py', '/tmp/x.py', 'C:/x.py', 'x\\x.py', '//server/a.py', 'CON.py', 'a/../b.py', 'a./b.py', 'a//b.py', 'x:stream.py'):
            with self.subTest(path=path), self.assertRaises(ManagerError):
                relative(path)

    def test_schema_cases(self):
        p, _ = package()
        for mutate in (lambda p: p.update(files=[]), lambda p: p.update(source_ref='main'),
                       lambda p: p['files'].append(dict(p['files'][0])),
                       lambda p: p['files'][0].update(target='Run.pyc'),
                       lambda p: p['files'][0].update(target='/Run.py'),
                       lambda p: p['files'][0].update(sha256='bad')):
            candidate = copy.deepcopy(p)
            mutate(candidate)
            with self.assertRaises(ManagerError):
                validate_package(candidate)

    def test_case_insensitive_duplicate(self):
        p, _ = package(files={'Run.py': b'', 'run.py': b''})
        with self.assertRaises(ManagerError):
            validate_package(p)

    def test_network_cancel_and_https_host_restrictions(self):
        for url in ('http://raw.githubusercontent.com/x', 'https://evil.test/x', 'https://github.com.evil.test/x'):
            with self.assertRaises(ManagerError):
                Downloader()(url)
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(Cancelled):
            Downloader(cancel)('https://raw.githubusercontent.com/x')

    def test_installer_matches_sources(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from build_installer import build
        self.assertEqual((ROOT / 'MW_install.vfpy').read_text(), build())


if __name__ == '__main__':
    unittest.main()
