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
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeats must be positive")
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
        # Warm all weights and graphs before comparing solver step counts.
        run(engine, dict(request, steps=32), args.output / "warmup")
        for steps in [32, 16, 8]:
            current = dict(request, steps=steps)
            rows = [run(engine, current, args.output / str(steps) / f"repeat-{i}")
                    for i in range(args.repeats)]
            if len({row["audio_sha256"] for row in rows}) != 1:
                raise AssertionError("Repeated same-step output differs")
            row = dict(rows[0], repeats=rows,
                       pipeline_seconds_mean=float(np.mean([r["pipeline_seconds"] for r in rows])))
            if steps != 32:
                row["latent_difference_from_32"] = metrics(
                    np.load(args.output / "32/repeat-0/latents.npy"), np.load(args.output / str(steps) / "repeat-0/latents.npy"))
                row["wave_difference_from_32"] = metrics(
                    np.load(args.output / "32/repeat-0/audio.npy"), np.load(args.output / str(steps) / "repeat-0/audio.npy"))
            results[str(steps)] = row
            (args.output / "step-sweep.json").write_text(json.dumps(results, indent=2) + "\n")
            print(json.dumps({"steps": steps, "seconds": row["pipeline_seconds"]}), flush=True)
    finally:
        engine.close()


if __name__ == "__main__":
    main()
