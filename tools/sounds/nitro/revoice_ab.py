"""WP-19 step 3: revoice raw non-verbal takes through the live RVC Teto
model with several settings, into a NEW folder (never in place, unlike
~/felt-voice/revoice_batch.py which overwrites its input).

    <raw_dir>/<kind>/<name>.wav  ->  <out_dir>/<kind>/<name>_rvc<S>.wav

for each setting S (see wp19_audio.RVC_SETTINGS: A = live params, B =
breath-preserving rmvpe+, Bc = breath-preserving crepe). Each output is
silence-trimmed again, since RVC can smear a little noise into the edges.

Usage (Nitro5, in ~/felt-voice-next):
    uv run --no-sync python wp19/revoice_ab.py <out_dir> <settings e.g. A,B,Bc> <raw_dir> [<raw_dir> ...]
"""

import json
import sys
import time
from pathlib import Path

import soundfile as sf

from wp19_audio import Revoicer, trim, write_wav


def main() -> None:
    out = Path(sys.argv[1])
    settings = sys.argv[2].split(",")
    raws = sorted(p for d in sys.argv[3:] for p in Path(d).glob("*/*.wav"))
    rvc = Revoicer()
    times: dict[str, list[float]] = {s: [] for s in settings}
    t_all = time.perf_counter()
    for s in settings:  # one setting at a time, so the loader doesn't reload per file
        for src in raws:
            dst = out / src.parent.name / f"{src.stem}_rvc{s}.wav"
            t0 = time.perf_counter()
            rvc.convert(src, dst, s)
            x, sr = sf.read(str(dst))
            write_wav(dst, trim(x, sr), sr)
            times[s].append(time.perf_counter() - t0)
        print(f"{s}: {len(raws)} files", flush=True)
    med = {s: round(sorted(v)[len(v) // 2], 3) for s, v in times.items() if v}
    print(json.dumps({"files_in": len(raws), "settings": settings, "median_s_per_file": med,
                      "total_s": round(time.perf_counter() - t_all, 1)}))


if __name__ == "__main__":
    main()
