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

## 2026-11-09 23:50 UTC — mirror and fresh pulls complete; rollout pending CI

- All five pinned GGUFs, original LICENSE/README and a provenance manifest are
  public under `https://ckpts.cantorfm.com/yue2-1.0/`. Complete public SHA-256
  and byte-range checks passed. Local receipt `measurements/weights-published-08.json`.
- Real Cantor 0.2.10 pulled **all three presets from an empty store**, using
  actual public R2 model/backend URLs. Four unique blobs: **14,129,738,592 bytes**.
  Quality/Balanced/Speed pulls took 129.42/66.87/51.06 s; CPU installation passed.
  Candidate manifests/relay were loopback; no new generation was requested.
- Receipt: `measurements/node-r2-pull-11.json`. Raw logs are also local under
  `yue2.cpp/artifacts/distribution-20261109/node-r2-pull-11/`, with private config
  excluded. Removed only this test's duplicate `models/` after successful checks;
  source weights at `/cantor/models/yue2-source/` remain intact.
- Native matrix source **9061e660d79babd8accecd25b441f4179c26b7db**, run
  https://github.com/ckadirt/yue2.cpp/actions/runs/42722149204: eight targets
  passed; hosted CUDA compilation remains in progress. Do not call it passed yet.
- Published Linux ARM CPU (d43af5015d85), Linux Vulkan (7fd3f2455e86), Windows
  CPU (d43af5015d85), Windows Vulkan (4800780c7bd9), and corrected macOS CPU/Metal
  (9061e660d79b). Their public hashes are in `measurements/`.
- Initial Mac archives required 15.0. Held deployment, rebuilt for Cantor's
  14.0 target, and added a fatal check of every packaged library's Mach-O
  minimum OS. New Mac archives passed; the catalog proposal uses only those.
- Cantor PR #6, current head **6e1f4befea49d2f4c0f5c16b67371da42881761a**:
  R2 model URLs; Linux ARM/Vulkan and Mac CPU/Metal; tested Linux CPU/CUDA
  unchanged. Linux entries stay first for old nodes ignoring OS metadata.
  Remaining: finish exact-head registration CI, merge/deploy, verify live URLs.
- Windows native builds do not mean Windows node support. Mac default backend
  release-manifest wiring also remains separate. `host-gaps.md` contains concrete
  proposals awaiting user approval. Do not implement those under this task.
- CPU sandbox **sb-01M7197YE2XRAKHFB7WXES6JAF** still runs; hard three-hour
  timeout, conservative stop target **02:10:03 UTC**. No GPU allocated. Stop
  early once persistent/local recovery records are safe and remote work ends.

## 2026-11-10 00:12 UTC — R2 distribution live; compute stopped

- PR #6 merged as **89c3fdfbee1580f9317ede41864debcd51d5340d** after all
  checks on exact head **6e1f4befea49d2f4c0f5c16b67371da42881761a** passed:
  https://github.com/ckadirt/Cantor/actions/runs/42723113240.
- Both deployments passed: relay
  https://github.com/ckadirt/Cantor/actions/runs/42726164628 and site
  https://github.com/ckadirt/Cantor/actions/runs/42726164314.
- All four live JSON endpoints on `cantorfm.com` and `relay.cantorfm.com`
  exactly matched reviewed files at **00:12:06 UTC**. Receipts:
  `measurements/live-r2-site-14.json` and `live-r2-relay-14.json`.
- CPU sandbox was synced and terminated, observed **23:59:29 UTC**. No GPU was
  started for this follow-up. `cpu-session.json` is marked stopped. Persistent
  source checkout was fast-forwarded to pushed commit **3da00db** before stop;
  later report updates are on GitHub and can be fetched without rebuilding.
- Native pipeline still has one hosted CUDA compile in progress. Eight other
  targets passed. Deployment uses the original generation-tested CUDA archive,
  so no unverified build was promoted. Continue monitoring run **42722149204**;
  do not claim that last build passed until its final result is observed.
- No remote compute needs restarting to finish CI monitoring or report updates.
  Host changes proposed in `host-gaps.md` remain unimplemented pending approval.

## 2026-11-10 00:31 UTC — CUDA compile passed; CI packaging environment fixed

- Run **42722149204** completed CUDA compilation (428 Ninja steps) and both
  real ABI/checkpoint tests passed. Packaging then failed before producing an
  archive because Git rejected the container checkout's ownership. No failed
  or unverified archive was promoted; the deployed CUDA archive is unchanged.
- Fixed the container setup in **57692e2**: explicitly trust only the checked-out
  workspace and its ggml submodule, then verify exact HEAD and a clean status
  before spending time on compilation. This also ensures generated engine
  version metadata can read Git successfully.
- Added a bounded 2 GiB ccache with best-effort restore/save, including save on
  failure, so future retries can reuse compiled kernels. No cache contains
  keys or model weights. Cache operations cannot hide build/test failures.
- A fresh full native CI run is starting on this correction. Continue until
  CUDA packaging and the native matrix genuinely pass; do not report the failed
  run as passing. All R2/catalog/real-node follow-up checks are already live and
  verified. No remote compute needs restarting to finish GitHub CI.

## 2026-11-10 00:53 UTC — ownership preflight confirmed; final cold build running

- Corrected full matrix run **42729246878**, source
  **57692e2cca8fa7a3eaf3bebff680db77457be179**:
  https://github.com/ckadirt/yue2.cpp/actions/runs/42729246878.
- The CUDA job **129542744211** passed exact-commit/clean-checkout Git
  preflight and cache restore setup before starting compilation. The first
  run with the new cache is cold; it cannot reuse the earlier discarded build.
- All eight other native targets passed again. Remaining: CUDA build/test,
  packaging, archive upload. No claim of full matrix success until observed.
- The R2 rollout is live and all four public manifests were verified; compute
  remains stopped. No new instance or GPU is needed to monitor this job.
- Clarified the Mac manifest caveat: the current shared manifest has YuE2 Mac
  entries but lacks ACE-Step's release-built Mac entries. A default switch
  must preserve both families; that host/release wiring remains unimplemented
  and awaits approval.

## 2026-11-10 01:17 UTC — all authorized work completed

- Final native matrix **42729246878**, source
  **57692e2cca8fa7a3eaf3bebff680db77457be179**, finished **successfully**.
  All nine native targets passed; nine non-expired package artifacts exist.
  The optional manual-release job was correctly skipped on this push.
- CUDA compilation, both ABI/checkpoint tests, relocated archive packaging,
  artifact upload and compiler-cache save all passed. The trusted-checkout
  correction resolved the observed failure without weakening provenance checks.
- Saved `measurements/platforms-final-ci-15.json`, containing exact run/source,
  native job results and artifact IDs. The source/ABI checks do not claim
  full song generation on every new platform or accelerator.
- R2 weights, source notices, public hash/range checks, all-preset fresh real-node
  pulls, catalog merge/deployment and both-domain live checks are complete.
  Existing A10G-tested CUDA/CPU archives remain selected for Linux x86_64.
- All Modal compute remains stopped; the original persistent volume and local
  logs/samples are retained. No new instance or GPU is needed.
- Windows node implementation, combined default macOS release-manifest wiring,
  and recording-input/covers integration remain flagged proposals in
  `host-gaps.md`; none was silently implemented. They require user approval
  before further work. Automatic lyric writing is not a built-in supported
  YuE2 task; supplied lyrics remain the current generation input.
