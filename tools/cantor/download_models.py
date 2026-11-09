"""Download and verify the pinned Serveurperso generation matrix; no requantization."""
import argparse
import hashlib
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import hf_hub_download

REPO = "Serveurperso/YuE2-GGUF"
REVISION = "e630f2b8f6aedf8254c3186438633c1b5eeaf80a"
FILES = {
    "YuE2-3B-BF16.gguf": (7166072352, "668ca9ffa4622449916aae5068b5737363e7ec186a824cd3d7a1a8a95269f166"),
    "YuE2-3B-Q8_0.gguf": (3810232064, "41121ce97786d7795a325bcf123ca196956c03bb252c9e75384cfc1f2fc19e6b"),
    "YuE2-3B-Q6_K.gguf": (2943331072, "42068d5e57713df11b9f6a5a3751072d9bbefe231d1d088f9c100e026ffa4ef9"),
    "YuE2-3B-Q5_K_M.gguf": (2622936832, "cd3efd250b734a229172800f08f33a893ad1f66b521666e176cdae4a0729b281"),
    "YuE2-Vae-F32.gguf": (530497344, "93e49dfb1970e89ad64cacb17cf13b5d05f6bb30ef7ed3adae3050bcb728638a"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    def download(name):
        path = Path(hf_hub_download(REPO, name, revision=REVISION, local_dir=args.output))
        size, expected = FILES[name]
        if path.stat().st_size != size:
            raise ValueError(f"Size mismatch: {name}")
        sha = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                sha.update(chunk)
        if sha.hexdigest() != expected:
            raise ValueError(f"SHA-256 mismatch: {name}")
        print(f"Verified {name} ({size} bytes)", flush=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(download, FILES))
    for name in ["README.md", "LICENSE"]:
        hf_hub_download(REPO, name, revision=REVISION, local_dir=args.output)
    manifest = {"source": REPO, "revision": REVISION,
                "files": {name: {"bytes": value[0], "sha256": value[1]} for name, value in FILES.items()}}
    (args.output / "cantor-source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
