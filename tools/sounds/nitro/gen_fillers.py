"""WP-19 step 2: filler and presence lines through the LIVE felt-voice
/v1/tts (Chatterbox-Turbo -> RVC Teto, the voice she speaks with today).
Read-only use of the service: plain POSTs, no config or .env changes.

The first batch (2026-09-24) was made with the old Piper base voice and
its script wasn't saved; this replaces it. Three takes per line via
punctuation (six for "hmm"). Presence lines ("back!", "zip it", "rude!") are their own
kind, `presence`, so they're never used as slow-request fillers.

Each take is silence-trimmed. Writes <out>/filler/<line>_<n>.wav,
<out>/presence/<line>_<n>.wav and <out>/manifest_fillers.json.

Usage (Nitro5, in ~/felt-voice-next; FELT_VOICE_URL defaults to localhost):
    uv run --no-sync python wp19/gen_fillers.py <out_dir>
"""

import io
import json
import os
import sys
import time
from pathlib import Path

import httpx
import soundfile as sf

from wp19_audio import trim, write_wav

URL = os.environ.get("FELT_VOICE_URL", "http://localhost:8421") + "/v1/tts"

LINES = {
    "filler": {
        # Turbo+RVC often turns a bare "Hmm" into a word (Whisper: "Bye.",
        # "Fair."), so hmm gets three extra spellings.
        "hmm": ["Hmm.", "Hmm...", "Hmmm?", "Hmmmm...", "Mm... hmm.", "Hmm, hmm."],
        "one_sec": ["One sec.", "One sec!", "One sec..."],
        "let_me_see": ["Let me see.", "Let me see...", "Let me see!"],
        "ooh_okay": ["Ooh, okay.", "Ooh, okay!", "Ooh... okay."],
    },
    "presence": {
        "back": ["Back!", "Back!!", "Back~!"],
        "zip_it": ["Okay okay, I'll zip it.", "Okay, okay! I'll zip it.", "Okay okay... I'll zip it."],
        "rude": ["Rude!", "Rude!!", "Rude..."],
    },
}


def main() -> None:
    out = Path(sys.argv[1])
    manifest = {}
    with httpx.Client(timeout=120) as c:
        for kind, lines in LINES.items():
            for line, texts in lines.items():
                for n, text in enumerate(texts, 1):
                    t0 = time.perf_counter()
                    r = c.post(URL, json={"text": text})
                    elapsed = time.perf_counter() - t0
                    print(f"{kind}/{line}_{n}: {text!r} HTTP {r.status_code} {len(r.content)} B {elapsed:.2f}s",
                          flush=True)
                    r.raise_for_status()
                    x, sr = sf.read(io.BytesIO(r.content))
                    y = trim(x, sr)
                    name = f"{line}_{n}"
                    write_wav(out / kind / f"{name}.wav", y, sr)
                    manifest[f"{kind}/{name}"] = {"source": "live-turbo", "text": text,
                                                  "seconds": round(len(y) / sr, 2),
                                                  "request_s": round(elapsed, 2)}
    (out / "manifest_fillers.json").write_text(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
