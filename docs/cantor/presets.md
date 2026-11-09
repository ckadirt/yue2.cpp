# Quality, balanced, and speed presets

Status: **initial measurements complete; final release validation pending**, 2026-11-09.

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

## Candidate generation presets

| Label | Main model | VAE | Decision |
|---|---|---|---|
| Quality | BF16 | F32 | Highest released precision; numerical reference |
| Balanced | Q8_0 | F32 | Preferred: near BF16 numerically; faster than BF16 and essentially tied with Q6 |
| Speed | Q5_K_M candidate | F32 | Validate a deliberate 16-step recipe; quantization alone gives only a small speed gain |

Quality and balanced retain 32 midpoint steps. A speed recipe with 16 steps is
an explicit solver setting, separate from its checkpoint precision. The 8-step
option needs stronger quality evidence before becoming a default.

The first isolated A10G matrix used 300 frames (12 seconds), direct conditioning,
CFG 1, 32 steps, retained weights, and two exact-repeat warm runs. Warm times
were BF16 **4.256 s**, Q8 **3.582 s**, Q6 **3.587 s**, and Q5 **3.439 s**.
Q8's fixed-semantic latent relative L2 against BF16 was **0.01549**; Q6 and Q5
were about **0.067**. Q5 changed one probe's top-logit choice, while Q8 and Q6
kept it. These are diagnostic differences, not human judgments of a song.

At 32 steps Q6 offers no measured latency benefit over Q8 and has appreciably
larger latent differences. Q5 is only about 4% faster than Q8 in this short
matrix. Thus the speed tier must be justified by its complete measured recipe.
See [raw summary](measurements/matrix-01-summary.json). Full-duration memory,
warm step-count comparisons, and multilingual review clips remain in progress.

If optional transcription is included later: compare F32 MERT + F32 SheetSage2
for quality, and matched Q8_0 files for smaller presets. This is a candidate
policy, not evidence that Q8 is faster on every device or equally accurate on
every recording.

Keep composition mode, acoustic steps, prompt, seed, and target frames fixed
when comparing quantization. Do not quietly remove planning or lower solver
steps to manufacture a speed win. Report those as independent controls if
tested. Include warm/cold stage timings, peak VRAM, hashes, and retained outputs.

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
