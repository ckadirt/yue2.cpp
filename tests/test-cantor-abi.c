#include "cantor_engine.h"
#include <assert.h>
#include <stdint.h>
#include <string.h>

int main(void) {
    assert(cantor_engine_abi_version() == 1);
    assert(strcmp(cantor_engine_model(), "yue2") == 0);
    assert(cantor_engine_stages() == ((1u << 2) | (1u << 3) | (1u << 4)));
    assert(cantor_engine_load(0, 0, 0) == 0);
    const cantor_component duplicate[] = {{"lm", "a"}, {"lm", "b"}};
    assert(cantor_engine_load(duplicate, 2, 0) == 0);
    const cantor_component unknown[] = {{"lm", "a"}, {"embed", "b"}};
    assert(cantor_engine_load(unknown, 2, 0) == 0);
    const cantor_component parts[] = {{"lm", "missing.gguf"}, {"vae", "missing-vae.gguf"}};
    cantor_ctx * c = cantor_engine_load(parts, 2, 0);
    assert(c);
    const char * invalid[] = {"{}", "[]", "null", "{", "{\"style\":\"x\",\"duration\":-1}",
        "{\"caption\":\"x\",\"steps\":0}", "{\"caption\":\"x\",\"duration\":361}",
        "{\"caption\":\"x\",\"seed\":18446744073709551615}",
        "{\"caption\":\"x\",\"steps\":4294967297}",
        "{\"caption\":\"x\",\"semantic_sampling\":{\"max_tokens\":4294967297}}",
        "{\"caption\":\"x\",\"semantic_sampling\":{\"repetition_penalty\":1e100}}",
        "{\"caption\":\"x\",\"semantic_sampling\":\"bad\"}",
        "{\"caption\":\"x\\u0000y\"}", "{\"caption\":\"x\",\"peak_clip\":1000}"};
    for (unsigned i = 0; i < sizeof(invalid) / sizeof(invalid[0]); ++i) {
        uint8_t * out = (uint8_t *)(uintptr_t)1;
        size_t n = 9;
        assert(cantor_engine_run_stage(c, CANTOR_STAGE_CODES, (const uint8_t *)invalid[i], strlen(invalid[i]),
            &out, &n, 0, 0, 0) == CANTOR_ERR);
        assert(!out && n == 0);
        assert(cantor_engine_last_error_code() == CANTOR_ERR_OTHER);
        assert(cantor_engine_resident_modules(c) == 0);
    }
    int count = 99, rate = 0;
    assert(!cantor_engine_audio(c, &count, &rate)); assert(count == 0 && rate == 48000);
    cantor_engine_free_blob(0); cantor_engine_free(c); cantor_engine_free(0);
    return 0;
}
