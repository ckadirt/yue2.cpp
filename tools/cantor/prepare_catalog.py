"""Create reviewable Cantor manifest fragments from pinned assets and build receipts."""
import argparse
import json
from pathlib import Path

from download_models import FILES, REPO, REVISION


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend-receipt", type=Path, action="append", default=[])
    parser.add_argument("--backend-base", default="https://ckpts.cantorfm.com/backends")
    parser.add_argument("--speed-steps", type=int, default=16)
    parser.add_argument("--weights-base", default="https://ckpts.cantorfm.com/yue2-1.0")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    variants = []
    for tier, quant, steps, memory in [("quality", "BF16", 32, 16),
                                      ("balanced", "Q8_0", 32, 12),
                                      ("fast", "Q5_K_M", args.speed_steps, 10)]:
        components = []
        for role, filename, precision in [("lm", f"YuE2-3B-{quant}.gguf", quant),
                                           ("vae", "YuE2-Vae-F32.gguf", "F32")]:
            size, sha = FILES[filename]
            components.append({"role": role, "blob": f"sha256:{sha}",
                "url": f"{args.weights_base.rstrip('/')}/{filename}",
                "bytes": size, "quant": precision})
        variants.append({"tag": f"3b-{tier}", "components": components,
            "defaults": {"steps": steps, "cfg": 1.0},
            "needs": {"vram_bytes": memory * 1024**3, "backends": ["cuda12", "metal", "vulkan", "cpu"]},
            "stages": ["codes", "diffuse", "decode"],
            "lyrics": {"can_generate": False, "requires_lyrics": False, "instrumental_text": ""},
            "parameters": [
                {"kind": "integer", "key": "inference_steps", "label": "Steps", "default": steps,
                 "minimum": 1, "maximum": 200, "step": 1},
                {"kind": "number", "key": "guidance_scale", "label": "Guidance", "default": 1.0,
                 "minimum": 0, "maximum": 20, "step": 0.1},
                {"kind": "choice", "key": "cot", "label": "Score mode", "default": "full",
                 "choices": ["full", "melody", "off"]}],
            "capabilities": [], "acts": []})
    model = {"name": "yue2", "engine": "yue2", "licence": "CC-BY-NC-4.0", "variants": variants}
    (args.output / "catalog-fragment.json").write_text(json.dumps(model, indent=2) + "\n")
    if args.backend_receipt:
        backends = []
        seen = set()
        for path in args.backend_receipt:
            receipt = json.loads(path.read_text())
            if receipt["family"] != "yue2" or receipt["abi"] != 1 or receipt["source_dirty"]:
                raise ValueError("Backend receipt is not a clean YuE2 ABI-1 build")
            key = receipt["backend"], receipt["arch"], receipt.get("os", "linux")
            if key in seen:
                raise ValueError("Duplicate backend/architecture")
            seen.add(key)
            backends.append({"backend": key[0], "arch": key[1], "os": key[2], "bytes": receipt["bytes"],
                "sha256": receipt["sha256"],
                "url": f"{args.backend_base}/{receipt['source_commit'][:12]}/{receipt['file']}"})
        # Older Linux nodes ignore OS metadata and select the first arch match.
        backends.sort(key=lambda artifact: artifact["os"] != "linux")
        (args.output / "backends-fragment.json").write_text(json.dumps(
            {"name": "yue2", "abi": 1, "backends": backends}, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
