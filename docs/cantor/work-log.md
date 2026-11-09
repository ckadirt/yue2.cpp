# YuE2 work log and recovery

## Recovery checklist

1. Read `plan.md`, `presets.md`, and the newest entry here before resuming.
2. Inspect local `yue2.cpp` branch/status and `/cantor/repos/yue2.cpp` before
   overwriting or pulling either copy. Preserve unrelated changes.
3. From `../gpu`, use its pinned Modal environment (`uv run ...`). Read the
   local Modal skill before interacting with the SDK.
4. Check named sandbox `cantor-node-session` in app `cantor-node`. Never mount
   the mutable `cantor-node` volume in two live sessions. A named sandbox can
   exist while GPU allocation is still pending; that is not readiness.
5. Session controller: `../gpu/yue2_session.py`; local receipt, when available:
   `../gpu/.codex/yue2-session.json`. Its server-side lifetime is 10,800 seconds.
   Verify the active instance and deadline; do not reset or extend it silently.
6. Keys stay in `/cantor/keys/.env`; never print values or put credentials in
   git URLs, manifests, output logs, or this record.
7. Commit and sync persistent work before stopping compute. Preserve the
   volume; terminate the sandbox when the work ends or at the deadline.

## 2026-11-09 — inventory and initial adaptation

- Confirmed all four main-model files and F32 VAE are already published.
  Exact revision, hashes, sizes, and provisional preset policy are in
  `presets.md`.
- User clarified that **quality / balanced / speed** must select combinations
  per component; choose the final balanced/speed main quant from measurements.
- Cloned public `ckadirt/yue2.cpp` locally, based on upstream `5a9500f`;
  branch `cantor-abi-v1`. Existing persistent checkout and key file confirmed
  through Modal volume metadata at `/cantor/repos/yue2.cpp` and
  `/cantor/keys/.env`. Key contents have not been printed.
- Read Cantor's ABI header and node integration guide. Important contracts:
  contiguous stage mask ending at DECODE; planar stereo; duration ceiling;
  optional `cantor_engine_duration` for opaque binary boundaries; separate
  GGML SONAMEs for each family; relocatable archive dependencies.
- Drafted optional hooks in `src/generate.h`, `src/nar.h`, `src/vae.h`, and
  `src/backend.h`. Added checkpoint codec/header/license and ABI header.
  **Not compiled or tested; no usable adapter yet.**
- Started a CUDA 12.8.1 development image and L4 allocation using
  `../gpu/yue2_session.py`. At **14:19:53 UTC**, sandbox
  `sb-aPAp5uOKX5qEsFlqqPRfbb` was discoverable, but no allocated container or
  successful GPU probe had been observed. The launcher had not written its
  completion receipt. Treat this as pending, not ready.
- User instructed fallback from stalled L4 allocation to A10G after about
  3–4 minutes. Next action: terminate/check the pending L4, then relaunch with
  A10G and the same three-hour hard limit; verify `nvidia-smi` before work.

### Next implementation actions

1. Commit this planning/checkpoint milestone, clearly marked incomplete.
2. Finish `src/cantor-abi.cpp` and CMake wiring.
3. Compile CPU adapter, add ABI/checkpoint tests, and correct draft hooks.
4. Build CUDA on the persistent checkout and verify downloaded model hashes.
5. Validate deterministic restart and quantization matrix; update these notes
   with actual results and commit each coherent milestone.

## 2026-11-09 — A10G ready; initial CPU checks passed

- Terminated stalled L4 `sb-aPAp5uOKX5qEsFlqqPRfbb`; launcher exited after
  termination. No L4 container was observed allocated.
- A10G allocated promptly: `sb-KAOORLiKNJml5mm4SnCh8D`.
  `nvidia-smi` confirms **NVIDIA A10, 23028 MiB**.
- Server-side lifetime: **10,800 seconds**. Client receipt time
  `2026-11-09T14:22:28.615230Z`; shutdown no later than
  **2026-11-09 17:22:28 UTC / 13:22:28 America/La_Paz**. Stop earlier on
  completion. Receipt: `../gpu/.codex/yue2-session.json`.
- Confirmed persistent checkout is clean. Credential variable names are
  `HF_TOKEN`, `GH_KEY`, and R2 connection variables. Values remain private.
- First documentation commit: `7e74f39` on local `cantor-abi-v1`.
- Implemented initial ABI wrapper and shared-library build, staged CODES /
  DIFFUSE / DECODE, private state codec, progress/cancellation hooks, and
  optional duration accessor. This implementation still needs GPU validation.
- CPU Debug build succeeded. CTest: **2/2 passed** (ABI invalid-input/lifecycle
  checks; checkpoint SHA-256 known vector, round trip, truncation/corruption).
  These are weightless checks, not numerical or full-model validation.
- ELF inspection confirms only `cantor_engine_*` exports, `$ORIGIN` RUNPATH,
  and family-specific `libggml-yue2.so.0` / `libggml-base-yue2.so.0` dependencies.
- Pinned download/verification script added at
  `yue2.cpp/tools/cantor/download_models.py`; running on the GPU session with
  files under `/cantor/models/yue2-source` and output at
  `/cantor/validation/yue2/download.log`. Completion not yet verified.
- Next: sync committed code to persistent checkout, CUDA build, verify all
  downloads, then exercise real generation and restart equivalence before
  selecting or publishing presets.
