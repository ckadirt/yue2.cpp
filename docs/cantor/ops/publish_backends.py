"""Publish verified backend archives to new immutable R2 keys; never replace objects."""
import argparse
import hashlib
import json
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import requests


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path, action='append', required=True)
    parser.add_argument('--validation', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    validation = json.loads(args.validation.read_text())
    if validation.get('ready') is not True:
        raise RuntimeError('Final validation has not marked these artifacts ready')
    values = {}
    for line in Path('/cantor/keys/.env').read_text().splitlines():
        if '=' in line and not line.strip().startswith('#'):
            key, value = line.strip().removeprefix('export ').split('=', 1)
            values[key.strip()] = value.strip().strip('\"\'')
    s3 = boto3.client('s3', endpoint_url=values['R2_ENDPOINT_URL'], region_name='auto',
        aws_access_key_id=values['R2_ACCESS_KEY_ID'], aws_secret_access_key=values['R2_SECRET_ACCESS_KEY'],
        config=Config(signature_version='s3v4', s3={'addressing_style': 'path'},
            request_checksum_calculation='when_required', response_checksum_validation='when_required',
            retries={'max_attempts': 5, 'mode': 'standard'}))
    records = []
    for receipt_path in args.receipt:
        receipt = json.loads(receipt_path.read_text())
        assert receipt['family'] == 'yue2' and receipt['abi'] == 1 and not receipt['source_dirty']
        assert receipt['source_commit'] == validation['source_commit']
        archive = receipt_path.parent / receipt['file']
        assert archive.stat().st_size == receipt['bytes'] and digest(archive) == receipt['sha256']
        assert validation['artifacts'][receipt['file']] == receipt['sha256']
        key = f"backends/{receipt['source_commit'][:12]}/{receipt['file']}"
        try:
            with archive.open('rb') as stream:
                s3.put_object(Bucket=values['R2_BUCKET'], Key=key, Body=stream,
                    ContentLength=receipt['bytes'], ContentType='application/gzip',
                    CacheControl='public, max-age=31536000, immutable', IfNoneMatch='*',
                    Metadata={'sha256': receipt['sha256'], 'source-commit': receipt['source_commit']})
        except ClientError as exc:
            code = exc.response['Error']['Code']
            if code not in {'PreconditionFailed', '412'}:
                raise RuntimeError(f'R2 upload failed: {code}') from None
            # An existing key may only be reused for the exact same bytes.
            existing = s3.head_object(Bucket=values['R2_BUCKET'], Key=key)
            if existing['ContentLength'] != receipt['bytes'] or existing.get('Metadata', {}).get('sha256') != receipt['sha256']:
                raise RuntimeError('Existing immutable object has another identity; refusing to replace it')
        url = 'https://ckpts.cantorfm.com/' + key
        public = requests.get(url, stream=True, timeout=180,
                              headers={'User-Agent': 'cantor-backend-validation/1'})
        if public.status_code != 200:
            raise RuntimeError(f'Public verification failed with HTTP {public.status_code}')
        sha, size = hashlib.sha256(), 0
        for chunk in public.iter_content(8 * 1024 * 1024):
            sha.update(chunk)
            size += len(chunk)
        if size != receipt['bytes'] or sha.hexdigest() != receipt['sha256']:
            raise RuntimeError('Public backend bytes failed integrity verification')
        row = {'url': url, 'bytes': size, 'sha256': sha.hexdigest(), 'public_verified': True}
        records.append(row)
        print(json.dumps(row), flush=True)
    args.output.write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
