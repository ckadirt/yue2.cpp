"""Check final recorded evidence before permitting immutable backend publication."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

SOURCE = '25455ed8a9164e4fced3e31ea5d239f99300890f'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/cantor/validation/yue2'))
    args = parser.parse_args()
    root = args.root
    read = lambda name: json.loads((root / name).read_text())
    for mode in ['long', 'plan']:
        smoke = read(f'release-smoke-{mode}-04/smoke-results.json')
        assert smoke['retained_weights_matches'] and smoke['changed_request_differs']
        assert len(smoke['restart_checks']) == 3
        assert all(r['equal'] and r['fresh_process'] for r in smoke['restart_checks'].values())
    for probe in ['bpe', 'sampling', 'rng', 'lm', 'nar', 'vae']:
        assert int((root / f'reference-release-04/{probe}.exit').read_text()) == 0
    for name in ['cpu-generation-04', 'cpu-ar-generation-04']:
        result = read(f'{name}/result.json')
        assert result['audio_seconds'] > 0 and 0 < result['rms'] and result['peak_abs'] <= 1
        assert '/CPU/' in read(f'{name}/generation-status.json')['runtime']
    assert read('node-release-04/result.json')['passed']
    for suite, count in [('review-release-04', 9), ('review-speed8-release-05', 3),
                         ('review-speed16-release-06', 3)]:
        rows = read(f'{suite}/profiles.json')
        assert len(rows) == count
        assert all(0 < row['audio_seconds'] <= 30.04 and 0 < row['rms'] and row['peak_abs'] <= 1 for row in rows.values())
    presets = read('presets-release-04/presets.json')['presets']
    fast = read('speed8-release-05/presets.json')['presets']['speed']
    assert set(presets) == {'quality', 'balanced', 'speed'} and fast['steps'] == 8
    assert fast['warm_seconds_mean'] < presets['speed']['warm_seconds_mean']
    steps = read('step-release-04-Q5_K_M/step-sweep.json')
    assert steps['16']['wave_difference_from_32']['relative_l2'] < 0.1
    # ODE steps must not change the chosen score/semantic composition.
    reference = root / 'speed32-reference-06'
    candidate = root / 'presets-release-04/speed/warm-0'
    assert np.array_equal(np.load(reference / 'semantic.npy'), np.load(candidate / 'semantic.npy'))
    assert json.loads((reference / 'effective-request.json').read_text())['abc'] == json.loads((candidate / 'effective-request.json').read_text())['abc']
    a = np.load(reference / 'audio.npy').astype(np.float64).ravel()
    b = np.load(candidate / 'audio.npy').astype(np.float64).ravel()
    song_l2 = float(np.linalg.norm(a - b) / np.linalg.norm(a))
    assert song_l2 < 0.1
    artifacts = {}
    for backend in ['cpu', 'cuda12']:
        path = root / 'dist-25455ed8a916' / f'yue2-engine-{backend}-x86_64.tar.gz'
        receipt = json.loads(path.with_suffix(path.suffix + '.json').read_text())
        assert receipt['source_commit'] == SOURCE and not receipt['source_dirty']
        assert path.stat().st_size == receipt['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt['sha256']
        if 'dependencies' in receipt:
            assert all('nccl' not in lib for row in receipt['dependencies'].values() for lib in row)
        artifacts[path.name] = receipt['sha256']
    report = {'ready': True, 'source_commit': SOURCE, 'artifacts': artifacts,
        'selected_steps': {'quality': 32, 'balanced': 32, 'speed': 16},
        'speed_16_vs_32_planned_song_wave_relative_l2': song_l2,
        'speed_8_steps': 'Measured as an optional control; exceeded the 0.1 relative-waveform-L2 selection tolerance on the planned-song case and was not chosen as default',
        'checks': ['fresh-process stochastic resume and retry', 'retained/evicted equivalence',
                   'six final reference probes', 'relocated CPU full generation',
                   'isolated Cantor 0.2.10 install/load/generate', 'multilingual and instrumental finite normalized audio',
                   'independent precision and warm solver comparisons', 'clean immutable archive hashes'],
        'limitations': ['No human listening assessment', 'Native per-ID Philox seeds differ from Torch GPU grid-stride seeds',
                        'Six-minute capacity used eight solver steps and supplied semantic tokens',
                        'Only Linux x86_64 CPU and A10G CUDA generation were executed']}
    (root / 'acceptance-release-05.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
