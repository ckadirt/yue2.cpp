# YuE2 delivery audit

Checked 2026-11-09 against source, local raw evidence, GitHub CI, and the live
catalog/backend manifests. This audit makes the boundary of the delivered
integration explicit. The earlier completion summary was too broad if read
as completion of weight mirroring, all-platform releases, or every-preset
public-download end-to-end testing.

| Claim | Verified result |
|---|---|
| Cantor interaction API | Implemented native **Cantor C ABI v1** over the Serveurperso YuE2 C++ runtime: load/free, CODES/DIFFUSE/DECODE, stage checkpoints/resume, errors, audio access, and residency reporting. This work did not add a Supabase API, service, or Vault workflow. |
| Generation parity | Reference numerical checks and exact native restart/retry checks were run. These establish numerical agreement within recorded tolerances and native reproducibility; they do not establish identical complete songs to PyTorch at equal seeds. The original full-vocabulary Torch token-draw test fails on A10 due to different GPU RNG indexing. That exception is preserved in the validation report. No human listening assessment has been completed. |
| Checkpoints hosted on R2 | **Not completed.** R2 contains two engine archives, not the GGUF weights. All three main-weight URLs and the shared VAE URL in the live catalog still use pinned upstream Hugging Face files. Users can therefore still encounter Hugging Face download limits. |
| Memory measured and catalog updated | GPU VRAM was sampled on A10G. Catalog reservations are 16/12/10 GiB for Quality/Balanced/Speed. These are conservative reservations, not exact measured peaks. Minimum system DRAM/RAM was not measured; the test host had 64 GiB. |
| Capabilities registered | Text/style plus user-supplied lyrics, or empty-lyrics instrumental generation. `lyrics.can_generate=false`; lyrics are optional. No audio-input actions/capabilities are registered. Automatic score mode is exposed; it is not automatic lyric writing. Recording melody input, singer references, and recording covers are not integrated. Supplied ABC is supported in the native adapter but not exposed in the current app catalog. |
| CI/CD for every target | **Partial.** The new Cantor workflow builds/tests/packages Linux x86_64 CPU. CUDA was built, validated, packaged, and published from the GPU session. No new automatic CUDA release/publish job was added. No Cantor ABI release matrix for Linux ARM64, Windows, macOS, or Vulkan was completed. Inherited CLI workflows mentioning other platforms are not evidence of Cantor ABI releases on those platforms. |
| Catalog points at released engines | Yes: two immutable public R2 archives, Linux x86_64 CPU and CUDA 12. No other YuE2 target is advertised. Both complete public archive bodies were hash-verified during publication. |
| Node install/pull/generate on every variant | **Partial.** A real isolated Cantor 0.2.10 node successfully started, pulled Balanced, installed/loaded CUDA, and generated a 15-second stereo WAV using two solver steps. The test used loopback manifest/archive URLs, pre-seeded independently hash-verified model blobs, and cached CUDA runtime libraries. It did not exercise a fresh public-network checkpoint download, the production relay path, default 32-step Balanced generation through the node, or every preset/platform combination. |
| Native generation on selected presets | Yes: BF16/32, Q8_0/32, and Q5_K_M/16 were generated and measured on A10G, including English, Spanish, and instrumental samples. Additional portable-CPU short generation checks passed, but CPU throughput and every CPU ISA path were not individually benchmarked. |
| Local listening samples | Ten WAV files were found in the ignored artifacts evidence directory. They have now been copied to the visible workspace folder `audio-samples/yue2/`, with SHA-256 verification, descriptive filenames, a Markdown index, an HTML audio player, and a provenance manifest. These binaries are local artifacts, not Git-tracked repository files. |

## Evidence

- Native interface: `yue2.cpp/include/cantor_engine.h` and
  `yue2.cpp/src/cantor-abi.cpp`.
- [Detailed validation and limitations](validation.md),
  [preset decisions](presets.md).
- [Fresh live verification receipt](measurements/audit-live-verification.json):
  both manifests matched the reviewed files at **22:22:55 UTC**.
- [Live model catalog](https://relay.cantorfm.com/catalog/v1.json),
  [live backend catalog](https://relay.cantorfm.com/backends/v1.json).
- [Passing CPU Cantor ABI CI](https://github.com/ckadirt/yue2.cpp/actions/runs/42693475733).
  The actual workflow is `yue2.cpp/.github/workflows/cantor.yml`.
- Node test implementation: `verify_node.py`; raw logs and result are at
  `yue2.cpp/artifacts/release-25455ed8a916/evidence/node-release-04/`.
  Its result records `relay: loopback only` and reused immutable model bytes.
- [Local samples](../../audio-samples/yue2/README.md),
  [local audio player](../../audio-samples/yue2/index.html).

## Remaining work for the broader release described by the user

1. Mirror the three selected main GGUFs and shared VAE to R2, verify their
   complete public hashes, and update catalog component URLs.
2. Add Cantor ABI build/package/release jobs for the additional supported
   platform/backend targets, validating each before advertising it.
3. Exercise a clean real-node public download/install/generation for every
   selected preset and released backend, using each preset's default steps.
4. Measure system RAM separately from GPU VRAM and perform listening review.

This audit did not restart the GPU or change the live catalog. The completed
GPU session remains stopped; its persistent volume and local evidence remain.
