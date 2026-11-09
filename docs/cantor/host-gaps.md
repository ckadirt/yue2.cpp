# Host work requiring separate approval

These are flagged follow-up proposals. No implementation changes to Cantor's
node, IPC, services, or default macOS manifest selection were made here.

## macOS default backend manifest

`node/crates/cantor-node/src/backends.rs` defaults macOS nodes to the latest
node release's `backends-macos-v1.json`. The release workflow currently builds
that file from its ACE-Step packages only. The shared catalog in PR #6 includes
the new macOS 14-targeted YuE2 archives, but that default release asset does not
automatically incorporate them.

An operator can already select the shared backend manifest with the existing
`backends_url` configuration. A proposed default-path fix is to extend
`.github/workflows/release.yml` in **Cantor**, merging the shared manifest's
macOS entries with that release's freshly built ACE-Step entries. Validate
family/OS/architecture/backend identities and preserve ACE-Step availability.
Publish it with a normal reviewed node release; do not overwrite an existing
release asset in place. This is a proposal, not a change already made.

## Windows Cantor node

Native YuE2 CPU and Vulkan DLLs pass Windows CI ABI/checkpoint/relocation checks.
That does not provide a Windows node executable. The current Rust host assumes
Linux-style library names outside macOS, and also uses Unix IPC/process/service
facilities. DLL loading is one part of a broader host port.

A proposed separate task starts with native Windows `cargo check`, inventories
the failing OS assumptions, adds Windows host abstractions, and runs node
lifecycle/install/load checks on native Windows CI. Keep full song-generation
testing marked unavailable until a suitable physical environment is supplied.
Do not register Windows as an installable node platform merely because the
engine DLL builds.

## Audio input and lyrics

Upstream YuE2 covers use recording-to-ABC transcription, then regeneration from
the reviewed score. The native port has optional transcriber assets, and the
Cantor adapter already accepts supplied ABC. Cantor does not yet connect an
audio-input workflow or expose multiline ABC through its app contract. Those
are integration gaps, not proof that YuE2 cannot render covers.

Automatic lyric writing is not a documented built-in YuE2 generation task.
Lyrics are supplied; an external lyric-writing model/agent would be a separate
feature. No covers or automatic lyric-writing capability was advertised by
this distribution follow-up.
