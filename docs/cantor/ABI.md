# Cantor ABI v1 for YuE2

Status: CPU/CUDA generation, fresh-process resumes, reference checks, and real
Cantor 0.2.10 execution passed. See `validation.md`, `presets.md`, and the work
log for the pinned release, measured recipes, and known limits.

The public interface is `include/cantor_engine.h`. Family identity is `yue2`.
The shared library is `libcantor_engine.so` / `libcantor_engine.dylib` /
`cantor_engine.dll`; internals are hidden. Linux dependencies use YuE2-specific
GGML SONAMEs and `$ORIGIN`. Plugins are discovered beside the engine binary.

## Components and requests

Supply exactly one `lm` and one `vae` path. `lm` is the published backbone
GGUF containing both AR and NAR experts; it is not an AR-only checkpoint.
`vae` is the matching published F32 VAE. No separate text encoder or standalone
DiT file is required. Model hashes are cached once per context; component files
must remain immutable while a context is alive.

Example shared request:

```json
{
  "caption": "English, piano pop, warm lead vocal, soft drums",
  "lyrics": "[Verse]\nMorning light is on the window",
  "duration": 30,
  "seed": 42,
  "inference_steps": 32,
  "guidance_scale": 1.0,
  "cot": "full"
}
```

`style` is the native alias for `caption`; `description` and `tags` are fallback
aliases. `abc` supplies a score in `full` or `melody` mode. `cot="off"` skips
score planning. `semantic_tokens` supplies a bounded CSV stream for replay.
Native ABC/semantic sampling objects are accepted. `inference_steps` maps to
the acoustic solver and `guidance_scale` to semantic CFG. Explicit `lm_seed`
can differ from acoustic `seed`; otherwise one supplied seed controls both.
Supplied semantic tokens without a score use direct (`off`) conditioning;
the engine does not invent an unrelated score for a replay.

Supplied ABC is a native-API capability. The initial Cantor catalog does not
declare an ABC text field because the current host text-extension validator
rejects newlines. It does expose automatic score mode (`full`, `melody`, `off`).

Output uses the same percentile peak normalization as the native tool (default
`peak_clip=10`, range 0–999; zero selects ordinary peak normalization).
One request produces one song. Duration is bounded to 0.04–360 seconds and
also caps semantic frames at 25 Hz. This is an upper bound, not a guarantee
that the model reaches that length. Lyrics can be empty for the upstream
instrumental workflow; voice-free output is not guaranteed. The adapter does
not write lyrics. Source/reference audio, continuation, and LoRA requests
are not advertised or accepted in this initial adapter; use an external ABC
score for melody-conditioned generation.

## Stages and state

| Stage | Input | Output |
|---|---|---|
| CODES | Request JSON, or paused CODES envelope | Planned/supplied score tokens and semantic tokens |
| DIFFUSE | Complete CODES or paused DIFFUSE envelope | Acoustic latents from midpoint flow matching |
| DECODE | Complete DIFFUSE envelope | Context-owned planar stereo F32 at 48 kHz |

PLAN is not advertised: Cantor currently uses that stage for metadata/lyric
preparation. The advertised generation chain is contiguous from CODES to
DECODE. `cantor_engine_duration` is the optional ABI-1 extension used by the
node to check duration ceilings without parsing private state bytes.

State envelopes use magic `YUE2ST01`, explicit little-endian lengths and element
storage, a section directory, and whole-envelope SHA-256. They retain canonical
resolved requests, model identities, device/runtime identity, score/code
history, sampling cursor, and acoustic cursor/state. The host treats them as
opaque bytes. This is a new private state format; compatibility across different
engine revisions/backends is intentionally refused rather than guessed.
The envelopes also retain score/semantic token-cap indicators. A completed
stage may have reached its requested token cap; completion does not assert
that the composition reached a musical ending.

The native sampler keeps one stable Philox subsequence per vocabulary ID.
PyTorch's CUDA exponential kernel uses a GPU-dependent grid-stride layout;
equal seeds therefore do not promise the same full-vocabulary Torch song on
every GPU. This does not affect native same-build pause/resume equivalence.
`tools/cantor/diagnose_draw.py` checks the compact cuRAND sequence, reproduces
the device's Torch layout, and measures the native sampling distribution.

CODES resumes by rebuilding the AR cache with one-token forwards for the saved
history and restoring the absolute Philox sampling position. DIFFUSE resumes
at completed midpoint steps, retaining completed chunks. DECODE cancellation
returns PAUSED without partial PCM state: retry its unchanged complete DIFFUSE
input. Blob allocations are freed with `cantor_engine_free_blob`. Audio stays
valid until the next stage call or context destruction; sample count is per
channel.

## Residency and limits

`keep_loaded=0` evicts weight-owning modules after their stage use.
`keep_loaded!=0` retains them until context destruction. Request graph/scratch
state and KV are released at stage boundaries in either mode. Residency accessors
report loaded weight-buffer bytes and loaded module count; they are not peak
whole-device memory measurements.

`n_threads` and `disable_flash_attn` are wired. VAE chunk/halo values override
the upstream 512/16 defaults when nonzero. The byte-budget field does not yet
implement budget-based eviction, and `disable_batch_cfg` does not select a
separate CFG implementation. Retention therefore requires capacity for all
retained weights plus the current request's working memory.

## Validation tools

- `ctest --test-dir build --output-on-failure`: weightless ABI and state-codec
  checks, with assertions enabled even in Release builds.
- `tools/cantor/verify_engine.py --smoke ...`: real-ABI generation, recreated-
  context pause/resume, retained weights, and changed-request checks.
- `tools/cantor/benchmark_matrix.py ...`: fixed-control precision comparisons
  and saved listening artifacts. Numeric differences are not human judgments.
- `tools/cantor/package_backend.py ...`: immutable archive, export/dependency,
  relocated CPU initialization, and source-build identity checks.
