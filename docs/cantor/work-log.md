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

## 2026-11-09 — verified assets and retained-weight cleanup

- All five GGUF downloads completed and passed exact size/SHA-256 checks.
  Receipt: `/cantor/models/yue2-source/cantor-source-manifest.json`.
- Initial adapter commit `e1a273e` and its planning parent were transferred
  as a git bundle to `/cantor/repos/yue2.cpp`; remote branch `cantor-abi-v1`.
  GitHub push has not yet been verified.
- CUDA build uses `build-cuda`, CUDA 12.8.1, architecture 86, RelWithDebInfo,
  and dynamically loaded CPU/CUDA backends. Logs:
  `/cantor/validation/yue2/{cmake-cuda,build-cuda,ctest-cuda}.log`.
  At the last check, CUDA compilation had reached 147/212 tasks; no completion
  claim yet.
- PyTorch 2.10.0 cu128 and pinned reference dependencies installed under
  `/cantor/venvs/yue2-reference`; install log retained on the volume.
- Retained modules now have an explicit request-graph/scratch cleanup before
  freeing request KV, so `keep_loaded` retains weights without stale request
  references. CPU rebuild and both weightless tests passed again.
- Added `tools/cantor/verify_engine.py`: runs through the actual exported C
  ABI, saves requests/stage blobs/audio/timing receipts, and checks context-
  recreation resume for CODES, DIFFUSE, and DECODE, plus two requests with
  retained weights. This harness has only been syntax-checked so far.
- Local sandbox permissions changed during work. Modal reconnects require
  network-enabled execution; the authorized A10G and original deadline remain
  unchanged. No new compute session was launched.

## 2026-11-09 — interrupted CUDA compilation; bounded recovery

- The A10G sandbox disappeared from named lookup before the deadline.
  Inspecting its exact ID returned **exit code 137** and no sandbox stderr.
  This is consistent with a memory kill, but the provider did not supply a
  more specific cause. CUDA compilation was near task 167/212 at the previous
  check. No generation had started.
- Official reference source and checkpoints finished downloading before that
  interruption: `/cantor/repos/YuE` at `1116bea...`, and
  `/cantor/repos/yue2.cpp/checkpoints/{YuE2-3B,YuE2-Vae}` at the revisions in
  the inspection report. The reference environment install also completed.
- Recovery script: `recover_session.py` in this directory. It refuses duplicate
  mounts, reuses the cached CUDA image, requests A10G with **64 GiB host RAM**,
  and limits startup to four minutes. Subsequent compilation must use `-j 2`.
- **Original task deadline remains 17:22:28 UTC.** Recovery calculates a shorter
  server timeout from that deadline with a five-minute reserve. It does not
  start a fresh three-hour allowance. New receipt goes to `session.json`.
- Hardened the checkpoint parser against an empty directory and added
  checksummed malformed-directory tests for empty, overlapping, and overflowed
  ranges. Device description is now part of resume runtime identity.
- CPU rebuild/tests passed after those changes. Restricted local execution
  needs `CCACHE_DIR=/tmp/cantor-yue2-ccache` to avoid writing outside the allowed
  workspace. The source changes have not been pushed to GitHub yet.

## 2026-11-09 — recovery verified; fork backed up

- Recovery is live at **`sb-GMrcw2FVWis3eUe0Z71VP7`**, A10G / 64 GiB requested
  host RAM. Receipt: `session.json`. Ready at **14:44:08 UTC**, with a
  **9308-second** server lifetime; its conservative upper bound is 17:19:17 UTC,
  before the original 17:22:28 deadline.
- Verified the GGUF manifest, source checkout, official checkpoints, and
  reference environment survived. Reference import reports Python 3.12.15,
  NumPy 2.2.6, and **PyTorch 2.10.0+cu128**.
- CUDA compilation resumed at `-j 2`; new log is
  `/cantor/validation/yue2/build-cuda-recovery.log`. It has not completed yet.
- **Pushed commits through `d23a566`** to
  `https://github.com/ckadirt/yue2.cpp/tree/cantor-abi-v1` using the existing
  volume credential via a temporary askpass helper. No token in git URLs/logs.
- Added generation receipts with sampled device memory, semantic arrays,
  acoustic arrays, and score export to the real-ABI harness.
- Added a Linux archive packager and a read-only CPU ABI CI workflow. The
  packager checks exports, matching GGML dependencies, relocatable RUNPATH,
  and initializes the CPU backend after relocation in a clean interpreter.
  Local Debug archive relocation passed; no release archive was published.
- Fixed backend discovery for a dlopened library: resolve plugins beside the
  engine DSO rather than assuming the host executable or working directory.
  `GGML_BACKEND_PATH` in this GGML version denotes a library file, not a
  directory, so the harness no longer sets it incorrectly.
- CPU rebuild and both tests passed with the discovery fix. Next milestone:
  commit/sync these changes, finish CUDA build, then run real-model smoke,
  restart equivalence, and preset measurements.

## 2026-11-09 — CUDA build and first inference

- CUDA build finished and its weightless CTest suite passed **2/2**.
  The CPU CI run also passed:
  `https://github.com/ckadirt/yue2.cpp/actions/runs/42639895538`.
- First GPU smoke produced finite 48 kHz stereo audio and reported equal
  resumed outputs, but its cancellation helper emitted a Python callback
  exception when progress was still an empty list. **Do not count that run as
  clean validation.** Retained artifacts/log: `/cantor/validation/yue2/smoke-q8-01*`.
- Fixed callback return typing and require evidence that the requested pause
  boundary was actually reached. Added a stochastic mode to exercise absolute
  Philox positions, not just greedy token selection.
- Added monotonic progress checks. Adapter CODES progress now accounts for
  both planning and semantic phases instead of resetting the same stage's
  counter when planning completes.
- Supplied semantic replay without ABC now correctly uses direct conditioning
  and skips unnecessary AR weight loading; it does not plan a new unrelated
  score. Added explicit score/semantic truncation indicators to saved state.
- Added `benchmark_matrix.py` for equal-control BF16/Q8/Q6/Q5 comparisons and
  `step_sweep.py` to measure step-count changes separately. Neither has run yet.
- CPU rebuild and both tests passed after these changes. Next: commit/sync,
  rebuild only the adapter, rerun clean greedy and stochastic GPU smoke,
  then run numeric reference and preset comparisons on an otherwise idle GPU.

## 2026-11-09 — clean context-recreation checks passed

- Commit **`a16b4ec`** pushed to the fork and rebuilt on A10G.
- Clean greedy smoke **passed**, with no callback errors:
  `/cantor/validation/yue2/smoke-q8-02/smoke-results.json`.
- Clean stochastic smoke **passed**, exercising the sampler cursor:
  `/cantor/validation/yue2/smoke-q8-stochastic-01/smoke-results.json`.
- Both checked byte-identical completed CODES/DIFFUSE envelopes after context
  recreation, exact decoded PCM after decode retry, equivalence between
  evicted and retained weights, and changed output on a changed request.
  These were 25-frame, 2-step short checks, not song-quality benchmarks.
- Expanded the harness to resume in a **fresh interpreter process**, test a
  longer stream/cache boundary, and accept full planning mode. Those expanded
  tests have not run yet.
- Hardened request integers against narrowing overflow and non-finite nested
  sampling values; added invalid-input cases. Cantor omits absent optional
  fields and its app seed bound is below the native signed-64-bit limit.
- CPU tests still pass. Next: commit/sync these focused changes, run fresh-
  process long/planning checks, then equal-control precision and reference
  comparisons. Do not publish preset claims before those measurements.

## 2026-11-09 15:37 UTC — fresh-process long-stream check passed

- **`70a8a7c`** pushed, CUDA adapter rebuilt, and both CPU/GPU contract tests
  passed. Portable CPU CI passed at
  https://github.com/ckadirt/yue2.cpp/actions/runs/42645566449.
- `smoke-q8-fresh-long-01` passed with stochastic sampling, 300 frames,
  cancellation at token 257, and new interpreter processes for each resume.
  Completed CODES/DIFFUSE envelopes and decoded PCM are exactly equal to
  uninterrupted output. Retained weights and changed-request checks pass.
- Full score-planning fresh-process smoke is still running. Equal-control
  four-precision matrix, separate 32/16/8-step sweep, and seven pinned-reference
  probes are queued behind its successful completion. They have not passed yet.
- Added portable Linux build recipe in **`0df59c6`**. CUDA uses
  `75-virtual;80-virtual;86-real`, CPU runtime variants, and no OpenMP dependency.
  A second build is queued after timing measurements. Do not distribute the
  current SM86-only development binary as a general CUDA backend.
- Prepared English/Spanish planned-song and empty-lyrics instrumental review
  requests for all four precisions. Listening approval remains separate from
  numeric diagnostics; no presets or artifacts have been published yet.
- Original shutdown deadline remains unchanged. Current sandbox expires before
  17:22:28 UTC; do not extend it or relaunch another three-hour session.

## 2026-11-09 20:15 UTC — explicitly authorized second session

- The previous sandbox expired. User explicitly requested another instance.
  New A10G **`sb-HPDyMosvKKNkcy6HFxs0HV`**, 64 GiB host RAM, persistent
  `cantor-node` volume. Hard timeout 10,800 seconds; client deadline
  **2026-11-09 23:05:54 UTC / 19:05:54 Bolivia**. Stop earlier when finished.
- Recovery found completed four-precision matrix and 32/16/8-step sweep,
  both fresh-process smoke passes, and six successful reference probes.
  Raw receipts/logs were copied locally under `artifacts/recovery-02/`.
- Full-vocabulary `test-draw.py` fails 496/512 IDs on A10. Diagnosed and
  reproduced the exact cause: PyTorch uses 110,592 CUDA threads for its
  184,704-entry vocabulary, reusing Philox words through a grid-stride loop;
  native upstream uses one stable subsequence per vocabulary ID. Compact
  reference matched all 512 draws; 65,536 native draws had total variation
  distance 0.013315 from the expected probabilities. The layout predictor
  reproduced all 512 full-vocabulary PyTorch draws. Preserve native seed
  behavior and document that equal-seed Torch generation is not promised.
- BF16/Q8/Q6/Q5 warm 12-second pipelines: 4.256 / 3.582 / 3.587 / 3.439 s
  at 32 steps. Q8 fixed-code latent relative L2 is 0.01549; Q6/Q5 about 0.067.
  These are short synthetic-control measurements, not listening judgments.
- English/Spanish/instrumental BF16 and Q8 review clips completed; Q6/Q5 were
  interrupted and need completion.
- Found an unwanted NCCL dependency in the portable CUDA configuration.
  Explicitly disable it: Cantor's managed CUDA runtime supplies cudart/cuBLAS,
  not NCCL. Rebuild and audit dependencies before publication.
