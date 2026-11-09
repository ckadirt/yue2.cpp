"""Package one relocatable Linux Cantor engine; preserve matching GGML SONAMEs."""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--backend", choices=["cpu", "cuda12", "vulkan"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-dirty", action="store_true", help="Local validation only; mark receipt as dirty")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit("Refusing to replace an existing backend archive")
    source_root = Path(__file__).resolve().parents[2]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source_root, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=source_root, text=True).strip())
    if dirty and not args.allow_dirty:
        raise SystemExit("Refusing to package uncommitted source; commit it or use --allow-dirty for local checks")
    build = args.build.resolve()
    files = [build / "libcantor_engine.so"]
    files += sorted(build.glob("libggml-yue2.so*"))
    files += sorted(build.glob("libggml-base-yue2.so*"))
    files += sorted(build.glob("libggml-cpu*.so*"))
    plugin = {"cpu": None, "cuda12": "cuda", "vulkan": "vulkan"}[args.backend]
    if plugin:
        selected = sorted(build.glob(f"libggml-{plugin}.so*"))
        if not selected:
            raise SystemExit(f"Missing {plugin} backend")
        files += selected
    if not files[0].is_file() or not list(build.glob("libggml-base-yue2.so.0")):
        raise SystemExit("Missing engine or SONAME-named GGML libraries")
    with tempfile.TemporaryDirectory(prefix="yue2-package-") as temporary:
        root = Path(temporary)
        for source in files:
            # Materialize symlinks by their required names so the node's
            # strict archive extractor need not accept symlink entries.
            shutil.copyfile(source, root / source.name)
            (root / source.name).chmod(0o755)
        for name in ["LICENSE", "LICENSE.cantor-checkpoint"]:
            shutil.copyfile(source_root / name, root / name)
        exports = subprocess.check_output(["nm", "-D", "--defined-only", str(root / "libcantor_engine.so")], text=True)
        names = [line.split()[-1] for line in exports.splitlines() if line.split()]
        if not names or any(not name.startswith("cantor_engine_") for name in names):
            raise SystemExit("Engine leaks non-ABI exports")
        dependencies = {}
        system = {"libc.so.6", "libm.so.6", "libdl.so.2", "libpthread.so.0", "librt.so.1",
                  "libstdc++.so.6", "libgcc_s.so.1", "ld-linux-x86-64.so.2", "ld-linux-aarch64.so.1"}
        allowed = system | {"cpu": set(), "cuda12": {"libcudart.so.12", "libcublas.so.12",
                              "libcublasLt.so.12", "libcuda.so.1"}, "vulkan": {"libvulkan.so.1"}}[args.backend]
        for library in root.glob("*.so*"):
            dynamic = subprocess.check_output(["readelf", "-d", str(library)], text=True)
            dependencies[library.name] = re.findall(r"Shared library: \[([^]]+)\]", dynamic)
            for needed in dependencies[library.name]:
                if needed.startswith("libggml") and not (root / needed).is_file():
                    raise SystemExit(f"Missing dependency {needed} for {library.name}")
                if not needed.startswith("libggml") and needed not in allowed:
                    raise SystemExit(f"Unmanaged external dependency {needed} for {library.name}")
            if "RUNPATH" in dynamic and "[$ORIGIN]" not in dynamic:
                raise SystemExit(f"Non-relocatable RUNPATH in {library.name}")
        # A clean interpreter loads the relocated engine and its CPU plugin.
        check = """import ctypes as C,sys,os
root=sys.argv[1]
engine=C.CDLL(os.path.join(root,'libcantor_engine.so'))
assert engine.cantor_engine_abi_version()==1
engine.cantor_engine_version.restype=C.c_char_p
assert engine.cantor_engine_version().decode().startswith(sys.argv[2][:7]), 'stale engine build identifier'
core=C.CDLL(os.path.join(root,'libggml-yue2.so.0'))
core.ggml_backend_load_all_from_path.argtypes=[C.c_char_p]
core.ggml_backend_load_all_from_path(os.fsencode(root))
core.ggml_backend_init_by_type.argtypes=[C.c_int,C.c_char_p]
core.ggml_backend_init_by_type.restype=C.c_void_p
cpu=core.ggml_backend_init_by_type(0,None)
assert cpu, 'relocated CPU plugin did not initialize'
core.ggml_backend_free.argtypes=[C.c_void_p]
core.ggml_backend_free(cpu)
"""
        env = dict(os.environ)
        env.pop("GGML_BACKEND_PATH", None)
        env.pop("LD_LIBRARY_PATH", None)
        subprocess.run([os.sys.executable, "-c", check, str(root), commit], env=env, cwd="/tmp", check=True)
        with tarfile.open(args.output, "x:gz") as archive:
            for file in sorted(root.iterdir()):
                archive.add(file, arcname=file.name, recursive=False)
    arch = {"aarch64": "arm64", "x86_64": "x86_64"}[platform.machine()]
    receipt = {"family": "yue2", "abi": 1, "backend": args.backend, "arch": arch, "os": "linux",
               "file": args.output.name, "bytes": args.output.stat().st_size, "source_dirty": dirty,
               "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
               "source_commit": commit, "dependencies": dependencies}
    args.output.with_suffix(args.output.suffix + ".json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
