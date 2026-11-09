# YuE2 for Cantor

The fork implements Cantor engine ABI 1 with CODES → DIFFUSE → DECODE.
Validated Linux x86_64 CPU/CUDA binaries are built from `25455ed8a916`.

- [Selected presets and timings](presets.md)
- [Validation, artifacts, and limitations](validation.md)
- [Delivery audit and remaining gaps](delivery-audit.md)
- [Current distribution follow-up](follow-up.md)
- [Native platform delivery](platforms.md)
- [Native ABI contract](ABI.md)
- [Implementation plan](plan.md)
- [Recovery log](work-log.md)
- [Model inspection](../yue2-model-inspection.md)

Generation uses the published MoT `lm` file plus the F32 VAE. Quality is BF16
with 32 steps; balanced is Q8_0 with 32; speed is Q5_K_M with 16. Native supplied
ABC works; the app catalog currently exposes automatic score mode because its
text-extension contract rejects multiline input. Audio covers and lyric writing
are not advertised.

The `ops/` scripts preserve this task's recovery and publication procedure.
They read credentials from `/cantor/keys/.env` at runtime and never embed them.
Another GPU launch requires fresh user authorization; never renew an expired
three-hour allocation automatically.

Full requests, state, numeric outputs, and WAVs remain on the persistent Modal
volume under `/cantor/validation/yue2`. Local copies are under
`artifacts/release-25455ed8a916/`; `SAMPLES.md` there is a listening index.
These generated audio artifacts are intentionally not tracked in Git.

Registration: https://github.com/ckadirt/Cantor/pull/5.

For this local multi-repo workspace, visible WAV copies and an HTML player
are also at `../audio-samples/yue2/` relative to the repository root.
All five evaluated generation GGUFs and source notices are now mirrored under
`https://ckpts.cantorfm.com/yue2-1.0/`; the catalog switch is in Cantor PR #6.
