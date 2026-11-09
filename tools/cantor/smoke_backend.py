"""Load a relocated engine, CPU backend, and selected plugin without models."""
import ctypes as C
import os
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
if sys.platform == "win32":
    dll_directory = os.add_dll_directory(str(root))
    # Hosted Windows runners lack graphics-driver Vulkan Runtime installs.
    # CI supplies the hash-pinned standard loader as an external prerequisite.
    if os.environ.get('CANTOR_VULKAN_RUNTIME_DIR'):
        vulkan_runtime_directory = os.add_dll_directory(os.environ['CANTOR_VULKAN_RUNTIME_DIR'])
    engine_name, core_name = "cantor_engine.dll", "ggml-yue2.dll"
elif sys.platform == "darwin":
    engine_name, core_name = "libcantor_engine.dylib", "libggml-yue2.dylib"
else:
    engine_name, core_name = "libcantor_engine.so", "libggml-yue2.so.0"
engine = C.CDLL(str(root / engine_name))
assert engine.cantor_engine_abi_version() == 1
engine.cantor_engine_model.restype = C.c_char_p
assert engine.cantor_engine_model() == b"yue2"
engine.cantor_engine_version.restype = C.c_char_p
assert engine.cantor_engine_version().decode().startswith(sys.argv[2][:7]), "Stale build"
core = C.CDLL(str(root / core_name))
core.ggml_backend_load_all_from_path.argtypes = [C.c_char_p]
core.ggml_backend_load_all_from_path(os.fsencode(root))
core.ggml_backend_init_by_type.argtypes = [C.c_int, C.c_char_p]
core.ggml_backend_init_by_type.restype = C.c_void_p
cpu = core.ggml_backend_init_by_type(0, None)
assert cpu, "Relocated CPU dispatch failed"
base_name = {"win32": "ggml-base-yue2.dll", "darwin": "libggml-base-yue2.dylib"}.get(sys.platform, "libggml-base-yue2.so.0")
base = C.CDLL(str(root / base_name))
base.ggml_backend_free.argtypes = [C.c_void_p]
base.ggml_backend_free(cpu)
if sys.argv[3] != "cpu":
    plugin = {"cuda12": "cuda", "metal": "metal", "vulkan": "vulkan"}[sys.argv[3]]
    filename = {"win32": f"ggml-{plugin}.dll", "darwin": f"libggml-{plugin}.so"}.get(sys.platform, f"libggml-{plugin}.so")
    C.CDLL(str(root / filename))
print("Relocated ABI, CPU dispatch, and selected plugin load passed")
