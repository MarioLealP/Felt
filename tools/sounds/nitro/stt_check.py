"""WP-19 spot check: run every WAV under the given folders through the
live felt-voice Whisper (/v1/stt, read-only use) and flag transcripts that
contain real words. A laugh transcribed as "See ya!" means RVC (or the
generator) turned the sound into speech.

Usage: uv run --no-sync python wp19/stt_check.py <out.json> <dir> [<dir> ...]
       (FELT_VOICE_URL defaults to http://localhost:8421)
"""

import json
import os
import re
import sys
from pathlib import Path

import httpx

URL = os.environ.get("FELT_VOICE_URL", "http://localhost:8421") + "/v1/stt"

# Tokens built only from these letters read as vocal sounds (ha, hehe, hmm,
# mhm, ugh, ooh, pfft, urgh, whoa ...). A few real words that happen to use
# only these letters are still counted as words.
SOUND_TOKEN = re.compile(r"^[haeiouwmgpfrt]+$")
REAL_WORDS = {"me", "we", "am", "a", "i", "him", "how", "who", "home", "game", "go", "ago", "mug", "hug", "ma",
              "mom", "the", "to", "too", "two", "art", "are", "her", "hit", "hate", "heat", "put", "fat", "wait",
              "eight", "right", "what", "way", "war", "wow", "ow", "our", "hour", "ohio", "hear", "here", "hero",
              "free", "tree", "age", "page", "rage", "gem", "him", "hot", "heart", "hum", "hag", "hog"}


def words_in(text: str) -> list[str]:
    toks = re.findall(r"[a-z']+", text.lower().replace("-", " "))
    return [t for t in toks if not SOUND_TOKEN.match(t) or t in REAL_WORDS]


def main() -> None:
    out = Path(sys.argv[1])
    files = sorted(p for d in sys.argv[2:] for p in Path(d).rglob("*.wav"))
    results = json.loads(out.read_text()) if out.exists() else {}
    with httpx.Client(timeout=60) as c:
        for f in files:
            key = f"{f.parent.name}/{f.name}"
            r = c.post(URL, files={"file": (f.name, f.read_bytes(), "audio/wav")})
            r.raise_for_status()
            text = r.json()["text"].strip()
            results[key] = {"text": text, "words": words_in(text)}
    out.write_text(json.dumps(results, indent=1))
    print(f"{len(files)} files -> {out}")


if __name__ == "__main__":
    main()
