"""Exercise an isolated Cantor node through its real CLI and loopback manifests."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import wave


def link_or_copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, target)
    except OSError:
        shutil.copyfile(source, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', type=Path, default=Path('/cantor/bin/cantor'))
    parser.add_argument('--fragments', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--models', type=Path, required=True)
    parser.add_argument('--runtime-cache', type=Path, default=Path('/cantor/models/engines'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    args.output.chmod(0o700)
    www, config = args.output / 'www', args.output / 'config'
    www.mkdir()
    config.mkdir(mode=0o700)
    model = json.loads((args.fragments / 'catalog-fragment.json').read_text())
    backend = json.loads((args.fragments / 'backends-fragment.json').read_text())
    handler = partial(SimpleHTTPRequestHandler, directory=str(www.resolve()))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    address = f'http://127.0.0.1:{server.server_port}'
    for artifact in backend['backends']:
        filename = Path(artifact['url']).name
        link_or_copy(args.artifacts / filename, www / filename)
        artifact['url'] = f'{address}/{filename}'
    (www / 'catalog.json').write_text(json.dumps({'schema': 1, 'models': [model]}))
    (www / 'backends.json').write_text(json.dumps({'schema': 1, 'engines': [backend]}))
    # Existing model bytes were SHA-verified independently. Sharing immutable
    # blobs avoids downloading the multi-GB checkpoint again for the host test.
    variant = next(v for v in model['variants'] if v['tag'] == '3b-balanced')
    model_root = args.output / 'models'
    for part in variant['components']:
        link_or_copy(args.models / Path(part['url']).name,
                     model_root / 'blobs/sha256' / part['blob'].removeprefix('sha256:'))
    engines = model_root / 'engines'
    engines.mkdir(exist_ok=True)
    for cached in args.runtime_cache.glob('cuda12-*'):
        if cached.is_dir() and (cached / '.complete').is_file() and cached.name.startswith(('cuda12-cuda_cudart-', 'cuda12-libcublas-')):
            (engines / cached.name).symlink_to(cached, target_is_directory=True)
    sock = args.output / 'control.sock'
    settings = {'name': 'YuE2 isolated validation', 'relay_url': 'ws://127.0.0.1:9',
        'model_dir': str(model_root), 'library_dir': str(args.output / 'library'),
        'catalog_url': address + '/catalog.json', 'backends_url': address + '/backends.json',
        'backend': 'cuda12'}
    (config / 'node.toml').write_text(''.join(f'{k} = {json.dumps(v)}\n' for k, v in settings.items()) + 'pairings = []\n\n[engine]\nn_threads = 4\n')
    (config / 'node.toml').chmod(0o600)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    daemon_log = (args.output / 'node.log').open('w')
    process = subprocess.Popen([str(args.node), 'run', '--config-dir', str(config),
        '--control-socket', str(sock)], stdout=daemon_log, stderr=subprocess.STDOUT)
    commands = []

    def command(name, *values, timeout=600):
        argv = [str(args.node), name, *values, '--control-socket', str(sock)]
        with (args.output / f'{name}.log').open('w') as log:
            result = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        commands.append({'command': name, 'exit_code': result.returncode})
        if result.returncode:
            raise RuntimeError(f'Cantor {name} failed; inspect {name}.log')

    try:
        until = time.monotonic() + 60
        while not sock.exists():
            if process.poll() is not None or time.monotonic() >= until:
                raise RuntimeError('Isolated node failed to start; inspect node.log')
            time.sleep(0.2)
        command('pull', 'yue2:3b-balanced')
        command('backends', '--install', '--use', 'cuda12')
        command('generate', 'English, warm piano pop, soft drums, clear lead vocal',
            '--model', 'yue2:3b-balanced', '--lyrics', '[Verse]\nMorning light is on the window',
            '--duration', '15', '--steps', '2', '--seed', '42', '-o', str(args.output / 'host.wav'))
        with wave.open(str(args.output / 'host.wav'), 'rb') as audio:
            channels, rate, frames = audio.getnchannels(), audio.getframerate(), audio.getnframes()
        assert channels == 2 and rate == 48000 and 0 < frames <= 15 * rate
        (args.output / 'result.json').write_text(json.dumps(
            {'passed': True, 'commands': commands, 'channels': channels,
             'sample_rate': rate, 'frames': frames, 'isolated_config': True,
             'relay': 'loopback only', 'model_blobs': 'reused independently verified immutable bytes'}, indent=2) + '\n')
        print('Isolated Cantor install/load/generate passed', flush=True)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        daemon_log.close()
        server.shutdown()
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
