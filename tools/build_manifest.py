"""Generate release metadata only from files that exist at immutable remote commits."""
import argparse
import ast
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'manager'))
from mwsm_core import Downloader, REPOSITORY, digest, json_bytes, source_url, validate_manifest


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
            or not re.fullmatch(r'(?:0|[1-9][0-9]*)[.](?:0|[1-9][0-9]*)[.](?:0|[1-9][0-9]*)', versions[0])):
        raise ValueError('Expected one numeric SemVer app_version in ' + source)
    return versions[0]


def generate(manager_ref, scripts_ref, source_root, output, manager_version='0.2.0'):
    fetch = Downloader()
    for ref in (manager_ref, scripts_ref):
        if not re.fullmatch('[0-9a-f]{40}', ref):
            raise ValueError('Use full immutable commit SHAs')
    script_metadata = json.loads((ROOT / 'tools' / 'release-scripts.json').read_text(encoding='utf-8'))
    published = {p['id']: p for p in json.loads((ROOT / 'manifest.json').read_text())['scripts']}
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
        previous = published.get(p['id'])
        if previous and previous['version'] == p['version']:
            by_target = lambda files: sorted(files, key=lambda f: f['target'])
            if by_target(previous['files']) != by_target(p['files']):
                raise ValueError('Bump app_version before publishing changed files: ' + p['id'])
        scripts.append(p)
    manager = {'version': manager_version, 'source_ref': manager_ref, 'files': []}
    for name in ('main.py', 'mwsm_core.py', 'mwsm_host.py', 'mwsm_ui.py'):
        source = 'manager/' + name
        local = (ROOT / source).read_bytes()
        ast.parse(local, feature_version=(3, 10))
        remote = fetch(source_url(manager, {'source': source}))
        if local != remote:
            raise ValueError('Manager must be committed and published before catalog generation: ' + source)
        manager['files'].append({'source': source, 'target': name, 'sha256': digest(remote)})
    m = validate_manifest({'schema_version': 1, 'repository': REPOSITORY, 'manager': manager, 'scripts': scripts})
    output.write_bytes(json_bytes(m))
    print('Verified and wrote', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manager-ref', required=True)
    parser.add_argument('--scripts-ref', required=True)
    parser.add_argument('--source-root', type=Path)
    parser.add_argument('--manager-version', default='0.2.0')
    parser.add_argument('--output', type=Path, default=ROOT / 'manifest.json')
    args = parser.parse_args()
    generate(args.manager_ref, args.scripts_ref, args.source_root, args.output, args.manager_version)
