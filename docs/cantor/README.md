# YuE2 integration workspace

This directory is the durable working record for bringing `ckadirt/yue2.cpp`
to the same Cantor ABI and distribution contract as the existing engines.

- [Plan and acceptance criteria](plan.md)
- [Checkpoint preset decisions](presets.md)
- [Work log and recovery instructions](work-log.md)
- [Validation evidence](validation.md)
- [Delivery audit: completed work and remaining gaps](delivery-audit.md)
- [Model inspection](../yue2-model-inspection.md)

Implementation checkout: `../../yue2.cpp`, branch `cantor-abi-v1`.
Remote persistent checkout: `/cantor/repos/yue2.cpp` on Modal volume
`cantor-node`, mounted at `/cantor`. Private credentials: `/cantor/keys/.env`.
Only paths and credential names may appear in these records; never values.

Keep the plan and work log current at each coherent implementation commit.
Copy these records into the fork's `docs/cantor/` directory so the record itself
is committed and recoverable. Preserve test outputs and generation artifacts
on the persistent volume, with concise results and paths in the work log.

Validated binary source: `25455ed8a916`. CPU/CUDA archives are publicly hosted;
the selected recipes and measured timings are in the preset/validation reports.
Local listening index: `../../yue2.cpp/artifacts/release-25455ed8a916/SAMPLES.md`.
Visible local copies: [audio-samples/yue2](../../audio-samples/yue2/README.md),
with an [HTML audio player](../../audio-samples/yue2/index.html).
Registration: https://github.com/ckadirt/Cantor/pull/5.

The Python operations helpers are recovery records for this authorized task.
Starting another GPU session requires fresh user authorization; expiration is
not permission to renew a three-hour allocation automatically.
