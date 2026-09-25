"""WP-19 step 1: non-verbal takes from FULL Chatterbox (0.5B, non-Turbo),
cloned from the same Teto reference clip felt-voice uses. Mario
(2026-09-25): "run the giggle, chuckle etc through the full non turbo".

Full Chatterbox has no paralinguistic tags, so every sound is written out
phonetically. Each kind gets 4 spellings x exaggeration {0.7, 0.9}, with
cfg_weight alternating 0.3 / 0.5 per spelling and a distinct seed per take.
Takes that trim to outside 0.25-3.0 s (rambling or silence) are dropped and
retried with a new seed, up to 3 times.

Output is RAW (Chatterbox's own Teto clone, not yet RVC): revoice_ab.py
does the RVC pass. Writes <out>/<kind>/<kind>_cb07_s1.wav ... and
<out>/manifest_cb.json.

Separate process from the live felt-voice (read-only import of nothing
but its paths). Load split copied from ~/felt-voice-next/bench_full.py:
load on CPU, then T3 in bf16 and the S3Gen decoder on the GPU.

Usage (Nitro5, in ~/felt-voice-next):
    uv run --no-sync python wp19/chatterbox_nonverbals.py <out_dir> [kind ...]
"""

import json
import sys
import time
from pathlib import Path

import torch

from wp19_audio import FELT_VOICE, trim, write_wav

# kind -> 4 phonetic spellings (index 0/2 use cfg 0.5, 1/3 use cfg 0.3)
TEXTS = {
    "giggle": ["hehehe!", "ehehe~", "hihihi!", "teehee!"],
    "laugh": ["ahaha!", "hahaha!", "ahahaha!", "pfft, hahaha!"],
    "chuckle": ["heh.", "heh heh.", "hm hm hm.", "hehe."],
    "hehe": ["hehe!", "hehe~", "ehehe.", "heheh."],
    "sigh": ["haaah...", "hhaaaa...", "hahh...", "phew..."],
    "yawn": ["haaaawm...", "hwaaah... mm.", "aaahhmm...", "hwaaaah..."],
    "gasp": ["hwah?!", "hah!", "huh?!", "ah!?"],
    "hm": ["hm?", "hmm?", "hm-hm?", "mm?"],
    "mm-hm": ["mm-hm.", "mhm.", "mm-hmm!", "uh-huh."],
    "ooh": ["ooh!", "oooh~", "ooh...!", "ohh!"],
    "ugh": ["ugh...", "ugh!", "uuugh...", "urgh."],
}
EXAGS = (0.7, 0.9)
MIN_S, MAX_S = 0.25, 3.0
MAX_TRIES = 3

OUT = Path(sys.argv[1])
KINDS = sys.argv[2:] or list(TEXTS)
REF = FELT_VOICE / "models" / "chatterbox" / "teto_ref.wav"
BF16 = torch.bfloat16


def load():
    from chatterbox.tts import ChatterboxTTS

    tts = ChatterboxTTS.from_pretrained(device="cpu")
    tts.watermarker.apply_watermark = lambda wav, sample_rate: wav
    tts.prepare_conditionals(str(REF))
    s3 = tts.s3gen
    for name, child in s3.named_children():
        if name not in ("tokenizer", "speaker_encoder"):
            child.to("cuda")
    for name, buf in list(s3.named_buffers(recurse=False)):
        setattr(s3, name, buf.to("cuda"))
    s3.__class__ = type("S3GenPinned", (type(s3),), {"device": property(lambda _s: torch.device("cuda"))})
    tts.t3.to(dtype=BF16).to("cuda")
    tts.device = "cuda"
    tts.conds = tts.conds.to("cuda")
    tts.conds.t3 = tts.conds.t3.to(dtype=BF16)
    # Non-verbals are <3 s: cap sampling at 150 speech tokens (6 s) so a
    # rambling take costs seconds, not the default 1000-token (40 s) run.
    orig = tts.t3.inference
    tts.t3.inference = lambda *a, **k: orig(*a, **{**k, "max_new_tokens": 150})
    torch.cuda.empty_cache()
    return tts


def main() -> None:
    from chatterbox.models.t3.modules.cond_enc import T3Cond

    t0 = time.perf_counter()
    tts = load()
    base = tts.conds.t3
    print(f"loaded in {time.perf_counter() - t0:.1f}s", flush=True)

    def set_exag(e: float) -> float:
        tts.conds.t3 = T3Cond(speaker_emb=base.speaker_emb, cond_prompt_speech_tokens=base.cond_prompt_speech_tokens,
                              emotion_adv=e * torch.ones(1, 1, 1)).to(device="cuda", dtype=BF16)
        return float(tts.conds.t3.emotion_adv[0, 0, 0])

    manifest_path = OUT / "manifest_cb.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    stats = {"generated": 0, "rejected": 0, "gen_s": []}
    for kind in KINDS:
        take = 0
        for ti, text in enumerate(TEXTS[kind]):
            cfg = 0.5 if ti % 2 == 0 else 0.3
            for exag in EXAGS:
                take += 1
                name = f"{kind}_cb{int(round(exag * 10)):02d}_s{take}"
                for attempt in range(MAX_TRIES):
                    seed = 1000 * (ti + 1) + 10 * take + attempt
                    e = set_exag(exag)
                    torch.manual_seed(seed)
                    g0 = time.perf_counter()
                    with torch.inference_mode():
                        wav = tts.generate(text, exaggeration=e, cfg_weight=cfg, temperature=0.8)
                    torch.cuda.synchronize()
                    stats["gen_s"].append(time.perf_counter() - g0)
                    y = trim(wav.squeeze(0).float().numpy(), tts.sr)
                    d = len(y) / tts.sr
                    stats["generated"] += 1
                    if MIN_S <= d <= MAX_S:
                        break
                    stats["rejected"] += 1
                    print(f"  reject {name} attempt {attempt} ({d:.2f}s)", flush=True)
                else:
                    print(f"  GAVE UP {name}", flush=True)
                    continue
                write_wav(OUT / kind / f"{name}.wav", y, tts.sr)
                manifest[f"{kind}/{name}"] = {"source": "chatterbox-full", "text": text, "exaggeration": exag,
                                              "cfg_weight": cfg, "temperature": 0.8, "seed": seed,
                                              "raw_seconds": round(d, 2)}
                print(f"{name}: {text!r} exag={exag} cfg={cfg} seed={seed} {d:.2f}s", flush=True)
        manifest_path.write_text(json.dumps(manifest, indent=1))
    g = sorted(stats["gen_s"])
    print(json.dumps({"generated": stats["generated"], "rejected": stats["rejected"],
                      "gen_median_s": round(g[len(g) // 2], 2) if g else None,
                      "total_s": round(time.perf_counter() - t0, 1),
                      "torch_max_allocated_mib": torch.cuda.max_memory_allocated() // 2**20}))


if __name__ == "__main__":
    main()
