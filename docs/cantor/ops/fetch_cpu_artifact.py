"""Recover the clean portable CPU archive from the exact passing fork CI run."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import time
import zipfile

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    values = {}
    for line in Path('/cantor/keys/.env').read_text().splitlines():
        if '=' in line and not line.strip().startswith('#'):
            key, value = line.strip().removeprefix('export ').split('=', 1)
            values[key.strip()] = value.strip().strip('\"\'')
    client = requests.Session()
    client.headers.update({'Authorization': 'Bearer ' + values['GH_KEY'],
                           'Accept': 'application/vnd.github+json'})
    api = 'https://api.github.com/repos/ckadirt/yue2.cpp'

    def get(url):
        result = client.get(url, timeout=180)
        if result.status_code != 200:
            raise RuntimeError(f'GitHub request failed with HTTP {result.status_code}')
        return result

    until = time.monotonic() + 1200
    while time.monotonic() < until:
        runs = get(f'{api}/actions/runs?branch=cantor-abi-v1&per_page=30').json()['workflow_runs']
        matching = [r for r in runs if r['name'] == 'Cantor ABI' and r['head_sha'] == args.commit]
        if matching and matching[0]['status'] == 'completed':
            run = matching[0]
            if run['conclusion'] != 'success':
                raise RuntimeError('The requested CPU CI run did not pass')
            break
        time.sleep(15)
    else:
        raise RuntimeError('CPU CI did not finish within 20 minutes')
    artifacts = get(f"{api}/actions/runs/{run['id']}/artifacts").json()['artifacts']
    artifact = next(a for a in artifacts if a['name'] == 'yue2-engine-cpu-x86_64' and not a['expired'])
    payload = get(artifact['archive_download_url']).content
    args.output.mkdir(parents=True, exist_ok=True)
    names = ['yue2-engine-cpu-x86_64.tar.gz', 'yue2-engine-cpu-x86_64.tar.gz.json']
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for name in names:
            member = next(n for n in archive.namelist() if Path(n).name == name)
            path = args.output / name
            if path.exists():
                raise RuntimeError('Refusing to replace a recovered archive or receipt')
            path.write_bytes(archive.read(member))
    receipt = json.loads((args.output / names[1]).read_text())
    archive = args.output / names[0]
    assert receipt['source_commit'] == args.commit and not receipt['source_dirty']
    assert archive.stat().st_size == receipt['bytes']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == receipt['sha256']
    (args.output / 'cpu-ci-source.json').write_text(json.dumps(
        {'commit': args.commit, 'workflow_run': run['html_url'], 'artifact_id': artifact['id']}, indent=2) + '\n')
    print(json.dumps({'cpu_archive_verified': True, 'workflow_run': run['html_url'],
                      'sha256': receipt['sha256'], 'bytes': receipt['bytes']}), flush=True)


if __name__ == '__main__':
    main()
