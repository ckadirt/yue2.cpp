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

## 2026-11-09 20:26 UTC — maximum-duration capacity and final adapter fixes

- All three 9,000-frame / six-minute fixed-semantic stress cases passed with
  retained weights and eight midpoint steps. Sampled device peaks: BF16
  **12,519 MiB**, Q8 **9,251 MiB**, Q5 **8,137 MiB**. These are capacity cases,
  not song-quality examples or isolated latency results. Receipts:
  `/cantor/validation/yue2/stress-360-01-{BF16,Q8_0,Q5_K_M}`.
- Proposed conservative catalog reservations: quality 16 GiB, balanced 12 GiB,
  speed 10 GiB. Generation uses the shared lm+vae roles only.
- Extracted the native percentile peak normalization into a shared helper and
  applied it to ABI PCM. A prior Spanish clip peaked at 1.04; the host otherwise
  clips samples directly. Preserve the native tool's output policy, with
  default `peak_clip=10`, and reject invalid bounds and embedded NUL text.
  CPU rebuild and both contract tests pass. GPU revalidation is still pending.
- Corrected the step-sweep harness to warm weights and graphs **before every
  comparison series**, then measure two exact-repeat runs per step count.
  Earlier 32-step timing included cold graph setup; retain it as historical
  data but do not compare it directly with warm 16/8-step timings.
- Added explicit backend external-dependency auditing and manifest preparation
  from pinned model assets and clean build receipts. Catalog fragments are
  drafts until final recipe and packaged-engine validation pass.
- Existing `/cantor/bin/cantor` is 0.2.10 and exports support for the duration
  extension. Use a separate private test directory and loopback relay for the
  final real-node check; leave the owner's normal node configuration untouched.

## 2026-11-09 20:44 UTC — final source frozen and CPU archive validated

- Final native source **`25455ed8a9164e4fced3e31ea5d239f99300890f`** pushed.
  CPU CI passed: https://github.com/ckadirt/yue2.cpp/actions/runs/42693475733.
  Recovered CPU archive SHA-256
  `66a0b88daa20b4da7e14b1b4aed7d39fe4f6003015d887fdd71a6ee1826425d1`,
  7,768,386 bytes. Real relocated CPU inference passed replay and eight-token
  AR generation through all stages, with finite normalized stereo PCM.
- CUDA build is still on **`f66260f`**, intentionally preserving its source
  identity while compiling reusable kernels. The persisted
  `/cantor/validation/yue2/post-build-04.sh` waits for that archive, fast-forwards
  to **`25455ed`**, rebuilds the adapter and probes, repackages, and runs final
  restart, timing, numeric-reference and multilingual validation.
- Active CUDA build: `/cantor/validation/yue2/portable-build-no-nccl-03.log`.
  Queued release driver: `/cantor/validation/yue2/post-build-04.log`.
- Prepared isolated real-node and immutable R2-upload helpers in this directory
  and on the volume. No backend or catalog has been published yet.
- Cantor catalog worktree: `.worktrees/cantor-yue2`, branch
  `feat/yue2-engine-20261109`, based on `0de557f`. Only its catalog draft is
  modified; the owner's main checkout and unrelated uncommitted edits are
  untouched. Asset checks pass. The ABC text control is capped at 3 KiB to fit
  the host's 4 KiB aggregate extension budget; the native ABI supports larger
  supplied scores subject to its token/context limits.
- The corrected 3 KiB catalog-generator limit is a local metadata change and
  will be committed with final evidence after binary packaging. Do not move the
  active GPU checkout ahead during the frozen release build.

## 2026-11-09 21:45 UTC — final release accepted and archives published

- Final binary source remains **`25455ed8a9164e4fced3e31ea5d239f99300890f`**.
  Portable CPU and CUDA archives both passed relocation, dependency audits,
  functional generation, and final reference/restart checks. CUDA includes
  SM86 SASS plus SM75/SM80 PTX; no NCCL dependency. See `validation.md`.
- Default recipes are **BF16 + F32 VAE + 32 steps**, **Q8_0 + F32 + 32**,
  and **Q5_K_M + F32 + 16**. Complete 30-second planned-song warm means:
  **13.9075 / 11.3948 / 8.0221 s**. Two repeat outputs per recipe match exactly.
- Eight steps measured 6.7394 s, but its planned-song waveform relative L2
  against 32 steps was 0.13647. The initially attempted acceptance correctly
  stopped before upload. Retained the 0.1 selection tolerance, checked the
  same song at 32 steps, and selected 16 (relative L2 0.03334). This is a
  numerical engineering proxy, not a human listening assessment.
- Both final stochastic fresh-process cases passed; all six final reference
  probes passed. Normalized English/Spanish/instrumental clips were saved for
  each chosen recipe, with extra 8-step and Q5/32 comparisons.
- Isolated Cantor **0.2.10** pull, backend installation/CUDA load, and generation
  passed: **719,936 stereo frames at 48 kHz** from a 15-second request. The first
  four-second test was rejected at admission; corrected the harness to the
  existing 15-second minimum. Owner configuration was not changed.
- Public CPU archive: 7,768,386 bytes,
  `66a0b88daa20b4da7e14b1b4aed7d39fe4f6003015d887fdd71a6ee1826425d1`.
  Public CUDA archive: 72,993,755 bytes,
  `c7420b1718589a1cc641d0e6da0fd803c0c13a88f4e74a01c55b0366d5125039`.
  Both are under `https://ckpts.cantorfm.com/backends/25455ed8a916/`, and full
  public bodies were hash-verified. Conditional writes replaced no old object.
  Weights stay at pinned upstream HF URLs; no new weight mirror was needed.
- Local full evidence: `artifacts/release-25455ed8a916/evidence/`; listening
  index: `artifacts/release-25455ed8a916/SAMPLES.md`. Private test-node keys and
  configuration were excluded from the evidence download.
- Registration: https://github.com/ckadirt/Cantor/pull/5, branch
  **`feat/yue2-engine-20261109-publish`**, latest commit **`c0981de`**. It is based
  on published main **`8d264cb`**, excluding six unrelated unpublished local
  commits. Only catalog/backends and a necessary CI runner-label repair change.
- Host text extensions reject newlines. Removed the proposed ABC app field;
  native ABI supplied-ABC support remains validated. Catalog controls are
  steps, guidance, and score mode. No recording covers or lyric writing.
- GitHub retired macOS 14 on November 2. Its CI job cancelled before any steps.
  Moved that entry to supported `macos-15`, retaining `macos-15-intel`, so CI
  can run all checks. Source: https://github.blog/changelog/2026-10-01-github-actions-macos-14-runner-image-retirement/.
- Remaining work: finish registration CI, merge/deploy, verify live manifests,
  record shutdown. No further GPU inference is needed. The session's enforced
  deadline remains **23:05:54 UTC**; stop it early after recovery notes are saved.
