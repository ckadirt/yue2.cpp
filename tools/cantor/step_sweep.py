"""Measure acoustic step counts separately from quantization, retaining reference outputs."""
import argparse
import json
from pathlib import Path

import numpy as np

from verify_engine import Engine, run
from benchmark_matrix import metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--vae", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=750)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    request = json.loads(args.fixture.read_text())
    values = request["semantic_tokens"].split(",")[:args.frames]
    if len(values) != args.frames:
        raise ValueError("Not enough fixture frames")
    request.update(semantic_tokens=",".join(values), duration=args.frames / 25,
                   seed=1234, lm_seed=1234, lm_batch_size=1, synth_batch_size=1)
    engine = Engine(args.library, args.model, args.vae, keep=True)
    results = {}
    try:
        for steps in [32, 16, 8]:
            current = dict(request, steps=steps)
            row = run(engine, current, args.output / str(steps))
            if steps != 32:
                row["latent_difference_from_32"] = metrics(
                    np.load(args.output / "32/latents.npy"), np.load(args.output / str(steps) / "latents.npy"))
                row["wave_difference_from_32"] = metrics(
                    np.load(args.output / "32/audio.npy"), np.load(args.output / str(steps) / "audio.npy"))
            results[str(steps)] = row
            (args.output / "step-sweep.json").write_text(json.dumps(results, indent=2) + "\n")
            print(json.dumps({"steps": steps, "seconds": row["pipeline_seconds"]}), flush=True)
    finally:
        engine.close()


if __name__ == "__main__":
    main()
