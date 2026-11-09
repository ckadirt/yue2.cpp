#include "cantor-checkpoint.h"
#include <algorithm>
#include <cassert>
#include <stdexcept>
#include <string>
int main() {
    namespace cp = yue2::checkpoint;
    const std::string abc = "abc";
    assert(cp::hex_digest(cp::sha256(reinterpret_cast<const uint8_t *>(abc.data()), abc.size())) ==
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    const std::array<char, 8> magic{{'Y','U','E','2','S','T','0','1'}};
    auto encoded = cp::encode(magic, 2, {{cp::section_kind::request_json, {'{','}'}}});
    auto decoded = cp::decode(encoded, magic);
    assert(decoded.stage == 2 && decoded.sections.size() == 1);
    assert(decoded.sections[0].bytes == std::vector<uint8_t>({'{','}'}));
    auto rejects = [&](const std::vector<uint8_t> & bytes) {
        bool failed = false;
        try { cp::decode(bytes, magic); } catch (const std::exception &) { failed = true; }
        assert(failed);
    };
    for (size_t n = 0; n < encoded.size(); ++n) rejects({encoded.begin(), encoded.begin() + n});
    auto corrupt = encoded; corrupt.back() ^= 1; rejects(corrupt);
    corrupt = encoded; corrupt[0] ^= 1; rejects(corrupt);
    corrupt = encoded; corrupt.push_back(0); rejects(corrupt);
    auto put = [](std::vector<uint8_t> & b, size_t offset, uint64_t value, unsigned width) {
        for (unsigned j = 0; j < width; ++j) b[offset + j] = uint8_t(value >> (j * 8));
    };
    auto seal = [](std::vector<uint8_t> & b) {
        std::fill(b.begin() + 40, b.begin() + 72, 0);
        auto digest = cp::sha256(b.data(), b.size());
        std::copy(digest.begin(), digest.end(), b.begin() + 40);
    };
    // Correct checksums must not make malformed directories acceptable.
    corrupt = encoded; corrupt.resize(72);
    put(corrupt, 16, 0, 4); put(corrupt, 20, 72, 4); put(corrupt, 24, 72, 8);
    seal(corrupt); rejects(corrupt);
    corrupt = cp::encode(magic, 2, {{cp::section_kind::request_json, {1,2}},
                                  {cp::section_kind::metadata, {3,4}}});
    put(corrupt, 72 + 24 + 8, 120, 8); // second payload overlaps the first
    seal(corrupt); rejects(corrupt);
    corrupt = encoded; put(corrupt, 72 + 16, UINT64_MAX, 8);
    seal(corrupt); rejects(corrupt);
}
