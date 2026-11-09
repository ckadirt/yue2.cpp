"""Package a relocated native Cantor engine, with platform-specific load checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile


def output(*args):
    return subprocess.check_output(args, text=True)


def main():
    if sys.platform == "linux":
        from package_linux import main as linux_main
        return linux_main()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--backend", choices=["cpu", "metal", "vulkan"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-dirty", action="store_true", help="Local checks only")
    args = parser.parse_args()
    system = {"darwin": "macos", "win32": "windows"}.get(sys.platform)
    arch = {"AMD64": "x86_64", "x86_64": "x86_64", "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine())
    if not system or not arch or (args.backend == "metal" and system != "macos"):
        parser.error("Unsupported platform/backend")
    repo = Path(__file__).resolve().parents[2]
    commit = output("git", "-C", str(repo), "rev-parse", "HEAD").strip()
    dirty = bool(output("git", "-C", str(repo), "status", "--porcelain").strip())
    if dirty and not args.allow_dirty:
        parser.error("Refusing to package uncommitted source")
    if args.output.exists():
        parser.error("Refusing to overwrite an archive")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    build = args.build.resolve()
    windows = system == "windows"
    name = "cantor_engine.dll" if windows else "libcantor_engine.dylib"
    if windows and (build / "Release" / name).is_file():
        build /= "Release"
    prefix, suffix = ("", ".dll") if windows else ("lib", "*.dylib")
    files = [build / name]
    for stem in ["ggml-yue2", "ggml-base-yue2", "ggml-cpu*"]:
        matches = sorted(build.glob((prefix + stem + suffix).replace("**", "*")))
        if not matches:
            parser.error(f"Missing {stem} library")
        files += matches
    if args.backend != "cpu":
        matches = sorted(build.glob(prefix + "ggml-" + args.backend + suffix))
        if not matches:
            parser.error(f"Missing {args.backend} plugin")
        files += matches
    with tempfile.TemporaryDirectory(prefix="yue2-package-") as temporary:
        root = Path(temporary)
        for f in files:
            shutil.copyfile(f, root / f.name)
            (root / f.name).chmod(0o755)
        for f in ["LICENSE", "LICENSE.cantor-checkpoint"]:
            shutil.copyfile(repo / f, root / f)
        dependencies = {}
        if windows:
            exports = output("dumpbin", "/nologo", "/exports", str(root / name))
            names = re.findall(r"^\s+\d+\s+[0-9A-F]+\s+[0-9A-F]+\s+(\w+)", exports, re.M)
            for f in root.glob("*.dll"):
                needed = re.findall(r"^\s+([\w.-]+\.dll)\s*$", output("dumpbin", "/nologo", "/dependents", str(f)), re.M | re.I)
                dependencies[f.name] = needed
                for dependency in needed:
                    if dependency.lower().startswith("ggml") and not (root / dependency).is_file():
                        raise RuntimeError(f"Missing {dependency}")
        else:
            names = [line.split()[-1].removeprefix("_") for line in output("nm", "-gU", str(root / name)).splitlines() if line.split()]
            for f in root.glob("*.dylib"):
                needed = [line.strip().split(" (", 1)[0] for line in output("otool", "-L", str(f)).splitlines()[2:]]
                dependencies[f.name] = needed
                for dependency in needed:
                    if dependency.startswith(("/usr/lib/", "/System/Library/")):
                        continue
                    if not dependency.startswith(("@rpath/", "@loader_path/")) or not (root / Path(dependency).name).is_file():
                        raise RuntimeError(f"Unbundled dependency {dependency}")
        if not names or any(not n.startswith("cantor_engine_") for n in names):
            raise RuntimeError(f"Unexpected engine exports: {names}")
        env = dict(os.environ)
        for key in ["GGML_BACKEND_PATH", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"]:
            env.pop(key, None)
        subprocess.run([sys.executable, str(Path(__file__).with_name("smoke_backend.py")),
                        str(root), commit, args.backend], cwd=temporary, env=env, check=True)
        with tarfile.open(args.output, "x:gz") as archive:
            for f in sorted(root.iterdir()):
                archive.add(f, arcname=f.name, recursive=False)
    receipt = {"family": "yue2", "abi": 1, "os": system, "arch": arch, "backend": args.backend,
               "source_commit": commit, "source_dirty": dirty, "file": args.output.name,
               "bytes": args.output.stat().st_size, "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
               "dependencies": dependencies, "validation": "relocated ABI and CPU dispatch; no generation"}
    args.output.with_suffix(args.output.suffix + ".json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
