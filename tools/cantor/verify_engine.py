"""Exercise the real Cantor C ABI, retaining stage receipts and restart evidence."""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import threading
import time
import wave

import numpy as np


class Component(C.Structure):
    _fields_ = [("role", C.c_char_p), ("path", C.c_char_p)]


class Options(C.Structure):
    _fields_ = [("vram_budget_bytes", C.c_uint64), ("keep_loaded", C.c_int),
                ("vae_chunk", C.c_int), ("vae_overlap", C.c_int), ("n_threads", C.c_int),
                ("disable_flash_attn", C.c_int), ("disable_batch_cfg", C.c_int)]


Progress = C.CFUNCTYPE(None, C.c_int, C.c_int, C.c_int, C.c_void_p)
Cancel = C.CFUNCTYPE(C.c_int, C.c_void_p)


class GPUMemory:
    """Sample device-wide memory at 200 ms intervals; no peak guarantee."""
    def __init__(self):
        self.peak_mib = None
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.sample, daemon=True)

    def sample(self):
        while not self.stop.is_set():
            try:
                result = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used",
                    "--format=csv,noheader,nounits"], text=True, stderr=subprocess.DEVNULL, timeout=5)
                value = int(result.splitlines()[0])
                self.peak_mib = max(self.peak_mib or 0, value)
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
            self.stop.wait(0.2)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join(timeout=6)


def state_sections(blob):
    """Diagnostic reader of this engine's private v1 envelope, not a host API."""
    if blob[:8] != b"YUE2ST01":
        raise ValueError("Unexpected checkpoint format")
    count = struct.unpack_from("<I", blob, 16)[0]
    sections = {}
    for i in range(count):
        kind, offset, size = struct.unpack_from("<I4xQQ", blob, 72 + i * 24)
        sections[kind] = blob[offset:offset + size]
    return sections


class Engine:
    def __init__(self, library, model, vae, keep=False, tile=512):
        self.lib = lib = C.CDLL(str(library.resolve()))
        lib.cantor_engine_load.argtypes = [C.POINTER(Component), C.c_size_t, C.POINTER(Options)]
        lib.cantor_engine_load.restype = C.c_void_p
        lib.cantor_engine_free.argtypes = [C.c_void_p]
        lib.cantor_engine_last_error.restype = C.c_char_p
        lib.cantor_engine_run_stage.argtypes = [C.c_void_p, C.c_int, C.c_void_p, C.c_size_t,
            C.POINTER(C.c_void_p), C.POINTER(C.c_size_t), Progress, Cancel, C.c_void_p]
        lib.cantor_engine_free_blob.argtypes = [C.c_void_p]
        lib.cantor_engine_audio.argtypes = [C.c_void_p, C.POINTER(C.c_int), C.POINTER(C.c_int)]
        lib.cantor_engine_audio.restype = C.POINTER(C.c_float)
        lib.cantor_engine_resident_bytes.argtypes = [C.c_void_p]
        lib.cantor_engine_resident_bytes.restype = C.c_uint64
        lib.cantor_engine_resident_modules.argtypes = [C.c_void_p]
        parts = (Component * 2)(Component(b"lm", os.fsencode(model)), Component(b"vae", os.fsencode(vae)))
        opts = Options(0, int(keep), tile, 16, 4, 0, 0)
        self.ctx = lib.cantor_engine_load(parts, 2, C.byref(opts))
        if not self.ctx:
            raise RuntimeError(lib.cantor_engine_last_error().decode())

    def close(self):
        if self.ctx:
            self.lib.cantor_engine_free(self.ctx)
            self.ctx = None

    def stage(self, stage, data, cancel_at=None):
        progress = []
        def report(s, done, total, _):
            progress.append((s, done, total))
        def stop(_):
            return int(cancel_at is not None and (cancel_at == 0 or
                (progress and progress[-1][1] >= cancel_at)))
        on_progress, on_cancel = Progress(report), Cancel(stop)
        source = C.create_string_buffer(data)
        output, length = C.c_void_p(), C.c_size_t()
        start = time.perf_counter()
        status = self.lib.cantor_engine_run_stage(self.ctx, stage, source, len(data),
            C.byref(output), C.byref(length), on_progress, on_cancel, None)
        elapsed = time.perf_counter() - start
        blob = C.string_at(output, length.value) if output else b""
        self.lib.cantor_engine_free_blob(output)
        if status < 0:
            raise RuntimeError(self.lib.cantor_engine_last_error().decode())
        receipt = {"stage": stage, "status": status, "seconds": elapsed, "progress": progress,
                   "blob_sha256": hashlib.sha256(blob).hexdigest(), "blob_bytes": len(blob),
                   "resident_modules": self.lib.cantor_engine_resident_modules(self.ctx),
                   "resident_weight_bytes": self.lib.cantor_engine_resident_bytes(self.ctx)}
        return status, blob, receipt

    def audio(self):
        count, rate = C.c_int(), C.c_int()
        ptr = self.lib.cantor_engine_audio(self.ctx, C.byref(count), C.byref(rate))
        if not ptr or rate.value != 48000 or count.value < 1:
            raise AssertionError("Missing 48 kHz stereo PCM")
        pcm = np.ctypeslib.as_array(ptr, shape=(count.value * 2,)).copy().reshape(2, count.value)
        if not np.isfinite(pcm).all():
            raise AssertionError("Non-finite PCM")
        return pcm


def write_audio(directory, audio):
    np.save(directory / "audio.npy", audio)
    interleaved = (np.clip(audio.T, -1, 1) * 32767).astype("<i2")
    with wave.open(str(directory / "audio.wav"), "wb") as file:
        file.setnchannels(2)
        file.setsampwidth(2)
        file.setframerate(48000)
        file.writeframes(interleaved.tobytes())


def run(engine, request, directory):
    directory.mkdir(parents=True, exist_ok=False)
    state = json.dumps(request, ensure_ascii=False).encode()
    (directory / "request.json").write_bytes(state)
    timings = []
    with GPUMemory() as gpu:
        for stage, name in [(2, "codes"), (3, "latents"), (4, "decode")]:
            status, state, receipt = engine.stage(stage, state)
            if status != 0:
                raise AssertionError("Unexpected pause")
            timings.append(receipt)
            if stage != 4:
                (directory / f"{name}.bin").write_bytes(state)
                sections = state_sections(state)
                if stage == 2:
                    np.save(directory / "semantic.npy", np.frombuffer(sections[3], "<i4") - 151853)
                    effective = json.loads(sections[1])
                    (directory / "effective-request.json").write_text(json.dumps(effective, indent=2, ensure_ascii=False) + "\n")
                    if effective.get("abc"):
                        (directory / "score.abc").write_text(effective["abc"])
                else:
                    np.save(directory / "latents.npy", np.frombuffer(sections[4], "<f4").reshape(-1, 64))
    audio = engine.audio()
    write_audio(directory, audio)
    result = {"stages": timings, "audio_seconds": audio.shape[1] / 48000,
              "pipeline_seconds": sum(t["seconds"] for t in timings),
              "audio_sha256": hashlib.sha256(audio.tobytes()).hexdigest(),
              "sampled_device_peak_mib": gpu.peak_mib, "memory_sample_interval_seconds": 0.2,
              "peak_abs": float(np.abs(audio).max()), "rms": float(np.sqrt(np.square(audio).mean()))}
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def smoke(args):
    request = {"caption": "English, warm piano pop, clear lead vocal", "lyrics": "[Verse]\nHello morning light",
               "cot": "off", "duration": 1.0, "seed": 42, "inference_steps": 2,
               "semantic_sampling": {"temperature": 0, "min_tokens": 25, "max_tokens": 25}}
    make = lambda keep=False: Engine(args.library, args.model, args.vae, keep, tile=16)
    engine = make()
    try:
        baseline = run(engine, request, args.output / "baseline")
    finally:
        engine.close()
    checks = {}
    for stage, source, cancel_at in [(2, json.dumps(request).encode(), 5),
        (3, (args.output / "baseline/codes.bin").read_bytes(), 1),
        (4, (args.output / "baseline/latents.bin").read_bytes(), 1)]:
        engine = make()
        try:
            status, checkpoint, paused = engine.stage(stage, source, cancel_at)
            if status != 1:
                raise AssertionError(f"Stage {stage} did not pause")
            (args.output / f"paused-{stage}.bin").write_bytes(checkpoint)
        finally:
            engine.close()
        engine = make()
        try:
            status, output, resumed = engine.stage(stage, checkpoint if checkpoint else source)
            if status != 0:
                raise AssertionError(f"Stage {stage} did not finish on recreated context")
            if stage < 4:
                expected = (args.output / ("baseline/codes.bin" if stage == 2 else "baseline/latents.bin")).read_bytes()
                equal = output == expected
            else:
                equal = np.array_equal(engine.audio(), np.load(args.output / "baseline/audio.npy"))
            if not equal:
                raise AssertionError(f"Stage {stage} restart differs from uninterrupted output")
            checks[str(stage)] = {"equal": equal, "paused": paused, "resumed": resumed}
        finally:
            engine.close()
    engine = make(keep=True)
    try:
        kept = run(engine, request, args.output / "kept-first")
        changed = dict(request, seed=43, caption="English, bright acoustic folk, soft drums")
        second = run(engine, changed, args.output / "kept-second")
        if kept["audio_sha256"] != baseline["audio_sha256"]:
            raise AssertionError("Retained and evicted weights produced different output")
        if second["audio_sha256"] == kept["audio_sha256"]:
            raise AssertionError("Changed request reused old output")
    finally:
        engine.close()
    report = {"restart_checks": checks, "baseline": baseline,
              "retained_weights_matches": True, "changed_request_differs": True}
    (args.output / "smoke-results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"smoke": "passed", "output": str(args.output)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--vae", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--keep-loaded", action="store_true")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.smoke:
        args.output.mkdir(exist_ok=False)
        smoke(args)
    else:
        if not args.request:
            parser.error("--request or --smoke is required")
        engine = Engine(args.library, args.model, args.vae, args.keep_loaded)
        try:
            print(json.dumps(run(engine, json.loads(args.request.read_text()), args.output)), flush=True)
        finally:
            engine.close()


if __name__ == "__main__":
    main()
