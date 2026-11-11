"""Generate release metadata only from files that exist at immutable remote commits."""
import argparse
import ast
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'manager'))
from mwsm_core import Downloader, REPOSITORY, RUNTIME_VERSION, digest, is_newer_version, json_bytes, source_url, validate_manifest, version_number


def script_version(data, source):
    versions = []
    for node in ast.parse(data, filename=source).body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            pairs = (zip(target.elts, node.value.elts)
                     if isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple)
                     else [(target, node.value)])
            for name, value in pairs:
                if isinstance(name, ast.Name) and name.id == 'app_version':
                    versions.append(ast.literal_eval(value))
    if (len(versions) != 1 or not isinstance(versions[0], str)
            or version_number(versions[0]) is None):
        raise ValueError('Expected one numeric SemVer app_version in ' + source)
    return versions[0]


def release_record(current, previous, label):
    if not previous:
        return current
    if current['version'] == previous['version']:
        if sorted(current['files'], key=lambda f: f['target']) == sorted(previous['files'], key=lambda f: f['target']):
            current['source_ref'] = previous['source_ref']
            return current
    elif is_newer_version(current['version'], previous['version']):
        return current
    raise ValueError('Use a version above %s before publishing %s' % (previous['version'], label))


def generate(manager_ref, scripts_ref, source_root, output, manager_version=RUNTIME_VERSION):
    fetch = Downloader()
    for ref in (manager_ref, scripts_ref):
        if not re.fullmatch('[0-9a-f]{40}', ref):
            raise ValueError('Use full immutable commit SHAs')
    script_metadata = json.loads((ROOT / 'tools' / 'release-scripts.json').read_text(encoding='utf-8'))
    baseline = validate_manifest(json.loads((ROOT / 'manifest.json').read_bytes()))
    published = {p['id']: p for p in baseline['scripts']}
    scripts = []
    for item in script_metadata['scripts']:
        p = {k: v for k, v in item.items() if k not in ('files', 'version_file')}
        p['source_ref'] = scripts_ref
        p['files'] = []
        version_file = item.get('version_file', 'FL8 Scripts/' + p['entrypoint'])
        if version_file not in item['files']:
            raise ValueError('Version source must be a package file: ' + version_file)
        for source in item['files']:
            data = fetch(source_url(p, {'source': source}))
            if source_root and (source_root / source).read_bytes() != data:
                raise ValueError('Local/remote mismatch: ' + source)
            if source == version_file:
                p['version'] = script_version(data, source)
            p['files'].append({'source': source, 'target': source.removeprefix('FL8 Scripts/'), 'sha256': digest(data)})
        scripts.append(release_record(p, published.get(p['id']), p['id']))
    manager = {'version': manager_version, 'source_ref': manager_ref, 'files': []}
    for name in ('main.py', 'mwsm_core.py', 'mwsm_host.py', 'mwsm_ui.py'):
        source = 'manager/' + name
        local = (ROOT / source).read_bytes()
        ast.parse(local, feature_version=(3, 10))
        remote = fetch(source_url(manager, {'source': source}))
        if local != remote:
            raise ValueError('Manager must be committed and published before catalog generation: ' + source)
        manager['files'].append({'source': source, 'target': name, 'sha256': digest(remote)})
    manager = release_record(manager, baseline['manager'], 'manager')
    m = validate_manifest({'schema_version': 1, 'repository': REPOSITORY, 'manager': manager, 'scripts': scripts})
    output.write_bytes(json_bytes(m))
    print('Verified and wrote', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manager-ref', required=True)
    parser.add_argument('--scripts-ref', required=True)
    parser.add_argument('--source-root', type=Path)
    parser.add_argument('--manager-version', default=RUNTIME_VERSION)
    parser.add_argument('--output', type=Path, default=ROOT / 'manifest.json')
    args = parser.parse_args()
    generate(args.manager_ref, args.scripts_ref, args.source_root, args.output, args.manager_version)
