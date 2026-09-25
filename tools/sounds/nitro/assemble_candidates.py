"""WP-19: gather the revoiced takes, fillers and presence lines into one
staging folder laid out like E:\\Felt\\Sounds\\candidates\\, plus a
manifest.json the curation page reads (source, prompt text, generator and
RVC settings, duration, Whisper transcript per file).

Only RVC'd audio goes in (one voice). Two RVC settings per non-verbal:
    rvcA = live felt-voice params (rmvpe+, index 0.66, protect 0.33)
    rvcB = breath-preserving (crepe, index 0.33, protect 0.5)
B is the "Bc" run: of the breath-preserving variants tried (rmvpe+ /
crepe / crepe with index 0), crepe with index 0.33 turned the fewest
sounds into words by Whisper (see WP-19 notes).

Usage (Nitro5, in ~/felt-voice-next):
    uv run --no-sync python wp19/assemble_candidates.py wp19/out wp19/out/candidates
"""

import json
import shutil
import sys
from pathlib import Path

from wp19_audio import duration

SRC_SETTING = {"A": "A", "Bc": "B"}
RVC_LABEL = {
    "A": "RVC A: live params (rmvpe+, index 0.66, protect 0.33)",
    "B": "RVC B: breath-preserving (crepe, index 0.33, protect 0.5)",
}


def main() -> None:
    work, dst = Path(sys.argv[1]), Path(sys.argv[2])
    if dst.exists():
        shutil.rmtree(dst)
    meta = {}
    for name in ("raw_cb/manifest_cb.json", "raw_orph/manifest_orph.json"):
        meta.update(json.loads((work / name).read_text()))
    stt = json.loads((work / "stt.json").read_text())
    stt_f = json.loads((work / "stt_fillers.json").read_text())
    manifest = {}
    for src_setting, setting in SRC_SETTING.items():
        for f in sorted((work / "rvc").glob(f"*/*_rvc{src_setting}.wav")):
            kind = f.parent.name
            base = f.stem.rsplit("_rvc", 1)[0]
            out_name = f"{base}_rvc{setting}.wav"
            (dst / kind).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, dst / kind / out_name)
            m = dict(meta[f"{kind}/{base}"])
            raw_stt = stt.get(f"{kind}/{base}.wav", {})
            this_stt = stt.get(f"{kind}/{f.name}", {})
            m.update({"rvc": setting, "rvc_label": RVC_LABEL[setting], "seconds": round(duration(f), 2),
                      "whisper": this_stt.get("text", ""), "whisper_words": this_stt.get("words", []),
                      "whisper_before_rvc": raw_stt.get("text", "")})
            manifest[f"{kind}/{out_name}"] = m
    fill_meta = json.loads((work / "fillers" / "manifest_fillers.json").read_text())
    for key, m in fill_meta.items():
        kind, name = key.split("/")
        (dst / kind).mkdir(parents=True, exist_ok=True)
        src = work / "fillers" / kind / f"{name}.wav"
        shutil.copyfile(src, dst / kind / f"{name}.wav")
        s = stt_f.get(f"{kind}/{name}.wav", {})
        manifest[f"{kind}/{name}.wav"] = {**m, "rvc": "live", "rvc_label": "live felt-voice (Turbo -> RVC A)",
                                          "whisper": s.get("text", "")}
    (dst / "manifest.json").write_text(json.dumps(manifest, indent=1))
    counts = {}
    for key in manifest:
        counts[key.split("/")[0]] = counts.get(key.split("/")[0], 0) + 1
    print(json.dumps({"files": len(manifest), "per_kind": counts}))


if __name__ == "__main__":
    main()
