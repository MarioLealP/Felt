"""WP-19 step 4: generates the static local curation page for Felt's sound
candidates. Per kind, each take is one row with its source (full
Chatterbox / Orpheus / live Turbo), the prompt text and generator
settings, and one player per RVC setting (A = live params, B =
breath-preserving) side by side, each with Keep / Reject and the live
Whisper transcript (a laugh transcribed as real words means it got
mangled into speech). "Download decisions.json" saves
{"kind/file.wav": "keep" | "reject"} for apply_keepers.py.

Deliberately a plain generated HTML file, not a server or a claude.ai
artifact: Mario opens candidates/curate.html directly in his local
Firefox (file://). The file list and metadata are baked into the page at
generation time; each <audio> uses a path relative to the page, which
works over file://. Decisions are also kept in localStorage so a reload
doesn't lose progress.

Reads candidates/manifest.json (written by nitro/assemble_candidates.py)
for labels; files without a manifest entry still show, just unlabelled.
Folders starting with "_" (e.g. _old_piper) are skipped.

Usage: uv run python build_curation_page.py
(no args - scans E:\\Felt\\Sounds\\candidates\\ and (re)writes curate.html there)
"""

import html
import json
import re
from pathlib import Path

CANDIDATES_DIR = Path(r"E:\Felt\Sounds\candidates")
OUTPUT_PATH = CANDIDATES_DIR / "curate.html"

KIND_ORDER = ["giggle", "laugh", "chuckle", "hehe", "sigh", "yawn", "gasp", "hm", "mm-hm", "ooh", "ugh",
              "filler", "presence"]
SOURCE_LABEL = {"chatterbox-full": "Chatterbox full", "orpheus-3b-q4km": "Orpheus 3B", "live-turbo": "live Turbo"}
RVC_TAG = re.compile(r"_rvc([AB])$")


def scan_candidates(root: Path) -> dict[str, list[str]]:
    """{kind: [filename, ...]} for every kind subfolder directly under
    `root`, skipping "_"-prefixed folders and anything not a .wav."""
    kinds: dict[str, list[str]] = {}
    if not root.is_dir():
        return kinds
    dirs = [p for p in root.iterdir() if p.is_dir() and not p.name.startswith("_")]
    dirs.sort(key=lambda p: (KIND_ORDER.index(p.name) if p.name in KIND_ORDER else 99, p.name))
    for kind_dir in dirs:
        wavs = sorted(f.name for f in kind_dir.iterdir() if f.is_file() and f.suffix.lower() == ".wav")
        if wavs:
            kinds[kind_dir.name] = wavs
    return kinds


def natural(s: str) -> list:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def group_takes(files: list[str]) -> dict[str, dict[str, str]]:
    """{take_base: {"A": file, "B": file}} for RVC'd takes; a file with no
    _rvcX suffix (fillers/presence) is its own take under key "live"."""
    takes: dict[str, dict[str, str]] = {}
    for f in files:
        stem = f[:-4]
        m = RVC_TAG.search(stem)
        if m:
            takes.setdefault(stem[: m.start()], {})[m.group(1)] = f
        else:
            takes.setdefault(stem, {})["live"] = f
    # Chatterbox takes first, then Orpheus, each in take order
    return dict(sorted(takes.items(), key=lambda kv: ("_orph_" in kv[0], natural(kv[0]))))


def describe(meta: dict) -> str:
    src = SOURCE_LABEL.get(meta.get("source", ""), meta.get("source", "?"))
    bits = [f'<b class="src {html.escape(meta.get("source", ""))}">{html.escape(src)}</b>']
    if meta.get("text"):
        bits.append(f'<span class="prompt">&ldquo;{html.escape(meta["text"])}&rdquo;</span>')
    params = []
    if "exaggeration" in meta:
        params.append(f"exag {meta['exaggeration']}")
    if "cfg_weight" in meta:
        params.append(f"cfg {meta['cfg_weight']}")
    if "voice" in meta:
        params.append(f"voice {meta['voice']}")
    if "seed" in meta:
        params.append(f"seed {meta['seed']}")
    if params:
        bits.append(f'<span class="params">{html.escape(" · ".join(params))}</span>')
    return " ".join(bits)


def player(kind: str, fname: str, meta: dict, label: str) -> str:
    key = f"{kind}/{fname}"
    whisper = meta.get("whisper", "")
    flag = ' <span class="wordy" title="Whisper heard real words">words</span>' if meta.get("whisper_words") else ""
    secs = f'{meta["seconds"]:.2f} s' if "seconds" in meta else ""
    return f"""
      <div class="cell" data-key="{html.escape(key)}">
        <span class="tag">{html.escape(label)} <span class="dim">{secs}</span></span>
        <audio controls preload="none" src="{html.escape(key)}"></audio>
        <div class="btns"><button class="keep" data-choice="keep">Keep</button><button class="reject" data-choice="reject">Reject</button><span class="status"></span></div>
        <span class="stt">Whisper: {html.escape(whisper) or "&mdash;"}{flag}</span>
        <span class="fname">{html.escape(fname)}</span>
      </div>"""


def render_html(kinds: dict[str, list[str]], manifest: dict[str, dict]) -> str:
    nav = " ".join(f'<a href="#k-{html.escape(k)}">{html.escape(k)} <span class="dim">{len(v)}</span></a>'
                   for k, v in kinds.items())
    labels = {"A": "RVC A · live params", "B": "RVC B · breath-preserving", "live": "live felt-voice"}
    sections = []
    for kind, files in kinds.items():
        rows = []
        for base, variants in group_takes(files).items():
            meta = manifest.get(f"{kind}/{next(iter(variants.values()))}", {})
            cells = [player(kind, variants[s], manifest.get(f"{kind}/{variants[s]}", {}), labels[s])
                     for s in ("A", "B", "live") if s in variants]
            before = meta.get("whisper_before_rvc")
            before_html = (f'<span class="dim before">before RVC, Whisper heard: {html.escape(before)}</span>'
                           if before else "")
            rows.append(f"""
    <div class="take">
      <div class="head"><span class="base">{html.escape(base)}</span> {describe(meta)} {before_html}</div>
      <div class="cells">{"".join(cells)}</div>
    </div>""")
        sections.append(f"""
  <section id="k-{html.escape(kind)}">
    <h2>{html.escape(kind)} <span class="dim">({len(files)} files)</span></h2>
    {"".join(rows)}
  </section>""")

    total = sum(len(v) for v in kinds.values())
    empty = "<p>No candidates found under E:\\Felt\\Sounds\\candidates\\ yet.</p>"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Felt sound candidates</title>
<style>
:root{{--bg:#0f0f10;--panel:#18181a;--line:#2a2a2e;--text:#e8e6e1;--dim:#9a978f;--acc:#f5d000;--b:#5ec8ff;--keep:#2f8f4e;--rej:#8f2f2f;--warn:#ff9a5e}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--text);font:15px/1.45 system-ui,sans-serif;margin:0 auto;max-width:1200px;padding:0 16px 80px}}
h1{{font-size:20px;letter-spacing:.08em;text-transform:uppercase;border-left:4px solid var(--acc);padding-left:10px;margin:24px 0 8px}}
h2{{font-size:15px;letter-spacing:.1em;text-transform:uppercase;color:var(--acc);margin:40px 0 8px;border-bottom:1px solid var(--line);padding-bottom:6px}}
.dim{{color:var(--dim);font-weight:400}}
.note{{color:var(--dim);font-size:13px;max-width:900px}}
#bar{{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 0;display:flex;flex-wrap:wrap;gap:10px;align-items:center}}
#bar button{{padding:8px 14px;font-size:14px}}
#summary{{color:var(--dim);font-size:13px}}
nav{{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;margin:8px 0}}
nav a{{color:var(--text);text-decoration:none;border-bottom:1px solid var(--line)}}
.take{{background:var(--panel);border:1px solid var(--line);padding:10px 12px;margin:10px 0}}
.head{{font-size:13px;margin-bottom:8px;display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline}}
.base{{font-family:ui-monospace,monospace;color:var(--dim)}}
.src{{font-weight:600}} .src.orpheus-3b-q4km{{color:var(--b)}} .src.chatterbox-full{{color:var(--acc)}}
.prompt{{font-style:italic}} .params{{color:var(--dim)}} .before{{font-size:12px}}
.cells{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(300px,100%),1fr));gap:12px}}
.cell{{border:1px solid var(--line);padding:8px;min-width:0}}
.cell.keep{{border-color:var(--keep);box-shadow:inset 3px 0 0 var(--keep)}}
.cell.reject{{opacity:.45;border-color:var(--rej)}}
.tag{{display:block;font-size:12px;color:var(--dim);margin-bottom:4px}}
audio{{width:100%;height:34px}}
.btns{{display:flex;gap:8px;align-items:center;margin-top:6px}}
button{{padding:4px 12px;border-radius:3px;border:1px solid #444;cursor:pointer;background:#222;color:var(--text);font:inherit}}
button.keep:hover,.cell.keep button.keep{{background:var(--keep)}}
button.reject:hover,.cell.reject button.reject{{background:var(--rej)}}
.status{{font-size:12px;color:var(--dim)}}
.stt{{display:block;font-size:12px;color:var(--dim);margin-top:5px;overflow-wrap:anywhere}}
.wordy{{color:var(--warn);border:1px solid var(--warn);padding:0 4px;font-size:11px;margin-left:4px}}
.fname{{display:block;font-family:ui-monospace,monospace;font-size:11px;color:#6d6a64;margin-top:3px;overflow-wrap:anywhere}}
</style>
</head>
<body>
<h1>Felt sound candidates</h1>
<p class="note">Pick keepers by ear. Every clip ends in the same RVC Teto model. Non-verbals come from
<b style="color:var(--acc)">full Chatterbox</b> (sounds written out phonetically, Teto clone) and
<b style="color:var(--b)">Orpheus 3B</b> (native tags such as &lt;laugh&gt;), each revoiced two ways:
<b>A</b> = the live felt-voice RVC params (rmvpe+, index 0.66, protect 0.33) and
<b>B</b> = breath-preserving (crepe, index 0.33, protect 0.5). Fillers and presence lines were rendered
by the live felt-voice (Turbo &rarr; RVC A). The Whisper line is the live STT's transcript; an orange
<span class="wordy">words</span> tag means it heard real words, which for a laugh or sigh usually means
RVC turned it into speech (Whisper is unreliable on one-word clips, so trust your ear). Choices are kept in
this browser; when done, press <b>Download decisions.json</b> and run <code>apply_keepers.py</code> on it.
Click a button again to undo it.</p>
<div id="bar">
  <button id="dl">Download decisions.json</button>
  <span id="summary"></span>
</div>
<nav>{nav}</nav>
{"".join(sections) if sections else empty}
<script>
const TOTAL = {total};
const STORE = "felt-sound-decisions-v1";
let decisions = {{}};
try {{ decisions = JSON.parse(localStorage.getItem(STORE) || "{{}}") || {{}}; }} catch (e) {{ decisions = {{}}; }}

function paint(cell) {{
  const d = decisions[cell.dataset.key];
  cell.classList.toggle("keep", d === "keep");
  cell.classList.toggle("reject", d === "reject");
  cell.querySelector(".status").textContent = d || "";
}}
function summary() {{
  const vals = Object.values(decisions);
  const kept = vals.filter(v => v === "keep").length;
  document.getElementById("summary").textContent = `${{vals.length}}/${{TOTAL}} reviewed · ${{kept}} kept`;
}}
function save() {{ try {{ localStorage.setItem(STORE, JSON.stringify(decisions)); }} catch (e) {{}} }}

document.querySelectorAll(".cell").forEach(cell => {{
  paint(cell);
  cell.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {{
    const key = cell.dataset.key, choice = b.dataset.choice;
    if (decisions[key] === choice) delete decisions[key]; else decisions[key] = choice;
    paint(cell); save(); summary();
  }}));
  cell.querySelector("audio").addEventListener("play", e => {{
    document.querySelectorAll("audio").forEach(a => {{ if (a !== e.target) a.pause(); }});
  }});
}});
document.getElementById("dl").addEventListener("click", () => {{
  const blob = new Blob([JSON.stringify(decisions, null, 2)], {{type: "application/json"}});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "decisions.json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}});
summary();
</script>
</body>
</html>
"""


def main() -> None:
    kinds = scan_candidates(CANDIDATES_DIR)
    manifest_path = CANDIDATES_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    OUTPUT_PATH.write_text(render_html(kinds, manifest), encoding="utf-8")
    total = sum(len(v) for v in kinds.values())
    unlabelled = sum(1 for k, v in kinds.items() for f in v if f"{k}/{f}" not in manifest)
    print(f"Wrote {OUTPUT_PATH} - {total} candidate(s) across {len(kinds)} kind(s), {unlabelled} without metadata.")
    for kind, files in kinds.items():
        print(f"  {kind}: {len(files)}")


if __name__ == "__main__":
    main()
