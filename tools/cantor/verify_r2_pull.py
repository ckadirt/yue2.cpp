"""Check all preset pulls from R2 with an empty isolated real-node model store."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import threading
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog', type=Path, required=True)
    p.add_argument('--backends', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--node', type=Path, default=Path('/cantor/bin/cantor'))
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    args.output.chmod(0o700)
    www, config = args.output / 'www', args.output / 'config'
    www.mkdir()
    config.mkdir(mode=0o700)
    model = next(x for x in json.loads(args.catalog.read_text())['models'] if x['name'] == 'yue2')
    engine = next(x for x in json.loads(args.backends.read_text())['engines'] if x['name'] == 'yue2')
    for variant in model['variants']:
        for part in variant['components']:
            assert part['url'].startswith('https://ckpts.cantorfm.com/yue2-1.0/')
    assert all(x['url'].startswith('https://ckpts.cantorfm.com/') for x in engine['backends'])
    (www / 'catalog.json').write_text(json.dumps({'schema': 1, 'models': [model]}))
    (www / 'backends.json').write_text(json.dumps({'schema': 1, 'engines': [engine]}))
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(www.resolve())))
    address = f'http://127.0.0.1:{server.server_port}'
    sock = args.output / 'control.sock'
    settings = {'name': 'YuE2 fresh R2 pull verification', 'relay_url': 'ws://127.0.0.1:9',
                'model_dir': str(args.output / 'models'), 'library_dir': str(args.output / 'library'),
                'catalog_url': address + '/catalog.json', 'backends_url': address + '/backends.json', 'backend': 'cpu'}
    (config / 'node.toml').write_text(''.join(f'{k} = {json.dumps(v)}\n' for k, v in settings.items()) + 'pairings = []\n\n[engine]\nn_threads = 2\n')
    (config / 'node.toml').chmod(0o600)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    node_log = (args.output / 'node.log').open('w')
    process = subprocess.Popen([str(args.node), 'run', '--config-dir', str(config), '--control-socket', str(sock)], stdout=node_log, stderr=subprocess.STDOUT)
    results = []

    def command(label, *argv):
        started = time.monotonic()
        with (args.output / f'{label}.log').open('w') as log:
            r = subprocess.run([str(args.node), *argv, '--control-socket', str(sock)], stdout=log, stderr=subprocess.STDOUT, timeout=1800)
        row = {'command': list(argv), 'exit_code': r.returncode, 'seconds': time.monotonic() - started}
        results.append(row)
        print(json.dumps(row), flush=True)
        if r.returncode:
            raise RuntimeError(f'Fresh R2 check failed: {label}; inspect its log')

    try:
        deadline = time.monotonic() + 60
        while not sock.exists():
            if process.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('Isolated node failed to start')
            time.sleep(0.2)
        for tag in ['3b-quality', '3b-balanced', '3b-fast']:
            command('pull-' + tag, 'pull', 'yue2:' + tag)
        command('backends', 'backends', '--install', '--use', 'cpu')
        parts = {part['blob']: part for v in model['variants'] for part in v['components']}
        for blob, part in parts.items():
            path = args.output / 'models/blobs/sha256' / blob.removeprefix('sha256:')
            assert path.is_file() and path.stat().st_size == part['bytes']
        receipt = {'passed': True, 'fresh_empty_store': True, 'commands': results,
                   'unique_model_blobs': len(parts), 'download_bytes': sum(x['bytes'] for x in parts.values()),
                   'weights_and_engine_urls': 'public R2', 'manifest_urls': 'reviewed candidates served over loopback',
                   'generation': 'not requested', 'relay': 'loopback only',
                   'identity_checks': 'Cantor verifies content-addressed SHA-256 during every new download'}
        (args.output / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print('All three fresh R2 preset pulls and CPU backend installation passed.', flush=True)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        node_log.close()
        server.shutdown()
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
