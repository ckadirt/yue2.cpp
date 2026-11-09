# Authorized distribution and platform follow-up

User approved checkpoint mirroring/catalog URLs and broader platform CI after
reviewing the delivery audit. Accepted native sampling differences and current
VRAM measurements; system RAM minimums are not a requirement. The user listened
to English, Spanish, and instrumental outputs and reported positive sound
quality. This is user listening feedback, not a formal blind evaluation.

## Plan

1. Follow the existing public bucket's family/version layout: `yue2-1.0/`.
   Mirror all five pinned generation GGUFs evaluated previously, plus original
   license/model-card notices and a source/hash manifest. Existing objects must
   never be replaced. Verify complete public bodies and HTTP range support.
2. Change only YuE2 component URLs in the catalog after those checks pass.
   Keep SHA-256, sizes, presets, and other model entries unchanged.
3. Build, test ABI/checkpoints, package and relocate-load on native CI runners:
   Linux x86_64 CPU/CUDA/Vulkan, Linux ARM64 CPU, macOS ARM64 CPU/Metal and
   Intel CPU, Windows x86_64 CPU/Vulkan. No GPU generation claim for hosted CI.
4. Retain receipts and publish only validated packages; preserve the known-good
   Linux generation engine until equivalent execution validation is available.
5. Record unresolved host/platform constraints and ask before expanding into
   Cantor node implementation changes. Stop the CPU session after mirroring.

## Session and recovery

- CPU only: `sb-01M716X7RQXN4P0CZCNSFEFQ6W`, volume `cantor-node` at `/cantor`.
- Created using `../gpu/node.py launch --minutes 180`; enforced three-hour
  maximum. No GPU allocated. Existing `../gpu/yue2_session.py` can exec/upload/
  download against the same named session; its stop command also syncs storage
  and terminates compute (its printed label still says GPU).
- Upload script: `yue2.cpp/tools/cantor/mirror_weights.py`.
- Remote log/receipt: `/cantor/validation/yue2/r2-mirror-08/`.
- Source weights: `/cantor/models/yue2-source/`; private keys stay in
  `/cantor/keys/.env` and are never downloaded or logged.
- Catalog worktree: `.worktrees/cantor-yue2`, branch
  `feat/yue2-r2-platforms-20261109`, based on published main `841fcea`.

## Initial CI findings

- Source `2697168`: Linux ARM64 passed. macOS/Windows compiled and ABI tests
  passed, then packaging checks caught a doubled wildcard and Windows's
  non-transitive DLL symbol resolution. Windows Vulkan configuration also
  lacked SPIR-V headers' CMake package. Corrections committed as `01ed720`;
  exact upstream SPIR-V header revision is pinned in the workflow.
- Native Windows engine packages do not imply a Windows Cantor node: the
  current host loader has no Windows DLL path. macOS nodes currently use a
  separate GitHub-release backend manifest. Flag these rather than changing
  node behavior under a model CI task.
- Upstream recording covers use transcription to ABC then regeneration;
  native support exists, but the Cantor audio-input path is not integrated.
  Built-in automatic lyric writing is not documented for YuE2.

## 2026-11-09 23:18 UTC — resumed CPU session and native checks

- User explicitly requested another restart. Prior CPU session was absent;
  restarted as `sb-01M7197YE2XRAKHFB7WXES6JAF`, 2 CPU/2 GiB RAM, no GPU.
  Enforced deadline: **2026-11-10 02:10:03 UTC**. Local receipt:
  `cpu-session.json`.
- R2 BF16 upload survived; its complete public body and HTTP byte-range probe
  passed. Other files continue sequentially. Remote durable log/receipt remain
  under `r2-mirror-08`; existing objects are checked and reused, never replaced.
- GitHub confirmed ARM Mac runner capacity shortages for the previous queued
  jobs. A subsequent run acquired runners and **both macOS ARM64 CPU and Metal
  passed**, including relocated loads. Windows CPU and Linux ARM64 CPU also
  passed. Final native source: `d43af5015d85a25bf4108ef3e8423f91f46599b0`;
  run https://github.com/ckadirt/yue2.cpp/actions/runs/42718837537.
- Fixed macOS MODULE `.so` packaging, source dirtiness caused by the generated
  Vulkan SDK folder, and macOS's exported static yyjson symbols (ABI-only export
  list). Linux implementation/numerics remain unchanged. Documentation-only
  pushes no longer trigger the entire matrix.
