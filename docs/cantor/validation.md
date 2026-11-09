# YuE2 validation evidence

Updated 2026-11-09. Final CPU/CUDA engine validation passed; immutable archives
are published and publicly hash-verified. [Cantor PR #5](https://github.com/ckadirt/Cantor/pull/5)
merged as `841fcea11cdf4316feaf02037daf891c21fdd6e2`; deployment passed and both
live manifests exactly matched the reviewed data on 2026-11-09 at 22:05 UTC.
Full logs, private stage blobs, requests, and PCM are retained under
`/cantor/validation/yue2`. A local evidence snapshot is in
`yue2.cpp/artifacts/release-25455ed8a916/evidence/`. Private test-node keys and
configuration were excluded from that snapshot. No human listening judgment
is claimed by the agent. The user subsequently listened to English, Spanish,
and instrumental samples and reported positive sound quality; this is recorded
as user feedback, not a formal blind evaluation.

## Fixed-control precision comparison

The final isolated A10G matrix used 750 semantic frames (30 seconds), direct
conditioning, CFG 1, seed 1234, 32 midpoint steps, and retained weights. Warm
figures average two repeat runs with identical output hashes. Cold figures
include first-context component hashing, loading, and graph preparation.

| Main precision | Warm pipeline | Warm sampled GPU peak | Fixed-code latent relative L2 vs BF16 | Fixed-code wave relative L2 vs BF16 |
|---|---:|---:|---:|---:|
| BF16 | 10.218 s | 12,051 MiB | reference | reference |
| Q8_0 | 8.780 s | 8,853 MiB | 0.02057 | 0.03126 |
| Q6_K | 8.685 s | 8,027 MiB | 0.02961 | 0.03405 |
| Q5_K_M | 8.271 s | 7,721 MiB | 0.04869 | 0.06575 |

VAE source precision was F32 for every row. Native optimized convolution
weights are internally F16, with F32 activations; this is not a uniformly
FP32 decoder execution claim. Final PCM uses the native peak-normalization
policy. The historical 12-second matrix is retained in
[its summary](measurements/matrix-01-summary.json); the
[final summary](measurements/release-25455ed-summary.json) records final archive
identities, measurements, reference checks, and publication receipts.

## Complete preset recipes

With full score planning, the frozen 30-second English request took 13.91 s
for quality (BF16/32), 11.39 s for balanced (Q8/32), and 8.02 s for speed
(Q5/16), averaging two exact-repeat warm runs with retained weights.
First-context requests took 50.78 / 32.25 / 23.26 s, including SHA-256 identity
checks and graph preparation, with downloaded model files already present.

Independent warm solver sweeps kept semantic conditions fixed. Q5's acoustic
pipeline took 5.536 / 3.022 / 1.767 s at 32 / 16 / 8 steps. On a separate
identical planned song, 16 steps had waveform relative L2 **0.03334** and
cosine **0.99944** against 32; eight steps had relative L2 **0.13647**.
Eight steps averaged 6.74 s end to end, but exceeded the 0.1 numerical
tolerance chosen for the default. Sixteen is the speed recipe. These are
engineering proxies, not listening assessments.

## Capacity

Fixed semantic streams of 9,000 frames produced 359.9987 seconds of finite
48 kHz stereo PCM for BF16, Q8 and Q5. Eight midpoint steps were used for these
memory cases; they are not music-quality or isolated latency benchmarks.
Weights remained loaded. Device-wide memory was sampled every 200 ms, so
these figures do not guarantee the absolute transient peak.

| Main precision | Sampled device peak | Catalog reservation for the default recipe |
|---|---:|---:|
| BF16 | 12,519 MiB | 16 GiB |
| Q8_0 | 9,251 MiB | 12 GiB |
| Q5_K_M | 8,137 MiB | 10 GiB |

A final **full-pipeline** BF16/F32/32 quality run also passed: real automatic
score planning, 9,000 generated AR codes, 32 midpoint steps, and decode produced
**359.9987 seconds** of normalized stereo PCM in **320.2338 seconds** from a cold
context. Stage times were CODES **149.4895 s**, DIFFUSE **165.0409 s**, DECODE
**5.7035 s**. Sampled peak: **12,969 MiB**. Score planning ended naturally;
semantic generation was forced to its 9,000-code cap, so this measures sustained
generation and does not promise a natural musical ending. See the
[complete-duration receipt](measurements/full-360-quality-result.json).

The test host had 64 GiB RAM and four allocated CPUs. That supported CUDA
compilation and CPU F32 reference models; it is not a measured minimum host-RAM
requirement for native inference. Custom guidance/context settings can change
memory use; the engine's byte-budget field does not implement adaptive eviction.

## Restart and reference checks

- Native greedy and stochastic context-recreation smoke checks passed.
- Stochastic **fresh-process** smoke passed for 300 frames, paused at token
  257, and for full score planning paused after five score tokens. Completed
  CODES and DIFFUSE blobs matched byte for byte; decoded PCM matched exactly.
  Decode retries, retained weights, and changed-request handling passed.
- BPE matched 254 IDs exactly. Sampling distributions had relative RMS error
  below `6e-8`. Acoustic uniform noise matched exactly; normal noise relative
  RMS was `1.77e-7`.
- AR prefill/decode relative RMS was `0.0014–0.0030`, with matching argmax IDs.
  NAR velocity/ODE cases were below `0.0089`. Plain and tiled VAE cases were
  below `0.0038`. These passed the pinned upstream suite's thresholds.

The original full-vocabulary Torch token-draw test **does fail** on A10:
496 of 512 sampled IDs differ at equal seed. Its cause was reproduced exactly.
PyTorch assigns CUDA RNG words through 110,592 threads for the 184,704-entry
vocabulary; native upstream assigns one stable Philox subsequence per token
ID. A predictor of the device's Torch layout matched all 512 Torch draws.
The compact native/cuRAND comparison matched all 512 IDs, and 65,536 native
draws had total variation distance 0.013315 from the target distribution.
The native policy is preserved; equal-seed Torch songs across arbitrary GPUs
are not promised. See the pinned [PyTorch CUDA distribution implementation](https://github.com/pytorch/pytorch/blob/v2.10.0/aten/src/ATen/native/cuda/DistributionTemplates.h)
and `tools/cantor/diagnose_draw.py`.

## Portable CPU archive

CI for source `25455ed8a9164e4fced3e31ea5d239f99300890f` passed and produced
the 7,768,386-byte CPU archive with SHA-256
`66a0b88daa20b4da7e14b1b4aed7d39fe4f6003015d887fdd71a6ee1826425d1`.
After extracting it into a fresh directory, real-model CPU generation passed
both supplied-code replay and eight-token autoregressive generation through
DIFFUSE and DECODE. Output was finite, normalized planar stereo at 48 kHz.
CPU timings overlapped compilation and are not throughput benchmarks.
[Passing CI run](https://github.com/ckadirt/yue2.cpp/actions/runs/42693475733).

## Portable CUDA archive and real host

The clean CUDA archive is 72,993,755 bytes, SHA-256
`c7420b1718589a1cc641d0e6da0fd803c0c13a88f4e74a01c55b0366d5125039`.
It includes native SM86 code and SM75/SM80 PTX. GPU execution was tested on A10G;
other GPUs were not physically tested. Dependencies were audited against the
node's managed CUDA runtime; NCCL and OpenMP dependencies are disabled.
The matching family-specific GGML libraries load beside the relocated engine.

The final archive passed both fresh-process stochastic smoke cases. All six
reference probes were rerun against the final Release CUDA binaries and passed.
Normalized English, Spanish, and empty-lyrics instrumental clips were retained
for the selected recipes. An isolated **Cantor 0.2.10** node successfully pulled
the catalog entry, installed/loaded CUDA, and generated **719,936 stereo frames
at 48 kHz** from a 15-second request. The first four-second host test was
correctly rejected by Cantor's 15-second minimum and was retained as a failed
test setup, not counted as an engine failure or a pass.

## Distribution

- [CPU archive](https://ckpts.cantorfm.com/backends/25455ed8a916/yue2-engine-cpu-x86_64.tar.gz)
- [CUDA archive](https://ckpts.cantorfm.com/backends/25455ed8a916/yue2-engine-cuda12-x86_64.tar.gz)

Both public bodies matched the complete accepted SHA-256 hashes. Conditional
R2 writes created new immutable keys; existing assets were not replaced.
Weights retain their pinned public upstream identities and original
CC-BY-NC-4.0 terms. Existing quantizations were reused. The authorized follow-up
mirrored **all five evaluated generation GGUFs** to
`https://ckpts.cantorfm.com/yue2-1.0/`, with source license/model-card notices and
a provenance manifest. Complete public bodies and HTTP byte-range probes
passed. [Weight publication receipt](measurements/weights-published-08.json).
The catalog switch and additional validated native engine registrations are
in [PR #6](https://github.com/ckadirt/Cantor/pull/6); see the
[platform report](platforms.md) for OS coverage and host constraints.

The catalog exposes steps, guidance, and automatic score mode. Supplied ABC
remains a native-API feature: the current shared app text-extension contract
rejects newlines. Recording covers, singer references, and automatic lyric
writing are not advertised. Initial distributed targets are Linux x86_64 CPU
and CUDA 12. No macOS, Vulkan, or Windows engine is declared.

Registration CI passed all jobs after the retired macOS 14 runner was moved to
macOS 15. [Registration CI](https://github.com/ckadirt/Cantor/actions/runs/42705072014)
and [successful deployment](https://github.com/ckadirt/Cantor/actions/runs/42707918802).
The [live verification receipt](measurements/live-verification.json) checks both
public manifests against the reviewed files, including all existing entries.

For the exact boundary of node testing, CI coverage, RAM measurements, and
distribution, see the [delivery audit](delivery-audit.md). The node test used
Balanced/CUDA with two steps, loopback manifests, and pre-seeded model blobs;
it was not a clean public-download test of every preset and platform.
