"""Mirror pinned generation files to R2 and verify every complete public body."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import requests

from download_models import FILES, REPO, REVISION


def credentials(path):
    values = {}
    for line in path.read_text().splitlines():
        if '=' in line and not line.strip().startswith('#'):
            key, value = line.strip().removeprefix('export ').split('=', 1)
            values[key.strip()] = value.strip().strip('\"\'')
    return values


def digest(path):
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024**2), b''):
            sha.update(chunk)
    return sha.hexdigest()


def head(s3, bucket, key):
    try:
        return s3.head_object(Bucket=bucket, Key=key)
    except ClientError as error:
        if error.response['Error']['Code'] not in {'404', 'NoSuchKey', 'NotFound'}:
            raise
        return None


def create(s3, bucket, key, path, sha, content_type):
    existing = head(s3, bucket, key)
    if existing:
        if existing['ContentLength'] != path.stat().st_size or existing.get('Metadata', {}).get('sha256') != sha:
            raise RuntimeError(f'Immutable key has a different identity: {key}')
        return
    metadata = {'sha256': sha, 'upstream-repository': REPO, 'upstream-revision': REVISION}
    common = dict(Bucket=bucket, Key=key)
    if path.stat().st_size < 128 * 1024**2:
        with path.open('rb') as stream:
            s3.put_object(**common, Body=stream, ContentLength=path.stat().st_size,
                          ContentType=content_type, CacheControl='public, max-age=31536000, immutable',
                          Metadata=metadata, IfNoneMatch='*')
        return
    upload = s3.create_multipart_upload(**common, ContentType=content_type,
                CacheControl='public, max-age=31536000, immutable', Metadata=metadata)['UploadId']
    part_size = 16 * 1024**2

    def part(number):
        with path.open('rb') as stream:
            stream.seek((number - 1) * part_size)
            data = stream.read(part_size)
        result = s3.upload_part(**common, UploadId=upload, PartNumber=number, Body=data)
        return {'PartNumber': number, 'ETag': result['ETag']}

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            parts = list(pool.map(part, range(1, (path.stat().st_size + part_size - 1) // part_size + 1)))
        # Preserve the same no-overwrite condition for the multipart commit.
        s3.complete_multipart_upload(**common, UploadId=upload, MultipartUpload={'Parts': parts}, IfNoneMatch='*')
    except BaseException:
        s3.abort_multipart_upload(**common, UploadId=upload)
        raise


def public_verify(url, size, sha):
    response = requests.get(url, stream=True, timeout=(30, 180), headers={'User-Agent': 'cantor/0.2.10'})
    response.raise_for_status()
    actual, count = hashlib.sha256(), 0
    for chunk in response.iter_content(8 * 1024**2):
        actual.update(chunk)
        count += len(chunk)
    if count != size or actual.hexdigest() != sha:
        raise RuntimeError(f'Complete public body failed verification: {url}')
    # Cantor resumes checkpoints using byte ranges. Probe a nonzero offset.
    if size > 4096:
        probe = requests.get(url, timeout=60, headers={'User-Agent': 'cantor/0.2.10', 'Range': 'bytes=1024-2047'})
        if probe.status_code != 206 or len(probe.content) != 1024 or not probe.headers.get('Content-Range', '').startswith('bytes 1024-2047/'):
            raise RuntimeError(f'Public range download failed: {url}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', type=Path, required=True)
    parser.add_argument('--keys', type=Path, default=Path('/cantor/keys/.env'))
    parser.add_argument('--prefix', default='yue2-1.0')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    values = credentials(args.keys)
    s3 = boto3.client('s3', endpoint_url=values['R2_ENDPOINT_URL'], region_name='auto',
                     aws_access_key_id=values['R2_ACCESS_KEY_ID'], aws_secret_access_key=values['R2_SECRET_ACCESS_KEY'],
                     config=Config(signature_version='s3v4', s3={'addressing_style': 'path'},
                         request_checksum_calculation='when_required', response_checksum_validation='when_required',
                         retries={'max_attempts': 5, 'mode': 'standard'}))
    records = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    files = dict(FILES)
    for name in ['LICENSE', 'README.md']:
        path = args.models / name
        files[name] = (path.stat().st_size, digest(path))
    for name, (size, sha) in files.items():
        path = args.models / name
        if path.stat().st_size != size or digest(path) != sha:
            raise RuntimeError(f'Pinned source integrity failed: {name}')
        key = args.prefix.rstrip('/') + '/' + name
        print(f'Uploading verified source {name}', flush=True)
        create(s3, values['R2_BUCKET'], key, path, sha, 'application/octet-stream' if name.endswith('.gguf') else 'text/plain; charset=utf-8')
        url = 'https://ckpts.cantorfm.com/' + key
        public_verify(url, size, sha)
        row = {'file': name, 'url': url, 'bytes': size, 'sha256': sha, 'public_verified': True}
        records.append(row)
        receipt = {'source': REPO, 'revision': REVISION, 'checked_utc': datetime.now(timezone.utc).isoformat(), 'files': records}
        args.output.write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(row), flush=True)
    manifest = args.output.with_name('manifest.json')
    manifest.write_text(json.dumps({'source': REPO, 'revision': REVISION, 'files': records}, indent=2) + '\n')
    sha = digest(manifest)
    create(s3, values['R2_BUCKET'], args.prefix.rstrip('/') + '/manifest.json', manifest, sha, 'application/json')
    public_verify('https://ckpts.cantorfm.com/' + args.prefix.rstrip('/') + '/manifest.json', manifest.stat().st_size, sha)
    print('All pinned generation checkpoints and source notices are public and verified.', flush=True)


if __name__ == '__main__':
    main()
