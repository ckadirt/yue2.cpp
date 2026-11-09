# Quality, balanced, and speed presets

Status: **live in Cantor**, 2026-11-09. [Merged registration](https://github.com/ckadirt/Cantor/pull/5).

The user's requirement is three meaningful presets, each selecting the right
precision for every component. A low-bit option is acceptable only if it
retains useful quality. "Speed" needs timing evidence, not just a smaller file.

## Existing upstream assets

Source: [Serveurperso/YuE2-GGUF](https://huggingface.co/Serveurperso/YuE2-GGUF),
revision `e630f2b8f6aedf8254c3186438633c1b5eeaf80a`.

| Component | Existing choices | Notes |
|---|---|---|
| MoT backbone, including both AR and NAR | BF16, Q8_0, Q6_K, Q5_K_M | One file controls both experts in this packaging |
| VAE encoder/decoder | F32 | Keep F32 in all initial presets |
| Optional MERT2 audio encoder | F32, Q8_0 | Needed for recording transcription/tokenization only |
| Optional SheetSage2 transcription head | F32, Q8_0 | Keep the matching MERT precision beside it |
| Optional community audio-tokenizer head | F32, Q8_0 | Outside initial standard generation scope |

Upstream quantization scripts deliberately stop at Q5_K_M for the main model.
They do not publish Q4 for this implementation. Audio.cpp's Q4 files use a
different format/layout and must not be substituted into this fork.

## Selected generation presets

| Label / Cantor tag | Main model | VAE | Midpoint steps | Catalog VRAM reservation |
|---|---|---|---:|---:|
| Quality / `3b-quality` | BF16 | F32 | 32 | 16 GiB |
| Balanced / `3b-balanced` | Q8_0 | F32 | 32 | 12 GiB |
| Speed / `3b-fast` | Q5_K_M | F32 | 16 | 10 GiB |

The main GGUF includes both AR and NAR experts. These presets select its
published recipe as a whole, rather than pretending AR and NAR are separate
downloadable roles. VAE F32 is the highest released decoder source precision;
the native runtime uses optimized F16 convolution weights with F32 activations.
Optional audio encoders/transcribers are not required for this generation arc.

On the final portable A10G build, a frozen 30-second English request with full
score planning, CFG 1, and seed 1234 took:

| Preset | First request in a new context | Warm mean, two exact-repeat runs |
|---|---:|---:|
| Quality | 50.78 s | **13.91 s** |
| Balanced | 32.25 s | **11.39 s** |
| Speed | 23.26 s | **8.02 s** |

Warm measurements retain weights. Cold measurements include component SHA-256
verification, loading and graph setup, and exclude downloading model files.
These are one-hardware, one-prompt examples, not cross-device performance
guarantees. Quantization can change the planned composition.

Independent 30-second, 32-step direct-conditioning comparisons averaged
BF16 **10.22 s**, Q8 **8.78 s**, Q6 **8.69 s**, and Q5 **8.27 s**. Q6's small
latency advantage did not justify another tier over Q8's closer reference
results. Fixed-code waveform relative L2 against BF16 was Q8 **0.0313**,
Q6 **0.0340**, and Q5 **0.0658**; these are numerical diagnostics, not listening
judgments. An earlier independent 12-second matrix is retained for comparison.

Step-count changes were measured separately after warming weights and graphs.
The full planned-song Q5 render at 16 steps differed from its identical
32-step render by **0.03334 relative waveform L2**. Eight steps ran faster
(6.74 s end to end), but changed that waveform by **0.13647**, exceeding the
0.1 numerical tolerance used for this preset decision. Eight remains an
optional control; 16 is the speed default. This tolerance is an engineering
proxy, not a perceptual-quality guarantee. No human listening is claimed.

English, Spanish and empty-lyrics instrumental clips were retained for each
selected recipe. Six-minute supplied-code capacity checks passed on A10G;
see [validation](validation.md) and [final measurements](measurements/release-25455ed-summary.json).

A final full-pipeline quality run produced 359.9987 seconds in **320.23 s**
from a cold context, using real score planning, 9,000 AR codes, and 32 solver
steps. Its sampled peak was **12,969 MiB**, within the 16 GiB reservation.
The semantic length was forced to the cap; this is sustained-generation
evidence rather than a guarantee of a natural musical ending.

If optional transcription is included later: compare F32 MERT + F32 SheetSage2
for quality, and matched Q8_0 files for smaller presets. This is a candidate
policy, not evidence that Q8 is faster on every device or equally accurate on
every recording.

All three presets use the same F32 VAE and explicit CFG 1 default. Score mode
defaults to `full`. Recording covers and automatic lyric writing are not
advertised. Cantor accepts 15–360-second requests for this engine; supplied
ABC is supported by the native API. It is not exposed as an app parameter:
the host's shared text-extension validator currently rejects multiline text.

## Pinned sizes and SHA-256

| File | Bytes | SHA-256 |
|---|---:|---|
| `YuE2-3B-BF16.gguf` | 7166072352 | `668ca9ffa4622449916aae5068b5737363e7ec186a824cd3d7a1a8a95269f166` |
| `YuE2-3B-Q8_0.gguf` | 3810232064 | `41121ce97786d7795a325bcf123ca196956c03bb252c9e75384cfc1f2fc19e6b` |
| `YuE2-3B-Q6_K.gguf` | 2943331072 | `42068d5e57713df11b9f6a5a3751072d9bbefe231d1d088f9c100e026ffa4ef9` |
| `YuE2-3B-Q5_K_M.gguf` | 2622936832 | `cd3efd250b734a229172800f08f33a893ad1f66b521666e176cdae4a0729b281` |
| `YuE2-Vae-F32.gguf` | 530497344 | `93e49dfb1970e89ad64cacb17cf13b5d05f6bb30ef7ed3adae3050bcb728638a` |

All five downloaded generation files were verified locally against these
sizes and SHA-256 values on the persistent volume.
