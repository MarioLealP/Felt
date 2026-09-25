"""WP-19: Orpheus 3B (canopylabs orpheus-3b-0.1-ft, unsloth Q4_K_M GGUF)
through the Nitro5's existing Ollama (CUDA), SNAC 24 kHz decoder on CPU.

Why this route: Ollama with CUDA was already installed on the Nitro5, and
`ollama pull hf.co/unsloth/orpheus-3b-0.1-ft-GGUF:Q4_K_M` plus raw-mode
/api/generate worked on the first try (~93 tok/s; real time needs ~84).
The desktop Vulkan llama.cpp route was not needed.

Prompt format (Orpheus special tokens as the GGUF names them):
    <custom_token_3><|begin_of_text|>{voice}: {text}<|eot_id|><custom_token_4><custom_token_5><custom_token_1>
The reply is a stream of <custom_token_N>; audio token i (0-based) maps to
SNAC code N - 10 - (i % 7) * 4096, 7 tokens per frame. Generation stops at
<custom_token_2> (end of speech).

Modes (Nitro5, in ~/felt-voice-next):
    uv run --no-sync python wp19/orpheus_gen.py nonverbals <out_dir> [kind ...]
        raw takes -> <out>/<kind>/<kind>_orph_<n>.wav + manifest_orph.json
    uv run --no-sync python wp19/orpheus_gen.py lines <out_dir> <voice> <prefix> [n_lines]
        round-3 speech timing test: synth (Ollama+SNAC), RVC A, streaming TTFA
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import numpy as np
import torch

from wp19_audio import Revoicer, trim, write_wav

OLLAMA = "http://localhost:11434/api/generate"
MODEL = "hf.co/unsloth/orpheus-3b-0.1-ft-GGUF:Q4_K_M"
SR = 24000
TOKEN_RE = re.compile(r"<custom_token_(\d+)>")

# kind -> list of (voice, text). Native Orpheus tags where the model has
# one (<laugh> <chuckle> <sigh> <yawn> <gasp> <groan>); plain phonetic text
# for the kinds it has no tag for. No <giggle> tag exists in the ft model.
PROMPTS = {
    "laugh": [("tara", "<laugh>"), ("leah", "<laugh>"), ("tara", "haha <laugh>"), ("leah", "hahaha <laugh>"),
              ("zoe", "<laugh>"), ("tara", "<laugh> <laugh>")],
    "chuckle": [("tara", "<chuckle>"), ("leah", "<chuckle>"), ("tara", "heh <chuckle>"), ("leah", "hm <chuckle>"),
                ("zoe", "<chuckle>"), ("tara", "<chuckle> mm.")],
    "giggle": [("tara", "hehehe <laugh>"), ("leah", "hehehe <chuckle>"), ("zoe", "teehee <laugh>"),
               ("tara", "hihihi <chuckle>"), ("leah", "ehehe <laugh>"), ("zoe", "hehehe <chuckle>")],
    "hehe": [("tara", "hehe <chuckle>"), ("leah", "hehe!"), ("zoe", "hehe <chuckle>"), ("tara", "hehe!"),
             ("leah", "hehe <chuckle>"), ("zoe", "hehe!")],
    "sigh": [("tara", "<sigh>"), ("leah", "<sigh>"), ("tara", "<sigh> mm."), ("leah", "hah <sigh>"),
             ("zoe", "<sigh>"), ("tara", "<sigh>...")],
    "yawn": [("tara", "<yawn>"), ("leah", "<yawn>"), ("tara", "<yawn> mm."), ("leah", "<yawn>..."),
             ("zoe", "<yawn>"), ("tara", "hwaah <yawn>")],
    "gasp": [("tara", "<gasp>"), ("leah", "<gasp>"), ("tara", "<gasp>!"), ("leah", "oh! <gasp>"),
             ("zoe", "<gasp>"), ("tara", "<gasp> huh?!")],
    "ugh": [("tara", "<groan>"), ("leah", "<groan>"), ("tara", "ugh <groan>"), ("leah", "<groan>..."),
            ("zoe", "<groan>"), ("tara", "urgh <groan>")],
    "hm": [("tara", "hm?"), ("leah", "hmm?"), ("zoe", "hm?"), ("tara", "mm?"), ("leah", "hm?"), ("zoe", "hmm?")],
    "mm-hm": [("tara", "mm-hm."), ("leah", "mhm."), ("zoe", "mm-hm."), ("tara", "mhm!"), ("leah", "mm-hm!"),
              ("zoe", "uh-huh.")],
    "ooh": [("tara", "ooh!"), ("leah", "oooh!"), ("zoe", "ooh!"), ("tara", "ohh!"), ("leah", "ooh..."),
            ("zoe", "oooh~")],
}
KEEP_PER_KIND = 4
MIN_S, MAX_S = 0.25, 3.0
# Yawns are naturally longer: allow up to 4 s and a longer generation cap.
MAX_S_KIND = {"yawn": 4.0}


def prompt_for(voice: str, text: str) -> str:
    return (f"<custom_token_3><|begin_of_text|>{voice}: {text}<|eot_id|>"
            "<custom_token_4><custom_token_5><custom_token_1>")


def options(seed: int, num_predict: int) -> dict:
    # canopylabs defaults: temperature 0.6, top_p 0.8, repetition_penalty >= 1.1
    return {"temperature": 0.6, "top_p": 0.8, "repeat_penalty": 1.1, "num_predict": num_predict,
            "num_ctx": 2048, "seed": seed, "stop": ["<custom_token_2>"]}


def audio_codes(text: str) -> list[int]:
    codes: list[int] = []
    for m in TOKEN_RE.finditer(text):
        n = int(m.group(1))
        if n < 10:  # specials (start/end of speech etc.)
            continue
        codes.append(n - 10 - (len(codes) % 7) * 4096)
    return codes


class Snac:
    def __init__(self, device: str = "cpu"):
        from snac import SNAC

        self.device = device
        self.model = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval().to(device)

    def decode(self, codes: list[int]) -> np.ndarray:
        n = len(codes) // 7
        l0, l1, l2 = [], [], []
        for f in range(n):
            c = codes[7 * f: 7 * f + 7]
            if any(not 0 <= x < 4096 for x in c):
                continue
            l0.append(c[0])
            l1 += [c[1], c[4]]
            l2 += [c[2], c[3], c[5], c[6]]
        if not l0:
            return np.zeros(0, dtype=np.float32)
        t = [torch.tensor(v, dtype=torch.int32, device=self.device).unsqueeze(0) for v in (l0, l1, l2)]
        with torch.inference_mode():
            audio = self.model.decode(t)
        return audio.squeeze().float().cpu().numpy()


def generate(client: httpx.Client, voice: str, text: str, seed: int, num_predict: int) -> tuple[str, dict]:
    r = client.post(OLLAMA, json={"model": MODEL, "prompt": prompt_for(voice, text), "raw": True, "stream": False,
                                  "keep_alive": "10m", "options": options(seed, num_predict)}, timeout=600)
    r.raise_for_status()
    d = r.json()
    return d["response"], {"eval_count": d.get("eval_count"), "eval_s": d.get("eval_duration", 0) / 1e9,
                           "prompt_eval_s": d.get("prompt_eval_duration", 0) / 1e9}


def ttfa(client: httpx.Client, snac: Snac, voice: str, text: str, seed: int) -> float:
    """Streaming time-to-first-audio: request sent -> 28 audio tokens (4
    frames, the usual Orpheus streaming window) received and decoded."""
    t0 = time.perf_counter()
    buf = ""
    with client.stream("POST", OLLAMA, json={"model": MODEL, "prompt": prompt_for(voice, text), "raw": True,
                                             "stream": True, "keep_alive": "10m",
                                             "options": options(seed, 1600)}, timeout=600) as r:
        for line in r.iter_lines():
            if not line:
                continue
            buf += json.loads(line).get("response", "")
            codes = audio_codes(buf)
            if len(codes) >= 28:
                snac.decode(codes[:28])
                return time.perf_counter() - t0
    return float("nan")


def gpu_used() -> int:
    out = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True)
    return int(out.strip())


def run_nonverbals(out: Path, kinds: list[str]) -> None:
    snac = Snac("cpu")
    client = httpx.Client()
    manifest_path = out / "manifest_orph.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    t_all = time.perf_counter()
    for kind in kinds:
        kept = 0
        for i, (voice, text) in enumerate(PROMPTS[kind]):
            if kept >= KEEP_PER_KIND:
                break
            seed = 700 + 13 * i
            resp, st = generate(client, voice, text, seed, num_predict=440 if kind == "yawn" else 320)
            y = trim(snac.decode(audio_codes(resp)), SR)
            d = len(y) / SR
            if not MIN_S <= d <= MAX_S_KIND.get(kind, MAX_S):
                print(f"  reject {kind} {voice} {text!r} ({d:.2f}s)", flush=True)
                continue
            kept += 1
            name = f"{kind}_orph_{kept}"
            write_wav(out / kind / f"{name}.wav", y, SR)
            manifest[f"{kind}/{name}"] = {"source": "orpheus-3b-q4km", "voice": voice, "text": text, "seed": seed,
                                          "temperature": 0.6, "top_p": 0.8, "raw_seconds": round(d, 2)}
            print(f"{name}: {voice} {text!r} {d:.2f}s ({st['eval_count']} tok in {st['eval_s']:.2f}s)", flush=True)
        manifest_path.write_text(json.dumps(manifest, indent=1))
    print(f"total {time.perf_counter() - t_all:.1f}s")


def run_lines(out: Path, voice: str, prefix: str, n_lines: int) -> None:
    sys.path.insert(0, str(Path.home() / "felt-voice-next"))
    from lines2 import LINES

    peak = {"gpu": 0}
    stop = threading.Event()

    def sampler():
        while not stop.is_set():
            try:
                peak["gpu"] = max(peak["gpu"], gpu_used())
            except Exception:
                pass
            time.sleep(0.2)

    threading.Thread(target=sampler, daemon=True).start()
    snac = Snac("cpu")
    rvc = Revoicer()
    client = httpx.Client()
    res = {"voice": voice, "vram_before_mib": gpu_used(), "lines": {}}
    # warm-up: loads the model into Ollama and RVC onto the GPU
    resp, _ = generate(client, voice, "Warm up.", 1, 400)
    write_wav(out / "_warm.wav", snac.decode(audio_codes(resp)), SR)
    rvc.convert(out / "_warm.wav", out / "_warm_rvc.wav", "A")
    for i, text in enumerate(LINES[:n_lines], 1):
        t0 = time.perf_counter()
        resp, st = generate(client, voice, text, 1000 + i, 1600)
        t1 = time.perf_counter()
        y = snac.decode(audio_codes(resp))
        t2 = time.perf_counter()
        raw = out / "raw" / f"{prefix}_{i:02d}.wav"
        write_wav(raw, y, SR)
        t3 = time.perf_counter()
        rvc.convert(raw, out / f"{prefix}_{i:02d}.wav", "A")
        t4 = time.perf_counter()
        first = ttfa(client, snac, voice, text, 1000 + i)
        row = {"audio_s": round(len(y) / SR, 2), "llm_s": round(t1 - t0, 2), "snac_s": round(t2 - t1, 2),
               "synth_s": round(t2 - t0, 2), "rvc_s": round(t4 - t3, 2), "total_s": round(t2 - t0 + t4 - t3, 2),
               "ttfa_s": round(first, 2), "tokens": st["eval_count"],
               "tok_per_s": round(st["eval_count"] / st["eval_s"], 1) if st["eval_s"] else None}
        res["lines"][f"{i:02d}"] = row
        print(i, row, flush=True)
    stop.set()
    res["vram_peak_total_mib"] = peak["gpu"]
    res["ollama_ps"] = httpx.get("http://localhost:11434/api/ps").json()
    (out / f"timings_{prefix}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "lines"}, indent=1))


if __name__ == "__main__":
    mode, out_dir = sys.argv[1], Path(sys.argv[2])
    if mode == "nonverbals":
        run_nonverbals(out_dir, sys.argv[3:] or list(PROMPTS))
    elif mode == "lines":
        run_lines(out_dir, sys.argv[3], sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 10)
    else:
        sys.exit(f"unknown mode {mode}")
