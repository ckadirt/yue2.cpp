"""Recover only passing native CI packages; verify receipt and archive identity."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import zipfile

import requests

from mirror_weights import credentials


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=int, required=True)
    p.add_argument('--commit', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--keys', type=Path, default=Path('/cantor/keys/.env'))
    args = p.parse_args()
    values = credentials(args.keys)
    client = requests.Session()
    client.headers.update({'Authorization': 'Bearer ' + values['GH_KEY'], 'Accept': 'application/vnd.github+json'})
    api = 'https://api.github.com/repos/ckadirt/yue2.cpp'

    def get(url):
        result = client.get(url, timeout=180)
        if result.status_code != 200:
            raise RuntimeError(f'GitHub request failed with HTTP {result.status_code}')
        return result

    run = get(f'{api}/actions/runs/{args.run}').json()
    assert run['head_sha'] == args.commit and run['name'] == 'Cantor ABI'
    jobs = get(f'{api}/actions/runs/{args.run}/jobs?per_page=100').json()['jobs']
    passed = {j['name'] for j in jobs if j['conclusion'] == 'success'}
    artifacts = get(f'{api}/actions/runs/{args.run}/artifacts?per_page=100').json()['artifacts']
    args.output.mkdir(parents=True, exist_ok=True)
    verified = {}
    receipts = []
    for artifact in artifacts:
        if artifact['expired'] or not artifact['name'].startswith('yue2-engine-'):
            continue
        # Require the corresponding native job to have passed, not only upload.
        payload = get(artifact['archive_download_url']).content
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = archive.namelist()
            receipt_name = next(n for n in names if n.endswith('.tar.gz.json'))
            receipt = json.loads(archive.read(receipt_name))
            job = f"{receipt['os']} / {receipt['arch']} / {receipt['backend']}"
            if job not in passed:
                continue
            assert receipt['source_commit'] == args.commit and not receipt['source_dirty']
            assert receipt['family'] == 'yue2' and receipt['abi'] == 1
            filename = receipt['file']
            assert filename == Path(filename).name and filename.endswith('.tar.gz')
            archive_name = next(n for n in names if Path(n).name == filename)
            body = archive.read(archive_name)
            assert len(body) == receipt['bytes'] and hashlib.sha256(body).hexdigest() == receipt['sha256']
            for name, data in [(filename, body), (filename + '.json', json.dumps(receipt, indent=2).encode() + b'\n')]:
                path = args.output / name
                if path.exists():
                    assert path.read_bytes() == data, 'Refusing to replace a different recovered artifact'
                else:
                    path.write_bytes(data)
            verified[filename] = receipt['sha256']
            receipts.append({'file': filename, 'job': job, 'artifact_id': artifact['id'], 'bytes': len(body), 'sha256': receipt['sha256']})
    if not verified:
        raise RuntimeError('No passing native packages available yet')
    result = {'ready': True, 'scope': 'Only listed passing native CI packages; no generation assertion',
              'source_commit': args.commit, 'workflow_run': run['html_url'], 'artifacts': verified,
              'packages': receipts, 'jobs': [{'name': j['name'], 'status': j['status'], 'conclusion': j['conclusion']} for j in jobs],
              'checked_utc': datetime.now(timezone.utc).isoformat()}
    (args.output / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
