// Cantor ABI v1 adapter. Numerical work stays in the upstream implementation.
#include "cantor_engine.h"
#include "cantor-checkpoint.h"
#include "pipeline.h"
#include "version.h"
#include "yyjson.h"

#include <array>
#include <cmath>
#include <limits>
#include <memory>
#include <stdexcept>

namespace cp = yue2::checkpoint;
namespace {
constexpr std::array<char, 8> magic{{'Y','U','E','2','S','T','0','1'}};
thread_local cantor_error last_code = CANTOR_OK;
thread_local std::string last_message;
void error(cantor_error code, const std::string & message) { last_code = code; last_message = message; }
void require(bool ok, const char * message) { if (!ok) throw std::invalid_argument(message); }
using Doc = std::unique_ptr<yyjson_doc, decltype(&yyjson_doc_free)>;
Doc document(const uint8_t * bytes, size_t size) {
    require(size > 0 && size <= 1024 * 1024, "JSON size outside 1 MiB boundary");
    require(std::find(bytes, bytes + size, uint8_t(0)) == bytes + size, "JSON contains a NUL byte");
    Doc doc(yyjson_read(reinterpret_cast<const char *>(bytes), size, 0), yyjson_doc_free);
    require(doc && yyjson_is_obj(yyjson_doc_get_root(doc.get())), "expected a JSON object");
    return doc;
}
std::string string_value(yyjson_val * root, const char * key, bool required = false) {
    auto * v = yyjson_obj_get(root, key);
    if (!v) { require(!required, "missing checkpoint string"); return {}; }
    require(yyjson_is_str(v), "expected string field");
    return {yyjson_get_str(v), yyjson_get_len(v)};
}
int integer_value(yyjson_val * root, const char * key) {
    auto * v = yyjson_obj_get(root, key);
    require(yyjson_is_int(v), "missing checkpoint integer");
    auto x = yyjson_get_sint(v);
    require(x >= INT32_MIN && x <= INT32_MAX, "checkpoint integer overflow");
    return static_cast<int>(x);
}
std::vector<uint8_t> bytes_of(const std::string & s) { return {s.begin(), s.end()}; }
template<class T> std::vector<uint8_t> pack(const std::vector<T> & values) {
    static_assert(sizeof(T) == 4, "32-bit state elements required");
    std::vector<uint8_t> out(values.size() * 4);
    for (size_t i = 0; i < values.size(); ++i) {
        uint32_t bits; std::memcpy(&bits, &values[i], 4);
        for (unsigned j = 0; j < 4; ++j) out[i * 4 + j] = uint8_t(bits >> (j * 8));
    }
    return out;
}
template<class T> std::vector<T> unpack(const std::vector<uint8_t> & bytes, size_t limit) {
    require(bytes.size() % 4 == 0 && bytes.size() / 4 <= limit, "checkpoint array size invalid");
    std::vector<T> out(bytes.size() / 4);
    for (size_t i = 0; i < out.size(); ++i) {
        uint32_t bits = 0;
        for (unsigned j = 0; j < 4; ++j) bits |= uint32_t(bytes[i * 4 + j]) << (j * 8);
        std::memcpy(&out[i], &bits, 4);
    }
    return out;
}
struct State {
    Yue2Request request;
    std::vector<int> abc, codes;
    std::vector<float> latents;
    Yue2ARResume ar;
    int phase = 0; // 0 score, 1 semantic, 2 codes complete
    int frame = 0, step = 0;
    bool done = false, score_truncated = false, semantic_truncated = false, planned_score = false;
};
Yue2Request parse_request(const uint8_t * bytes, size_t size) {
    auto doc = document(bytes, size);
    auto * root = yyjson_doc_get_root(doc.get());
    for (const char * key : {"style", "caption", "lyrics", "abc", "cot", "semantic_tokens"}) {
        auto * v = yyjson_obj_get(root, key);
        require(!v || yyjson_is_str(v), "text request fields must be strings");
    }
    for (const char * key : {"steps", "inference_steps", "seed", "lm_seed", "lm_batch_size", "synth_batch_size", "top_k"}) {
        auto * v = yyjson_obj_get(root, key);
        require(!v || yyjson_is_int(v), "integer request field has the wrong type");
    }
    for (const char * key : {"duration", "cfg_scale", "guidance_scale"}) {
        auto * v = yyjson_obj_get(root, key);
        require(!v || yyjson_is_num(v), "numeric request field has the wrong type");
    }
    auto text = std::string(reinterpret_cast<const char *>(bytes), size);
    Yue2Request r; request_init(&r);
    require(request_parse_json(&r, text.c_str()), "invalid YuE2 request");
    if (!yyjson_obj_get(root, "style")) {
        for (const char * key : {"caption", "description", "tags"}) {
            if (yyjson_obj_get(root, key)) { r.style = string_value(root, key); break; }
        }
    }
    if (auto * v = yyjson_obj_get(root, "inference_steps")) {
        require(yyjson_is_int(v), "inference_steps must be an integer");
        r.steps = yyjson_get_int(v);
    }
    if (auto * v = yyjson_obj_get(root, "guidance_scale")) {
        require(yyjson_is_num(v), "guidance_scale must be numeric");
        r.cfg_scale = static_cast<float>(yyjson_get_num(v));
    }
    if (!yyjson_obj_get(root, "lm_seed") && r.seed >= 0) r.lm_seed = r.seed;
    if (auto * v = yyjson_obj_get(root, "top_k")) r.semantic_sampling.top_k = yyjson_get_int(v);
    require(!r.style.empty(), "style/caption is required");
    require(r.cot == "full" || r.cot == "melody" || r.cot == "off", "invalid cot mode");
    require(r.abc.empty() || r.cot != "off", "ABC requires full or melody mode");
    if (!r.semantic_tokens.empty() && r.abc.empty()) r.cot = "off";
    require(std::isfinite(r.duration) && r.duration >= 0.04f && r.duration <= 360, "duration must be in [0.04,360]");
    require(r.steps >= 1 && r.steps <= 200, "steps must be in [1,200]");
    require(std::isfinite(r.cfg_scale) && (r.cfg_scale == -1 || (r.cfg_scale >= 0 && r.cfg_scale <= 20)), "invalid guidance scale");
    require(r.lm_batch_size == 1 && r.synth_batch_size == 1, "Cantor runs one song per request");
    require(r.adapters.empty() && r.source_tokens.empty(), "adapters and continuation are not wired in this adapter");
    require(yue2_sampling_valid(r.abc_sampling, "abc") && r.abc_sampling.max_tokens <= 4096, "invalid score sampling");
    require(yue2_sampling_valid(r.semantic_sampling, "semantic") && r.semantic_sampling.max_tokens <= 9000, "invalid semantic sampling");
    for (const char * key : {"src_audio_path", "ref_audio_path"}) {
        require(!yyjson_obj_get(root, key) || string_value(root, key).empty(), "recording input is not supported yet; supply ABC");
    }
    r.semantic_sampling.max_tokens = std::min(r.semantic_sampling.max_tokens, std::max(1, int(r.duration * 25)));
    r.semantic_sampling.min_tokens = std::min(r.semantic_sampling.min_tokens, r.semantic_sampling.max_tokens);
    request_resolve_seed(&r);
    return r;
}
}

struct cantor_ctx {
    std::string lm_path, vae_path, lm_hash, vae_hash;
    cantor_load_opts opts{};
    ModelStore * store = nullptr;
    Yue2Pipeline pipe{};
    std::vector<float> audio;
    int samples = 0;
    double duration = 0;
    ~cantor_ctx() { pipeline_free(&pipe); store_free(store); }
};

namespace {
void configure(cantor_ctx & c) {
    g_backend_n_threads = c.opts.n_threads;
    if (c.lm_hash.empty()) c.lm_hash = cp::hex_digest(cp::sha256_file(c.lm_path));
    if (c.vae_hash.empty()) c.vae_hash = cp::hex_digest(cp::sha256_file(c.vae_path));
    if (!c.pipe.configured) {
        Yue2PipelineParams p;
        p.no_fa = c.opts.disable_flash_attn != 0;
        if (c.opts.vae_chunk) p.vae_core = c.opts.vae_chunk;
        if (c.opts.vae_overlap) p.vae_halo = c.opts.vae_overlap;
        c.pipe.store = c.store;
        if (!pipeline_configure(&c.pipe, c.lm_path.c_str(), c.vae_path.c_str(), p))
            throw std::runtime_error("failed to configure YuE2 model/tokenizer");
    }
}
std::string runtime(cantor_ctx & c) {
    auto device = ggml_backend_get_device(c.pipe.kv_backend.backend);
    return std::string(YUE2_VERSION) + "/" + ggml_backend_name(c.pipe.kv_backend.backend) +
        "/device=" + (device ? ggml_backend_dev_description(device) : "unknown") +
        "/fa=" + std::to_string(c.opts.disable_flash_attn) + "/threads=" + std::to_string(c.opts.n_threads) +
        "/tile=" + std::to_string(c.pipe.params.vae_core) + "/halo=" + std::to_string(c.pipe.params.vae_halo);
}
std::vector<uint8_t> save(cantor_ctx & c, const State & s, cantor_stage stage) {
    std::unique_ptr<yyjson_mut_doc, decltype(&yyjson_mut_doc_free)> doc(yyjson_mut_doc_new(nullptr), yyjson_mut_doc_free);
    auto * root = yyjson_mut_obj(doc.get()); yyjson_mut_doc_set_root(doc.get(), root);
    yyjson_mut_obj_add_strcpy(doc.get(), root, "lm", c.lm_hash.c_str());
    yyjson_mut_obj_add_strcpy(doc.get(), root, "vae", c.vae_hash.c_str());
    yyjson_mut_obj_add_strcpy(doc.get(), root, "runtime", runtime(c).c_str());
    yyjson_mut_obj_add_int(doc.get(), root, "phase", s.phase);
    yyjson_mut_obj_add_int(doc.get(), root, "frame", s.frame);
    yyjson_mut_obj_add_int(doc.get(), root, "step", s.step);
    yyjson_mut_obj_add_int(doc.get(), root, "ar_step", s.ar.step);
    yyjson_mut_obj_add_int(doc.get(), root, "ar_owed", s.ar.owed);
    yyjson_mut_obj_add_bool(doc.get(), root, "ar_truncated", s.ar.generated.truncated);
    yyjson_mut_obj_add_bool(doc.get(), root, "score_truncated", s.score_truncated);
    yyjson_mut_obj_add_bool(doc.get(), root, "semantic_truncated", s.semantic_truncated);
    yyjson_mut_obj_add_bool(doc.get(), root, "planned_score", s.planned_score);
    yyjson_mut_obj_add_bool(doc.get(), root, "done", s.done);
    char * json = yyjson_mut_write(doc.get(), 0, nullptr);
    if (!json) throw std::bad_alloc();
    std::string metadata(json); free(json);
    return cp::encode(magic, stage, {
        {cp::section_kind::request_json, bytes_of(request_to_json(&s.request, false))},
        {cp::section_kind::abc_ids_i32, pack(s.abc)},
        {cp::section_kind::semantic_ids_i32, pack(s.codes)},
        {cp::section_kind::latents_f32, pack(s.latents)},
        {cp::section_kind::metadata, bytes_of(metadata)},
    });
}
State restore(cantor_ctx & c, const uint8_t * bytes, size_t size, uint32_t * stage) {
    auto blob = cp::decode(bytes, size, magic); *stage = blob.stage;
    require(blob.sections.size() == 5, "unexpected checkpoint sections");
    auto section = [&](cp::section_kind kind) -> const std::vector<uint8_t> & {
        const std::vector<uint8_t> * found = nullptr;
        for (const auto & part : blob.sections) if (part.kind == kind) {
            require(!found, "duplicate checkpoint section"); found = &part.bytes;
        }
        require(found, "missing checkpoint section"); return *found;
    };
    State s;
    const auto & req = section(cp::section_kind::request_json);
    s.request = parse_request(req.data(), req.size());
    s.abc = unpack<int>(section(cp::section_kind::abc_ids_i32), 4096);
    s.codes = unpack<int>(section(cp::section_kind::semantic_ids_i32), 9000);
    s.latents = unpack<float>(section(cp::section_kind::latents_f32), 9000 * 64);
    const auto & meta = section(cp::section_kind::metadata);
    auto doc = document(meta.data(), meta.size()); auto * root = yyjson_doc_get_root(doc.get());
    require(string_value(root, "lm", true) == c.lm_hash && string_value(root, "vae", true) == c.vae_hash,
            "checkpoint model identity differs from loaded component bytes");
    require(string_value(root, "runtime", true) == runtime(c), "checkpoint runtime/backend/options differ");
    s.phase = integer_value(root, "phase"); s.frame = integer_value(root, "frame");
    s.step = integer_value(root, "step"); s.ar.step = integer_value(root, "ar_step");
    s.ar.owed = integer_value(root, "ar_owed");
    auto boolean = [&](const char * key) { auto * v = yyjson_obj_get(root, key);
        require(yyjson_is_bool(v), "missing checkpoint boolean"); return yyjson_get_bool(v); };
    s.ar.generated.truncated = boolean("ar_truncated"); s.done = boolean("done");
    s.score_truncated = boolean("score_truncated");
    s.semantic_truncated = boolean("semantic_truncated"); s.planned_score = boolean("planned_score");
    require(s.phase >= 0 && s.phase <= 2 && s.frame >= 0 && s.frame <= int(s.codes.size()) &&
            s.step >= 0 && s.step <= s.request.steps && s.ar.step >= 0 && s.ar.step <= 9001 &&
            s.ar.owed >= -1 && s.ar.owed <= 1, "invalid checkpoint cursor");
    for (int id : s.abc) require(id >= 0 && id < YUE2_EOD, "invalid ABC token");
    for (int id : s.codes) require(id >= YUE2_CODEC_OFFSET && id < YUE2_CODEC_OFFSET + YUE2_CODEC_SIZE, "invalid semantic token");
    for (float x : s.latents) require(std::isfinite(x), "non-finite checkpoint latent");
    require(s.latents.empty() || s.latents.size() == s.codes.size() * 64, "invalid latent shape");
    s.ar.generated.tokens = s.phase == 0 ? s.abc : s.codes;
    if (s.phase < 2) {
        int count = int(s.ar.generated.tokens.size());
        require((s.ar.owed == -1 && s.ar.step == count) ||
                (s.ar.owed == 1 && s.ar.step == count && s.ar.generated.truncated) ||
                (s.ar.owed == 0 && s.ar.step == count + 1), "AR cursor/history mismatch");
    }
    return s;
}
struct Call {
    cantor_stage stage;
    cantor_progress_fn progress;
    cantor_cancel_fn cancel;
    void * data;
    bool stopped = false;
    int offset = 0, total = 0;
    static bool cancelled(void * p) {
        auto & c = *static_cast<Call *>(p);
        c.stopped = c.stopped || (c.cancel && c.cancel(c.data)); return c.stopped;
    }
    static void report(int done, int total, void * p) {
        auto & c = *static_cast<Call *>(p);
        if (c.progress) c.progress(c.stage, c.offset + done, c.total ? c.total : total, c.data);
    }
};
struct StageScope {
    cantor_ctx & c;
    ~StageScope() {
        store_clear_request_state(c.store);
        qw3lm_kv_free(&c.pipe.kv);
    }
};
bool codes(cantor_ctx & c, State & s, Call & call) {
    auto & p = c.pipe; auto & r = s.request;
    BPETokenizer * tok = store_bpe(c.store, c.lm_path.c_str());
    auto encode = [tok](const std::string & text) { return bpe_encode(tok, text); };
    Yue2Cot cot; require(yue2_cot_parse(r.cot, &cot), "invalid cot");
    if (s.phase == 0 && (cot == YUE2_COT_OFF || !r.abc.empty())) {
        s.abc = cot == YUE2_COT_OFF ? std::vector<int>{} : encode(r.abc); s.phase = 1;
        require(s.abc.size() <= 4096, "supplied score exceeds the 4096-token score boundary");
    }
    call.total = (s.planned_score ? r.abc_sampling.max_tokens : 0) + r.semantic_sampling.max_tokens;
    if (!r.semantic_tokens.empty()) {
        std::vector<int> values;
        require(pipeline_parse_tokens(r.semantic_tokens, &values) && values.size() <= size_t(r.semantic_sampling.max_tokens),
                "invalid supplied semantic stream");
        s.codes.clear(); for (int id : values) s.codes.push_back(id + YUE2_CODEC_OFFSET);
        s.phase = 2; s.done = true; s.ar = {};
        return true;
    }
    Qwen3LM * lm = require_lm(&p, {});
    if (!lm) throw std::runtime_error("AR model load failed");
    ModelHandle hold(c.store, lm);
    std::vector<Yue2Generation> generated;
    if (s.phase == 0) {
        auto prefix = yue2_build_prompt_ids(encode, cot, r.style, r.lyrics, nullptr);
        bool ok = yue2_generate(lm, &p.kv, {prefix}, {}, 1, r.abc_sampling, r.lm_seed,
            YUE2_PHASE_ABC, &generated, Call::cancelled, &call, &s.ar, Call::report);
        s.abc = ok ? generated[0].tokens : s.ar.generated.tokens;
        if (!ok) { if (call.stopped) return false; throw std::runtime_error("score generation failed"); }
        r.abc = bpe_decode(tok, s.abc); s.score_truncated = generated[0].truncated;
        s.phase = 1; s.ar = {};
    }
    auto prefix = yue2_build_prompt_ids(encode, cot, r.style, r.lyrics, cot == YUE2_COT_OFF ? nullptr : &s.abc);
    call.offset = s.planned_score ? r.abc_sampling.max_tokens : 0;
    const float guidance = r.cfg_scale < 0 ? yue2_default_guidance(cot) : r.cfg_scale;
    std::vector<std::vector<int>> negative;
    if (guidance != 1) negative.push_back(yue2_build_negative_ids(encode, cot, cot == YUE2_COT_OFF ? nullptr : &s.abc));
    {
        bool ok = yue2_generate(lm, &p.kv, {prefix}, negative, guidance, r.semantic_sampling, r.lm_seed,
            YUE2_PHASE_SEMANTIC, &generated, Call::cancelled, &call, &s.ar, Call::report);
        s.codes = ok ? generated[0].tokens : s.ar.generated.tokens;
        if (!ok) { if (call.stopped) return false; throw std::runtime_error("semantic generation failed"); }
        s.semantic_truncated = generated[0].truncated;
    }
    require(!s.codes.empty(), "empty semantic stream"); s.phase = 2; s.done = true; s.ar = {};
    return true;
}
bool diffuse(cantor_ctx & c, State & s, Call & call) {
    auto & p = c.pipe; const auto & r = s.request;
    require(s.phase == 2 && !s.codes.empty(), "DIFFUSE requires complete CODES");
    auto * tok = store_bpe(c.store, c.lm_path.c_str());
    auto encode = [tok](const std::string & text) { return bpe_encode(tok, text); };
    Yue2Cot cot; require(yue2_cot_parse(r.cot, &cot), "invalid cot");
    auto prefix = yue2_build_prompt_ids(encode, cot, r.style, r.lyrics, cot == YUE2_COT_OFF ? nullptr : &s.abc);
    const int chunk = (p.kv.cfg.max_seq_len - int(prefix.size()) - 3) / 2;
    require(chunk > 0 && (s.frame == int(s.codes.size()) || s.frame % chunk == 0), "invalid acoustic chunk cursor");
    if (s.latents.empty()) {
        require(s.frame == 0 && s.step == 0, "missing active acoustic state");
        s.latents.resize(s.codes.size() * 64);
        torch_cpu_randn(uint64_t(r.seed), s.latents.data(), int64_t(s.latents.size()));
    }
    s.done = false;
    const int chunks = (int(s.codes.size()) + chunk - 1) / chunk;
    call.total = chunks * r.steps;
    DebugDumper quiet; debug_init(&quiet, nullptr);
    int row0, rows; yue2_phase_rows(YUE2_PHASE_SEMANTIC, &row0, &rows);
    std::vector<float> logits(size_t(rows), 0);
    while (s.frame < int(s.codes.size())) {
        if (Call::cancelled(&call)) return false;
        const int count = std::min(chunk, int(s.codes.size()) - s.frame);
        std::vector<int> sequence = prefix;
        sequence.insert(sequence.end(), s.codes.begin() + s.frame, s.codes.begin() + s.frame + count);
        sequence.push_back(YUE2_MUSIC_END);
        {
            Qwen3LM * lm = require_lm(&p, {});
            if (!lm) throw std::runtime_error("acoustic AR prefill model load failed");
            ModelHandle hold(c.store, lm);
            require(qw3lm_kv_sets(&p.kv, 1), "KV allocation failed"); qw3lm_kv_trim(&p.kv, 0, 0);
            qw3lm_forward(lm, &p.kv, sequence.data(), int(sequence.size()), 0, logits.data(), row0, rows);
        }
        Yue2NAR * nar = require_nar(&p, {});
        if (!nar) throw std::runtime_error("NAR model load failed");
        ModelHandle hold(c.store, nar);
        call.offset = (s.frame / chunk) * r.steps;
        bool ok = nar_solve(nar, &p.kv, s.latents.data() + size_t(s.frame) * 64, count, 1,
            int(sequence.size()), 0, r.steps, &quiet, Call::cancelled, &call, &s.step, Call::report);
        if (!ok) { if (call.stopped) return false; throw std::runtime_error("acoustic solver failed"); }
        s.frame += count; s.step = 0;
    }
    for (float x : s.latents) require(std::isfinite(x), "non-finite acoustic output");
    s.done = true; return true;
}
cantor_status emit(cantor_ctx & c, const State & s, cantor_stage stage, bool done, uint8_t ** out, size_t * length) {
    auto bytes = save(c, s, stage);
    auto * buffer = static_cast<uint8_t *>(malloc(bytes.size())); if (!buffer) throw std::bad_alloc();
    std::memcpy(buffer, bytes.data(), bytes.size()); *out = buffer; *length = bytes.size();
    if (!done) error(CANTOR_ERR_CANCEL, "YuE2 paused at a durable boundary");
    return done ? CANTOR_DONE : CANTOR_PAUSED;
}
}

extern "C" {
uint32_t cantor_engine_abi_version(void) { return CANTOR_ENGINE_ABI; }
const char * cantor_engine_model(void) { return "yue2"; }
const char * cantor_engine_version(void) { return YUE2_VERSION; }
uint32_t cantor_engine_stages(void) { return (1u << CANTOR_STAGE_CODES) | (1u << CANTOR_STAGE_DIFFUSE) | (1u << CANTOR_STAGE_DECODE); }
cantor_error cantor_engine_last_error_code(void) { return last_code; }
const char * cantor_engine_last_error(void) { return last_message.c_str(); }
cantor_ctx * cantor_engine_load(const cantor_component * parts, size_t n, const cantor_load_opts * opts) {
    error(CANTOR_OK, "");
    try {
        require(parts && n == 2, "YuE2 requires exactly lm and vae components");
        std::unique_ptr<cantor_ctx> c(new cantor_ctx);
        if (opts) c->opts = *opts;
        require(c->opts.n_threads >= 0 && c->opts.vae_chunk >= 0 && c->opts.vae_overlap >= 0 &&
                c->opts.vae_chunk <= 24576 && c->opts.vae_overlap <= 24576, "invalid load options");
        for (size_t i = 0; i < n; ++i) {
            require(parts[i].role && parts[i].path && parts[i].path[0], "component role and path required");
            std::string role(parts[i].role);
            auto * path = role == "lm" ? &c->lm_path : role == "vae" ? &c->vae_path : nullptr;
            require(path && path->empty(), "unknown or duplicate component role"); *path = parts[i].path;
        }
        require(!c->lm_path.empty() && !c->vae_path.empty(), "lm and vae components required");
        c->store = store_create(c->opts.keep_loaded ? EVICT_NEVER : EVICT_STRICT);
        return c.release();
    } catch (const std::bad_alloc &) { error(CANTOR_ERR_OOM, "YuE2 context allocation failed"); }
      catch (const std::exception & e) { error(CANTOR_ERR_OTHER, e.what()); }
      catch (...) { error(CANTOR_ERR_OTHER, "unknown YuE2 load error"); }
    return nullptr;
}
void cantor_engine_free(cantor_ctx * c) { delete c; }
void cantor_engine_free_blob(uint8_t * p) { free(p); }
double cantor_engine_duration(cantor_ctx * c) { return c ? c->duration : 0; }
uint64_t cantor_engine_resident_bytes(cantor_ctx * c) { return c ? store_vram_bytes(c->store) : 0; }
int cantor_engine_resident_modules(cantor_ctx * c) { return c ? store_gpu_module_count(c->store) : 0; }
const float * cantor_engine_audio(cantor_ctx * c, int * count, int * rate) {
    if (count) *count = c ? c->samples : 0;
    if (rate) *rate = 48000;
    return c && !c->audio.empty() ? c->audio.data() : nullptr;
}
cantor_status cantor_engine_run_stage(cantor_ctx * c, cantor_stage stage, const uint8_t * input, size_t size,
    uint8_t ** output, size_t * output_size, cantor_progress_fn progress, cantor_cancel_fn cancel, void * userdata) {
    if (output) *output = nullptr;
    if (output_size) *output_size = 0;
    error(CANTOR_OK, "");
    try {
        require(c && input && size && output && output_size, "null or empty stage argument");
        c->audio.clear(); c->samples = 0;
        require(stage >= CANTOR_STAGE_CODES && stage <= CANTOR_STAGE_DECODE, "unsupported YuE2 stage");
        const bool packet = size >= magic.size() && !std::memcmp(input, magic.data(), magic.size());
        State state; uint32_t saved_stage = 0;
        if (!packet) {
            require(stage == CANTOR_STAGE_CODES, "stage requires a YuE2 state envelope");
            state.request = parse_request(input, size);
            state.planned_score = state.request.cot != "off" && state.request.abc.empty();
        }
        configure(*c);
        StageScope stage_scope{*c};
        if (packet) state = restore(*c, input, size, &saved_stage);
        c->duration = state.request.duration;
        Call call{stage, progress, cancel, userdata};
        if (stage == CANTOR_STAGE_CODES) {
            require(!packet || (saved_stage == CANTOR_STAGE_CODES && !state.done && state.phase < 2), "invalid CODES resume boundary");
            bool done = !Call::cancelled(&call) && codes(*c, state, call);
            return emit(*c, state, stage, done, output, output_size);
        }
        if (stage == CANTOR_STAGE_DIFFUSE) {
            require((saved_stage == CANTOR_STAGE_CODES && state.done && state.phase == 2 && state.latents.empty()) ||
                    (saved_stage == CANTOR_STAGE_DIFFUSE && !state.done && state.phase == 2), "invalid DIFFUSE input boundary");
            state.done = false;
            bool done = diffuse(*c, state, call);
            return emit(*c, state, stage, done, output, output_size);
        }
        require(saved_stage == CANTOR_STAGE_DIFFUSE && state.done && state.frame == int(state.codes.size()) &&
                !state.latents.empty() && state.step == 0, "DECODE requires completed acoustic latents");
        if (Call::cancelled(&call)) { error(CANTOR_ERR_CANCEL, "DECODE paused; retry the same latent boundary"); return CANTOR_PAUSED; }
        auto * vae = require_vae(&c->pipe); if (!vae) throw std::runtime_error("VAE model load failed");
        ModelHandle hold(c->store, vae);
        const int frames = int(state.codes.size()), capacity = frames * 1920;
        c->audio.resize(size_t(capacity) * 2);
        int count = vae_ggml_decode_tiled(vae, state.latents.data(), frames, c->audio.data(), capacity,
            c->pipe.params.vae_core, c->pipe.params.vae_halo, Call::cancelled, &call, Call::report);
        if (count < 0 || Call::cancelled(&call)) {
            c->audio.clear();
            if (call.stopped) { error(CANTOR_ERR_CANCEL, "DECODE paused; retry the same latent boundary"); return CANTOR_PAUSED; }
            throw std::runtime_error("VAE decode failed");
        }
        c->audio.resize(size_t(count) * 2);
        for (float x : c->audio) require(std::isfinite(x), "non-finite PCM output");
        c->samples = count; return CANTOR_DONE;
    } catch (const std::bad_alloc &) { error(CANTOR_ERR_OOM, "YuE2 stage allocation failed"); }
      catch (const std::invalid_argument & e) { error(CANTOR_ERR_OTHER, e.what()); }
      catch (const std::exception & e) { error(CANTOR_ERR_MODEL, e.what()); }
      catch (...) { error(CANTOR_ERR_OTHER, "unknown YuE2 stage error"); }
    if (c) { c->audio.clear(); c->samples = 0; qw3lm_kv_free(&c->pipe.kv); }
    return CANTOR_ERR;
}
}
