#include "cantor-checkpoint.h"
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
}
