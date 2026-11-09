"""Measure the complete proposed presets after independent quant/step comparisons."""
import argparse
import json
from pathlib import Path

import numpy as np

from verify_engine import Engine, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--models', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--speed-steps', type=int, choices=[8, 16], default=16)
    parser.add_argument('--tiers', nargs='+', choices=['quality', 'balanced', 'speed'],
                        default=['quality', 'balanced', 'speed'])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'scope': 'Single A10G, one frozen 30-second English planned-song request; warm timings include score planning. Quantization may change the planned score.', 'presets': {}}
    for name, quant, steps in [('quality', 'BF16', 32), ('balanced', 'Q8_0', 32), ('speed', 'Q5_K_M', args.speed_steps)]:
        if name not in args.tiers:
            continue
        request = {'caption': 'English, piano pop, warm expressive lead vocal, soft drums, clear production',
            'lyrics': '[Verse]\nMorning light is on the window\nEvery road will lead me home\n[Chorus]\nLet the music carry us together\nWe will never walk alone',
            'cot': 'full', 'duration': 30, 'seed': 1234, 'inference_steps': steps,
            'guidance_scale': 1.0, 'semantic_sampling': {'min_tokens': 750, 'max_tokens': 750}}
        engine = Engine(args.library, args.models / f'YuE2-3B-{quant}.gguf', args.models / 'YuE2-Vae-F32.gguf', keep=True)
        try:
            cold = run(engine, request, args.output / name / 'cold')
            rows = [run(engine, request, args.output / name / f'warm-{i}') for i in range(2)]
            if len({cold['audio_sha256'], *(r['audio_sha256'] for r in rows)}) != 1:
                raise AssertionError('Repeated same-preset output differs')
            mean = float(np.mean([r['pipeline_seconds'] for r in rows]))
            report['presets'][name] = {'quant': quant, 'vae': 'F32', 'steps': steps, 'cold': cold, 'warm': rows,
                'warm_seconds_mean': mean, 'realtime_factor': mean / rows[0]['audio_seconds']}
            (args.output / 'presets.json').write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps({'preset': name, 'warm_seconds': mean}), flush=True)
        finally:
            engine.close()


if __name__ == '__main__':
    main()
