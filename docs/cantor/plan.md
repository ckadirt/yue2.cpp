# Implementation plan

Updated: 2026-11-09. Status: implementation, normalized-output validation,
fresh-process resume, reference checks, capacity tests, recipe selection and
portable archive publication are complete. Cantor PR #5 merged; CI and live
deployment verification passed. See `validation.md`, `presets.md`,
and the work log for exact evidence and limitations.

## Authorized scope and constraints

- Adapt the existing `ckadirt/yue2.cpp` fork to Cantor engine ABI v1.
- Use the existing persistent `/cantor/repos` and `/cantor/keys` layout.
- GPU compute has a **hard maximum lifetime of three hours per authorized
  session**. Terminate earlier when finished. No automatic renewal.
- Try L4; abandon a stalled allocation after about 3–4 minutes and use A10G.
  Confirm the old sandbox is terminated before mounting the volume again.
- Commit coherent milestones regularly, retain validation artifacts, and keep
  this record current so work survives connection loss or compute shutdown.
- Validate per-component **quality / balanced / speed** presets. Do not assume
  lower-bit weights run faster or that every component should be quantized.
- Publishing fork commits and preparing checkpoint hosting are authorized.
  Publish usable artifacts only after the relevant validation has passed.

## Milestones

1. **Inventory and preset design**
   - Pin source and GGUF revisions, exact sizes and hashes.
   - Inspect which weights are shared between the AR and NAR halves.
   - Benchmark BF16, Q8_0, Q6_K and Q5_K_M with the F32 VAE.
   - Select three user-facing presets from evidence; document unsupported
     combinations and quality limits.
2. **Native ABI and stages**
   - Export the existing Cantor ABI without changing its layout.
   - Family `yue2`; initial contiguous stages CODES → DIFFUSE → DECODE.
   - CODES owns optional ABC planning and semantic generation. Cantor PLAN
     currently means metadata/lyric preparation, not ABC composition.
   - Roles initially `lm` (both MoT experts) and `vae`; use the upstream GGUFs.
   - Support shared caption, lyrics, duration and inference controls.
   - Return planar stereo F32, samples per channel, at 48 kHz.
3. **Durable pause/resume**
   - Versioned, bounded, checksummed private state envelopes.
   - Include exact component hashes, canonical resolved request, runtime
     identity, token history, sampling position, and solver cursor/state.
   - Rebuild AR history with equivalent forwards and absolute Philox draw
     positions. Resume midpoint flow only at complete solver steps.
   - Decode cancellation may retry the immutable completed latent boundary;
     do not claim to checkpoint partial PCM.
   - Progress/cancellation at token, solver-step and VAE-tile boundaries.
   - Retain weights according to `keep_loaded`; always release request KV
     and graphs at durable boundaries. Report residency honestly.
4. **Build and packaging**
   - Add shared library with hidden internals and explicit exports.
   - Use family-specific GGML SONAMEs and `$ORIGIN`/platform equivalents.
   - Build CPU and CUDA first; prepare other supported platform workflows
     without claiming untested device validation.
5. **Validation**
   - Weightless ABI, malformed-request/checkpoint, hash, lifecycle tests.
   - Compare uninterrupted and pause/resume runs, including context recreation.
   - Compare tokenizer, AR, fixed-input NAR, and VAE against pinned reference.
   - Exercise changed prompts/seeds, consecutive requests, both residency
     modes, duration ceilings, errors and cancellation.
   - Measure peak VRAM and stage timings for short and long requests.
   - Retain playable English/Spanish and supplied-score examples for review.
6. **Distribution and Cantor registration**
   - Prepare model catalog and backend manifest fragments, with actual hashes.
   - Preserve licenses and source provenance when mirroring checkpoints.
   - Validate archives before hosting them. Never replace existing releases
     or public manifests with unvalidated artifacts.
   - Record exactly what was published and what remains pending.

## Capability boundary

The first generation adapter must accept supplied ABC scores. Recording-to-cover
requires SheetSage2/MERT and a host-compatible audio entry path; native upstream
support alone does not make it a working Cantor capability. Do not advertise
audio covers, stems, singer cloning, or automatic lyrics until implemented and
validated. Optional community tokenizers/adapters remain separate components.

## Current implementation state

- Local fork cloned at upstream `5a9500fd2979ab99fc82895877aadf8583acbabb`.
- Branch `cantor-abi-v1`; upstream remote configured.
- Token-resume/progress, midpoint-resume/progress, VAE progress, and CPU thread
  hooks compile with the ABI wrapper and family-specific shared libraries.
- Generic checkpoint codec and ABI header reuse the existing MiniMax adapter
  with its retained Apache license. CPU ABI/checkpoint tests pass.
- All five generation GGUF files are hash-verified; BF16/Q8/Q6/Q5 matrix saved.
- Stochastic fresh-process long-stream and score-planning resumes match exactly.
- Tokenizer, sampling distribution, acoustic noise RNG, AR, NAR and VAE reference
  checks pass. Native equal-seed draws differ from Torch on A10 because their
  valid CUDA RNG layouts differ; the diagnostic reproduces the cause exactly.
- Six-minute fixed-semantic capacity passed for BF16/Q8/Q5 on A10G.
- Final CPU and CUDA engine source is `25455ed8a916`; both immutable archives
  are publicly hash-verified on R2. Real Cantor 0.2.10 install/load/generate passed.
- An explicitly authorized three-hour A10G session ends no later than
  2026-11-09 23:05:54 UTC. Compute is finished; shutdown follows the final log push.
- Native supplied ABC works. App text extensions reject multiline input, so
  the catalog exposes score-mode choice and does not offer a broken ABC field.
