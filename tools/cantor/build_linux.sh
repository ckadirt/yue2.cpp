#!/bin/sh
# Reproducible Linux packaging configuration. Run from the repository root.
set -eu
backend=${1:-cpu}
build=${2:-build-cantor-$backend}
case "$backend" in
    cpu)
        cmake -S . -B "$build" -DCMAKE_BUILD_TYPE=Release \
            -DGGML_BACKEND_DL=ON -DGGML_NATIVE=OFF \
            -DGGML_CPU_ALL_VARIANTS=ON -DGGML_OPENMP=OFF -DGGML_CUDA=OFF
        ;;
    cuda12)
        # PTX provides forward compatibility. Ampere SASS serves the tested
        # A10G directly; this must not become a native/SM86-only release.
        cmake -S . -B "$build" -DCMAKE_BUILD_TYPE=Release \
            -DGGML_BACKEND_DL=ON -DGGML_NATIVE=OFF \
            -DGGML_CPU_ALL_VARIANTS=ON -DGGML_OPENMP=OFF -DGGML_CUDA=ON -DGGML_CUDA_NCCL=OFF \
            '-DCMAKE_CUDA_ARCHITECTURES=75-virtual;80-virtual;86-real'
        ;;
    *) echo 'Usage: build_linux.sh [cpu|cuda12] [build-directory]' >&2; exit 2 ;;
esac
cmake --build "$build" --target cantor-engine test-cantor-abi test-cantor-checkpoint -j "${CANTOR_BUILD_JOBS:-2}"
ctest --test-dir "$build" --output-on-failure
