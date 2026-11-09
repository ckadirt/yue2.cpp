"""Retain multilingual review clips or maximum-duration memory stress evidence."""
import argparse
import json
from pathlib import Path

from verify_engine import Engine, run

REVIEW = {
    "english-planned": {
        "caption": "English, piano pop, warm expressive lead vocal, acoustic piano, soft drums, 88 BPM",
        "lyrics": "[Verse]\nMorning light is on the window\nEvery road will lead me home\nThrough the quiet of the city\nI can hear a hopeful song\n[Chorus]\nLet the music carry us together\nWe will never walk alone",
        "cot": "full"},
    "spanish-planned": {
        "caption": "Spanish, acoustic Latin pop, warm expressive female vocal, nylon guitar, soft percussion, 92 BPM",
        "lyrics": "[Verse]\nLa mañana trae tu nombre\nEntre luces de la ciudad\nCada paso encuentra un ritmo\nCada sueño vuelve a empezar\n[Chorus]\nQue la música nos lleve\nDonde nace un nuevo sol\nCaminamos siempre juntos\nCon el mismo corazón",
        "cot": "full"},
    "instrumental": {
        "caption": "Instrumental, ambient cinematic piano, spacious strings, gentle evolving harmony, no vocals",
        "lyrics": "", "cot": "off"},
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--suite", choices=["review", "stress"], required=True)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--quants", default="BF16,Q8_0,Q6_K,Q5_K_M")
    parser.add_argument("--steps", type=int, default=32)
    parser.add_argument("--frames", type=int, default=9000)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    if args.suite == "stress":
        if not args.fixture or not 1 <= args.frames <= 9000:
            parser.error("stress needs --fixture and frames in [1,9000]")
        request = json.loads(args.fixture.read_text())
        source = request["semantic_tokens"].split(",")
        request.update(semantic_tokens=",".join(source[i % len(source)] for i in range(args.frames)),
                       duration=args.frames / 25, steps=args.steps, seed=1234, lm_seed=1234,
                       lm_batch_size=1, synth_batch_size=1)
        request.pop("source_tokens", None)
        requests = {"memory-stress": request}
    else:
        requests = {key: dict(value, duration=30, inference_steps=args.steps,
                             seed=2026, guidance_scale=1.0) for key, value in REVIEW.items()}
    manifest = json.loads((args.models / "cantor-source-manifest.json").read_text())
    results = {}
    for quant in args.quants.split(","):
        if quant not in {"BF16", "Q8_0", "Q6_K", "Q5_K_M"}:
            parser.error("Unknown precision")
        filename = f"YuE2-3B-{quant}.gguf"
        engine = Engine(args.library, args.models / filename, args.models / "YuE2-Vae-F32.gguf", keep=True)
        try:
            for name, request in requests.items():
                directory = args.output / quant / name
                receipt = run(engine, request, directory)
                identity = json.loads((directory / "generation-status.json").read_text())
                assert identity["lm"] == manifest["files"][filename]["sha256"]
                assert identity["vae"] == manifest["files"]["YuE2-Vae-F32.gguf"]["sha256"]
                results[f"{quant}/{name}"] = receipt
                (args.output / "profiles.json").write_text(json.dumps(results, indent=2) + "\n")
                print(json.dumps({"quant": quant, "case": name,
                                  "audio_seconds": receipt["audio_seconds"],
                                  "sampled_device_peak_mib": receipt["sampled_device_peak_mib"]}), flush=True)
        finally:
            engine.close()


if __name__ == "__main__":
    main()
