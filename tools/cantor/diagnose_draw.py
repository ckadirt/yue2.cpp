"""Diagnose portable Philox draws versus PyTorch's device-dependent CUDA layout."""
import argparse
import ctypes as C
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import torch


def philox(x, z, seed):
    mask = np.uint64(0xffffffff)
    x, z = np.broadcast_arrays(x.astype(np.uint32), z.astype(np.uint32))
    y, w = np.zeros_like(x), np.zeros_like(x)
    k0, k1 = seed & 0xffffffff, seed >> 32
    for _ in range(10):
        a = x.astype(np.uint64) * np.uint64(0xd2511f53)
        b = z.astype(np.uint64) * np.uint64(0xcd9e8d57)
        x, y, z, w = ((b >> 32).astype(np.uint32) ^ y ^ np.uint32(k0),
                      (b & mask).astype(np.uint32),
                      (a >> 32).astype(np.uint32) ^ w ^ np.uint32(k1),
                      (a & mask).astype(np.uint32))
        k0, k1 = (k0 + 0x9e3779b9) & 0xffffffff, (k1 + 0xbb67ae85) & 0xffffffff
    return np.stack([x, y, z, w], axis=-1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(args.reference.resolve()))
    from yue2.protocol import CODEC_OFFSET, VOCAB_SIZE, GenerationConfig
    from yue2.sampling import distribution

    torch.manual_seed(7)
    logits = torch.randn(1, VOCAB_SIZE) * 3.0
    history = (torch.randint(0, 64, (160,), generator=torch.Generator().manual_seed(11)) + CODEC_OFFSET).tolist()
    probabilities = distribution(logits, GenerationConfig().semantic, history, 300, 'semantic').softmax(-1)[0]
    ids = torch.nonzero(probabilities).flatten().numpy()
    compact = probabilities[probabilities > 0].contiguous()
    seed, draws = 831001, 512

    def native(values, label, count):
        values.numpy().tofile(args.output / f'{label}.bin')
        target = args.output / f'{label}-ids.bin'
        subprocess.run([str(args.probe.resolve()), str(args.output / f'{label}.bin'),
                        str(seed), str(count), str(target)], check=True)
        return np.fromfile(target, dtype='float32').astype('int64')

    def cuda(values):
        gpu = values.cuda()
        generator = torch.Generator(device='cuda').manual_seed(seed)
        return np.array([int(torch.multinomial(gpu, 1, generator=generator)[0]) for _ in range(draws)])

    compact_reference = cuda(compact)
    assert np.array_equal(compact_reference, native(compact, 'compact', draws)), 'Compact cuRAND parity failed'
    full_reference = cuda(probabilities)
    full_native = native(probabilities, 'full', draws)
    props = torch.cuda.get_device_properties(0)
    runtime = C.CDLL('/usr/local/cuda/lib64/libcudart.so.12')
    max_threads = C.c_int()
    # cudaDevAttrMaxThreadsPerMultiProcessor, installed driver_types.h.
    assert runtime.cudaDeviceGetAttribute(C.byref(max_threads), 39, 0) == 0
    stride = min((VOCAB_SIZE + 255) // 256, props.multi_processor_count * (max_threads.value // 256)) * 256
    groups = ids // stride
    increments = (VOCAB_SIZE - 1) // (stride * 4) + 1
    words = philox(np.arange(draws, dtype=np.uint32)[:, None] * increments + groups[None, :] // 4,
                   (ids % stride)[None, :], seed)
    raw = np.take_along_axis(words, np.broadcast_to((groups % 4)[None, :, None], (draws, len(ids), 1)), axis=2)[..., 0]
    uniform = raw.astype(np.float32) * np.float32(2**-32) + np.float32(2**-33)
    exponential = -np.log(np.minimum(uniform, np.nextafter(np.float32(1), np.float32(0))))
    predicted = ids[(compact.numpy()[None, :] / exponential).argmax(axis=1)]
    assert np.array_equal(predicted, full_reference), 'CUDA grid-layout explanation did not reproduce torch draws'

    histogram = native(compact, 'histogram', 65536)
    frequencies = np.bincount(histogram, minlength=len(compact)) / len(histogram)
    expected = compact.numpy() / compact.numpy().sum()
    tvd = float(np.abs(frequencies - expected).sum() / 2)
    assert tvd < 0.03, 'Native sampler distribution drift'
    report = {'torch': torch.__version__, 'device': props.name, 'vocabulary': VOCAB_SIZE,
              'sm_count': props.multi_processor_count, 'max_threads_per_sm': max_threads.value,
              'torch_grid_stride': stride, 'compact_exact_draws': draws,
              'full_torch_layout_exact_draws': draws,
              'native_vs_full_torch_differing': int((full_native != full_reference).sum()),
              'histogram_draws': len(histogram), 'total_variation_distance': tvd,
              'policy': 'Preserve the upstream native per-vocabulary-ID Philox stream; do not promise equal-seed PyTorch output on every GPU'}
    (args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
