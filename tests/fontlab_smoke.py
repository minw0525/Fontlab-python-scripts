"""Run in FontLab's Python console, with a separately downloaded upstream snapshot.

runpy.run_path('/absolute/project/tests/fontlab_smoke.py')['run']('/tmp/mw-upstream')
All installed files stay in a new temporary user-data root. No font edits are run.
"""
from pathlib import Path
import importlib
import json
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def run(snapshot):
    old_path = sys.path[:]
    old_bytecode = sys.dont_write_bytecode
    try:
        sys.path.insert(0, str(ROOT / 'manager'))
        sys.dont_write_bytecode = True
        import mwsm_core, mwsm_host, mwsm_ui
        for window in mwsm_ui._windows:
            if window.busy:
                raise RuntimeError('Wait for the existing manager worker to finish')
            window.timer.stop()
            window.dialog.close()
        for module in (mwsm_core, mwsm_host, mwsm_ui):
            importlib.reload(module)
        audit = json.loads((ROOT / 'Documentation/upstream-audit.json').read_text())
        definitions = json.loads((ROOT / 'release-scripts.json').read_text())
        packages = []
        downloads = {}
        for p, evidence in zip(definitions['scripts'], audit['packages']):
            p = dict(p, source_ref=audit['source_ref'])
            p['files'] = []
            for f in evidence['files']:
                data = (Path(snapshot) / f['path']).read_bytes()
                assert mwsm_core.digest(data) == f['sha256']
                entry = {'source': f['path'], 'target': f['path'].removeprefix('FL8 Scripts/'), 'sha256': f['sha256']}
                p['files'].append(entry)
                downloads[mwsm_core.source_url(p, entry)] = data
            packages.append(p)
        # Test-only commit identifier; never written as a production manifest.
        manager = {'version': '0.1.0', 'source_ref': '0' * 40, 'files': []}
        for name in ('main.py', 'mwsm_core.py', 'mwsm_host.py', 'mwsm_ui.py'):
            data = (ROOT / 'manager' / name).read_bytes()
            f = {'source': 'manager/' + name, 'target': name, 'sha256': mwsm_core.digest(data)}
            manager['files'].append(f)
            downloads[mwsm_core.source_url(manager, f)] = data
        catalog = mwsm_core.validate_manifest({'schema_version': 1, 'repository': mwsm_core.REPOSITORY,
                                                'manager': manager, 'scripts': packages})
        user_data = Path(tempfile.mkdtemp(prefix='MW 검증 ')).resolve()
        store = mwsm_core.Store(user_data, lambda url, limit: downloads[url])
        store.install(manager, manager=True)
        adhesion = next(p for p in packages if p['id'] == 'adhesiontext-korean')
        store.install(adhesion)
        store.install(adhesion)  # Idempotence.
        original_path = sys.path[:]
        # Do not open an upstream dialog: its close handler writes font settings.
        # A separately named module lets us test __file__ / dictionary access
        # without replacing the user's already-loaded adhesiontext_korean module.
        from importlib.util import spec_from_file_location, module_from_spec
        app_path = store.version_dir(adhesion) / 'adhesiontext_korean/app.py'
        spec = spec_from_file_location('_mw_dictionary_smoke', str(app_path))
        app = module_from_spec(spec)
        spec.loader.exec_module(app)
        words = app.matchingWords('가나다라마바사아자차카타파하')
        assert isinstance(words, tuple)
        assert str(store.version_dir(adhesion)) in app.__file__
        assert sys.path == original_path
        store.verify(adhesion)
        mwsm_core.atomic_write(store.root / 'manifest-cache.json', mwsm_core.json_bytes({'checked_at': time.time(), 'manifest': catalog}))
        env = mwsm_host.environment()
        env['user_data'] = str(user_data)
        window = mwsm_ui.show_manager(env)
        window.dialog.setWindowTitle('MW Script Manager · 개발 검증 (임시 폴더)')
        print(json.dumps({'root': str(user_data), 'packages_in_catalog': len(packages),
                          'installed_packages': list(store.read_state()['packages']),
                          'dictionary_bytes': Path(app.dicFileLocation).stat().st_size,
                          'matching_words': len(words), 'relative_file': app.__file__,
                          'upstream_gui_executed': False,
                          'refresh_scripts': mwsm_host.refresh_scripts()}, ensure_ascii=False))
        return window
    finally:
        sys.path[:] = old_path
        sys.dont_write_bytecode = old_bytecode
