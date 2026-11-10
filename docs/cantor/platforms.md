# Native engine platform delivery

This follow-up adds native build/ABI/package checks and public engine archives.
PR #6 is merged and deployed; both public domains matched the reviewed
manifests on 2026-11-10 at 00:12:06 UTC.
It does not claim model generation on every OS or accelerator. Existing A10G
generation and Linux CPU short-generation evidence remains in [validation](validation.md).

| Platform/backend | Build, ABI, checkpoint and relocation result | Distribution |
|---|---|---|
| Linux x86_64 CPU | Passed | Existing generation-checked `25455ed8a916` stays in catalog |
| Linux x86_64 CUDA 12 | Existing archive generation-tested on A10G; new hosted CI build in progress | Existing `25455ed8a916` stays in catalog |
| Linux ARM64 CPU | Passed on native ARM runner | R2 `d43af5015d85`; live through PR #6 |
| Linux x86_64 Vulkan | Passed | R2 `7fd3f2455e86`; live through PR #6 |
| macOS Intel CPU | Passed; every packaged library targets at most macOS 14.0 | R2 `9061e660d79b`; live through PR #6 |
| macOS Apple Silicon CPU | Passed; every packaged library targets at most macOS 14.0 | R2 `9061e660d79b`; live through PR #6 |
| macOS Apple Silicon Metal | Passed, including selected plugin load and minimum OS check | R2 `9061e660d79b`; live through PR #6 |
| Windows x86_64 CPU | Passed, including DLL relocation and CPU dispatch | R2 `d43af5015d85`; engine archive only |
| Windows x86_64 Vulkan | Passed with the standard Vulkan loader prerequisite | R2 `4800780c7bd9`; engine archive only |

Receipts: [initial platform acceptance](measurements/platforms-acceptance-09.json),
[six public archives](measurements/platforms-published-09.json),
[Linux Vulkan publication](measurements/vulkan-published-10.json).
Corrected [macOS 14 publication](measurements/macos14-published-13.json) and
[native acceptance](measurements/macos14-acceptance-13.json);
[Windows Vulkan publication](measurements/windows-vulkan-published-12.json).
The first macOS archives defaulted to 15.0; PR #6 was held until corrected
14.0-targeted archives passed and were selected. They run CI on macOS 15;
physical macOS 14 song generation has not been tested.

The original catalog's Linux CPU/CUDA archives remain pinned to the builds
that were exercised with real model generation. Additional targets were built
and tested by native GitHub runners. Metal/Vulkan/CUDA plugin presence and
library loading do not establish song generation or performance on a GPU.

## Host constraints left explicit

- Released macOS nodes read a GitHub-release-specific backend manifest by
  default. The shared manifest in PR #6 contains the new macOS engines;
  the existing `backends_url` setting accepts custom manifests. The shared
  manifest lacks ACE-Step's Mac release entries, so switching it wholesale
  would omit fresh ACE-Step installation on Mac. The proposed combined
  manifest must preserve both families. Default release-manifest wiring was
  not changed under this model task; see [host gaps](host-gaps.md).
- A Windows native engine DLL is not a Windows node release. Cantor's current
  node has no Windows DLL-loading path. Windows engine artifacts are available
  for development, but Windows is not advertised in the shared Cantor manifest.
  Windows CPU builds currently require AVX2 and the standard MSVC runtime.
- Windows Vulkan requires `vulkan-1.dll`, normally supplied by graphics-driver
  Vulkan Runtime installation. The CI environment now supplies the official
  LunarG 1.4.309.0 components with verified SHA-256
  `7d969f4d7b44e387667d3148f61559497c22d50cbe3d50adc9e5409afbce2df1`.
  This is a CI prerequisite, not a bundled driver or a Cantor node change.

## Reproducing and releasing

`.github/workflows/cantor.yml` in the fork builds native targets on push/PR
and by manual dispatch. It runs the actual C ABI/checkpoint tests, audits
exports/dependencies, packages normal files (no archive symlinks), and loads
the relocated archive libraries in a fresh process. Per-file receipts contain
OS, architecture, backend, source commit, dependency names, size and SHA-256.

Manual dispatch with `publish_release=true` publishes an immutable full-commit
GitHub release only after all jobs pass. Existing release assets are never
clobbered. `tools/cantor/fetch_platform_artifacts.py` recovers only packages
whose native CI job passed; `publish_backends.py` preserves conditional
no-overwrite R2 publication with complete public-body verification.
The inherited CLI release workflow skips `cantor-*` tags so it cannot package
unrelated CLI targets into these releases. That legacy CLI release path is
not part of this validated Cantor ABI matrix.
