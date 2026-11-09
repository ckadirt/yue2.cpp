#pragma once
// Shared native output policy: percentile peak normalization, then clipping.
#include <algorithm>
#include <vector>

static void audio_normalize(float * audio, int n_total, int peak_clip = 10) {
    if (n_total <= 0) return;
    peak_clip = std::max(0, std::min(999, peak_clip));
    std::vector<float> absvals(static_cast<size_t>(n_total));
    for (int i = 0; i < n_total; ++i) absvals[i] = audio[i] < 0 ? -audio[i] : audio[i];
    const double pct = 1.0 - static_cast<double>(peak_clip) / 1000000.0;
    const size_t idx = static_cast<size_t>(static_cast<double>(n_total - 1) * pct);
    std::nth_element(absvals.begin(), absvals.begin() + idx, absvals.end());
    const float ref = absvals[idx];
    if (ref < 1e-6f) return;
    const float gain = 1.0f / ref;
    for (int i = 0; i < n_total; ++i) audio[i] = std::max(-1.0f, std::min(1.0f, audio[i] * gain));
}
