"""Compare published precisions with fixed controls; retain audio and numeric evidence."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np

from verify_engine import Engine, run

QUANTS = ["BF16", "Q8_0", "Q6_K", "Q5_K_M"]


def metrics(reference, candidate):
    a, b = reference.astype(np.float64).ravel(), candidate.astype(np.float64).ravel()
    if a.shape != b.shape:
        raise ValueError("Comparison shapes differ")
    return {"cosine": float(np.dot(a, b) / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-30)),
            "relative_l2": float(np.linalg.norm(a - b) / max(np.linalg.norm(a), 1e-30)),
            "max_abs": float(np.max(np.abs(a - b)))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=300)
    parser.add_argument("--steps", type=int, default=32)
    parser.add_argument("--lm-probe", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((args.models / "cantor-source-manifest.json").read_text())
    (args.output / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    request = {"caption": "English, piano pop, warm expressive lead vocal, soft drums, clear production",
               "lyrics": "[Verse]\nMorning light is on the window\nEvery road will lead me home\n[Chorus]\nLet the music carry us together\nWe will never walk alone",
               "cot": "off", "duration": args.frames / 25, "seed": 1234,
               "inference_steps": args.steps, "guidance_scale": 1.0,
               "semantic_sampling": {"min_tokens": args.frames, "max_tokens": args.frames}}
    fixed = json.loads(args.fixture.read_text())
    stream = fixed["semantic_tokens"].split(",")[:args.frames]
    if len(stream) != args.frames:
        raise ValueError("Fixture is shorter than the requested frame count")
    fixed.update(duration=args.frames / 25, seed=1234, lm_seed=1234, steps=args.steps,
                 semantic_tokens=",".join(stream), lm_batch_size=1, synth_batch_size=1)
    fixed.pop("source_tokens", None)
    report = {"frames": args.frames, "ode_steps": args.steps, "keep_loaded": True,
              "scope": "single A10G; fixed controls; numerical diagnostics are not listening judgments",
              "variants": {}}
    for quant in QUANTS:
        directory = args.output / quant
        model = args.models / f"YuE2-3B-{quant}.gguf"
        engine = Engine(args.library, model, args.models / "YuE2-Vae-F32.gguf", keep=True)
        try:
            cold = run(engine, request, directory / "cold")
            warm = [run(engine, request, directory / f"warm-{i}") for i in range(2)]
            if len({cold["audio_sha256"], *(row["audio_sha256"] for row in warm)}) != 1:
                raise AssertionError(f"Repeated same-request audio changed for {quant}")
            acoustic = run(engine, fixed, directory / "fixed-semantic")
        finally:
            engine.close()
        row = {"cold": cold, "warm": warm,
               "warm_pipeline_seconds_mean": float(np.mean([x["pipeline_seconds"] for x in warm])),
               "fixed_semantic": acoustic}
        identity = json.loads((directory / "cold/generation-status.json").read_text())
        if identity["lm"] != manifest["files"][model.name]["sha256"] or identity["vae"] != manifest["files"]["YuE2-Vae-F32.gguf"]["sha256"]:
            raise AssertionError("Engine component hashes differ from the verified source manifest")
        if quant != "BF16":
            ref = args.output / "BF16/fixed-semantic"
            row["fixed_semantic_latent_difference"] = metrics(np.load(ref / "latents.npy"), np.load(directory / "fixed-semantic/latents.npy"))
            row["fixed_semantic_wave_difference"] = metrics(np.load(ref / "audio.npy"), np.load(directory / "fixed-semantic/audio.npy"))
        if args.lm_probe:
            ids = [151643,22574,11,33897,2220,3122,11,8205,2990,25407,198,151847,151848,151851,153087,161729]
            prefix = directory / "lm"
            log = directory / "lm-probe.log"
            with log.open("w") as stream_log:
                subprocess.run([str(args.lm_probe.resolve()), "--device", "CUDA0", str(model), str(prefix),
                                *(str(i) for i in ids)], stdout=stream_log, stderr=subprocess.STDOUT, check=True)
            if quant != "BF16":
                row["lm_logits"] = {}
                for phase in ["prefill", "decode"]:
                    filename = f"lm_{phase}_0_logits.bin"
                    reference = np.fromfile(args.output / "BF16" / filename, dtype="<f4")
                    candidate = np.fromfile(directory / filename, dtype="<f4")
                    values = metrics(reference, candidate)
                    values["argmax_equal"] = bool(reference.argmax() == candidate.argmax())
                    row["lm_logits"][phase] = values
        report["variants"][quant] = row
        (args.output / "matrix.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"quant": quant, "warm_seconds": row["warm_pipeline_seconds_mean"]}), flush=True)
    print("Matrix complete; listening assessment and preset selection remain separate.", flush=True)


if __name__ == "__main__":
    main()
