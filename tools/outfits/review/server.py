r"""Outfit review app - local server (stdlib only; run with Windows Python).

A review batch is a folder:
    <batch>/pending/*          to look at: .vrm, audio (.wav/.mp3/.ogg) or images
                               (optional <name>.json sidecar: title, info, dest)
    <batch>/approved/, <batch>/rejected/   where Keep / Reject move them
    <batch>/.thumbs/<name>.webp            front snapshots the page posts back
    <batch>/refs/              reference files an item's sidecar "reference" names
                               (e.g. the neutral take a mood clip is compared with)
    <batch>/batch.json         {"title", "dest": <folder approved items go to> or null,
                                "hint": shown in the grid, e.g. when Claude reads the decisions}
    <batch>/finalized.log      what Finalize moved where
    <batch>/finalized.json     no-dest batches: Finalize records the keeps here

The page (index.html) views each VRM with three.js + three-vrm, plays Felt's
own .vrma animations from the Godot overlay's library, and calls:
    GET  /api/state            batch title/dest + every item with its state
    GET  /api/anims            the .vrma library (relative paths)
    GET  /files/<state>/<name> a VRM;  GET /anim/<path> a .vrma;  GET /thumbs/<name>
    POST /api/decide {name, to}   move between pending/approved/rejected/fix
    POST /api/comment {name, text} Mario's note, saved as "mario" in the sidecar
    POST /api/thumb  {name, data} save a snapshot (data: URL)
    POST /api/fit {name, fit}     WP-32: an accessory's tuned bone/size/pos/rot
An accessory item is a .glb whose sidecar names "base" (a VRM in refs/) and
"fit" {bone, size, fit_mode, rotate, pos, rot} - the page shows it on her,
attached the way the overlay's props.gd does.
    POST /api/finalize            move approved/* to each item's dest
    POST /api/ping                heartbeat; the server exits ~45 s after the
                                  window closes (no pings)

Usage:  python server.py [BATCH_DIR] [--port 8765] [--no-browser]
BATCH_DIR defaults to the most recently changed batch under E:\Felt\review.
"""

import argparse
import base64
import datetime
import json
import mimetypes
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).parent
REVIEW_ROOT = Path(r"E:\Felt\review")  # one sub-folder per batch; gitignored in the umbrella repo
ANIM_DIR = Path(r"E:\Felt\felt-character-assets\felt-godot-overlay\animations\library")
STATES = ("pending", "approved", "rejected", "fix")  # fix = "close, see my comment"
# What a batch can hold: 3D models, audio clips, images, live HTML pages.
KINDS = {".vrm": "vrm", ".glb": "accessory", ".wav": "audio", ".mp3": "audio", ".ogg": "audio",
         ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image",
         ".html": "page"}  # page = a self-contained live mockup (e.g. desktop design concepts)
_IDLE_EXIT_S = 45

mimetypes.add_type("model/gltf-binary", ".vrm")
mimetypes.add_type("model/gltf-binary", ".vrma")
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("audio/wav", ".wav")


class Batch:
    def __init__(self, root: Path):
        self.root = root
        for s in STATES:
            (root / s).mkdir(parents=True, exist_ok=True)
        (root / ".thumbs").mkdir(exist_ok=True)
        self.lock = threading.Lock()
        self.last_ping = None

    def meta(self):
        f = self.root / "batch.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}

    def find(self, name: str):
        for s in STATES:
            p = self.root / s / name
            if p.is_file():
                return s, p
        return None, None

    def items(self):
        out = []
        for s in STATES:
            for p in sorted(f for f in (self.root / s).iterdir() if f.suffix.lower() in KINDS):
                side = p.with_suffix(".json")
                info = json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}
                thumb = self.root / ".thumbs" / (p.stem + ".webp")
                out.append({
                    "name": p.name, "state": s, "info": info, "kind": KINDS[p.suffix.lower()],
                    "thumb": int(thumb.stat().st_mtime) if thumb.exists() else None,
                    "mtime": p.stat().st_mtime,
                })
        return out

    def decide(self, name: str, to: str):
        if to not in STATES:
            raise ValueError(f"bad state {to!r}")
        with self.lock:
            state, path = self.find(name)
            if path is None:
                raise FileNotFoundError(name)
            if state != to:
                shutil.move(str(path), str(self.root / to / name))
                side = path.with_suffix(".json")
                if side.exists():
                    shutil.move(str(side), str(self.root / to / side.name))
        return to

    def comment(self, name: str, text: str):
        with self.lock:
            state, path = self.find(name)
            if path is None:
                raise FileNotFoundError(name)
            side = path.with_suffix(".json")
            info = json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}
            if text.strip():
                info["mario"] = text.strip()
            else:
                info.pop("mario", None)
            side.write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")

    def fit(self, name: str, fit: dict):
        """WP-32: an accessory's tuned fit (bone, size, pos, rot) from the
        page's nudge panel, saved as "fit" in the sidecar."""
        with self.lock:
            state, path = self.find(name)
            if path is None:
                raise FileNotFoundError(name)
            side = path.with_suffix(".json")
            info = json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}
            info["fit"] = {
                **info.get("fit", {}),
                "bone": str(fit["bone"]),
                "size": float(fit["size"]),
                "pos": [round(float(v), 4) for v in fit["pos"]],
                "rot": [round(float(v), 1) for v in fit["rot"]],
            }
            side.write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")

    def finalize(self):
        default_dest = self.meta().get("dest")
        moved, skipped, recorded = [], [], []
        with self.lock:
            for p in sorted(f for f in (self.root / "approved").iterdir() if f.suffix.lower() in KINDS):
                side = p.with_suffix(".json")
                info = json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}
                dest = info.get("dest") or default_dest
                if not dest:
                    recorded.append(p.stem)  # no dest: the keep is the result, Claude acts on it
                    continue
                d = Path(dest)
                d.mkdir(parents=True, exist_ok=True)
                target = d / p.name
                if target.exists():
                    skipped.append({"name": p.name, "why": f"{target} already exists"})
                    continue
                shutil.move(str(p), str(target))
                done = self.root / "finalized"
                done.mkdir(exist_ok=True)
                if side.exists():
                    shutil.move(str(side), str(done / side.name))
                with open(self.root / "finalized.log", "a", encoding="utf-8") as log:
                    log.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M}\t{p.name}\t{target}\n")
                moved.append({"name": p.name, "to": str(target)})
            if not default_dest:
                # review-only batch (e.g. mockups): every decision is the result,
                # "needs fix" + notes included, so Finalize works without a keep
                def decided(state):
                    out = []
                    for f in sorted((self.root / state).glob("*")):
                        if f.suffix.lower() in KINDS:
                            side = f.with_suffix(".json")
                            info = json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}
                            out.append({"name": f.stem, "note": info.get("mario")})
                    return out

                stamp = f"{datetime.datetime.now():%Y-%m-%d %H:%M}"
                (self.root / "finalized.json").write_text(json.dumps({
                    "finalized": stamp, "approved": recorded,
                    "fix": decided("fix"), "rejected": decided("rejected")}, indent=1), encoding="utf-8")
                recorded = recorded or [d["name"] for d in decided("fix")]
        return {"moved": moved, "skipped": skipped, "recorded": recorded}


def anim_list():
    if not ANIM_DIR.is_dir():
        return []
    return sorted(str(p.relative_to(ANIM_DIR)).replace("\\", "/") for p in ANIM_DIR.rglob("*.vrma"))


def safe_join(base: Path, rel: str) -> Path:
    p = (base / rel).resolve()
    if base.resolve() not in p.parents:
        raise PermissionError(rel)
    return p


def make_handler(batch: Batch):
    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def _send(self, code, body: bytes, ctype="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj).encode())

        def _file(self, path: Path):
            if not path.is_file():
                return self._json({"error": "not found"}, 404)
            ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self._send(200, path.read_bytes(), ctype)

        def do_GET(self):
            url = unquote(urlparse(self.path).path)
            try:
                if url in ("/", "/index.html"):
                    return self._file(HERE / "index.html")
                if url == "/api/state":
                    m = batch.meta()
                    return self._json({"title": m.get("title", batch.root.name), "dest": m.get("dest"), "hint": m.get("hint"),
                                       "root": str(batch.root), "items": batch.items()})
                if url == "/api/anims":
                    return self._json(anim_list())
                if url.startswith("/files/"):
                    _, _, state, name = url.split("/", 3)
                    if state not in STATES:
                        raise PermissionError(state)
                    return self._file(safe_join(batch.root / state, name))
                if url.startswith("/anim/"):
                    return self._file(safe_join(ANIM_DIR, url[len("/anim/"):]))
                if url.startswith("/refs/"):  # reference clips/images items compare against (sidecar "reference")
                    return self._file(safe_join(batch.root / "refs", url[len("/refs/"):]))
                if url.startswith("/thumbs/"):
                    return self._file(safe_join(batch.root / ".thumbs", url[len("/thumbs/"):]))
                return self._json({"error": "not found"}, 404)
            except PermissionError:
                return self._json({"error": "forbidden"}, 403)

        def do_POST(self):
            url = urlparse(self.path).path
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
            try:
                if url == "/api/ping":
                    batch.last_ping = time.monotonic()
                    return self._json({"ok": True})
                if url == "/api/decide":
                    return self._json({"state": batch.decide(body["name"], body["to"])})
                if url == "/api/comment":
                    batch.comment(body["name"], body.get("text", ""))
                    return self._json({"ok": True})
                if url == "/api/fit":
                    batch.fit(body["name"], body["fit"])
                    return self._json({"ok": True})
                if url == "/api/thumb":
                    name = Path(body["name"]).stem
                    data = body["data"].split(",", 1)[1]
                    (batch.root / ".thumbs" / f"{name}.webp").write_bytes(base64.b64decode(data))
                    return self._json({"ok": True})
                if url == "/api/finalize":
                    return self._json(batch.finalize())
                return self._json({"error": "not found"}, 404)
            except (KeyError, ValueError, FileNotFoundError, OSError) as e:
                return self._json({"error": str(e)}, 400)

    return H


def watchdog(batch: Batch, server: ThreadingHTTPServer):
    """Exit once the window has stopped pinging (it pings every 5 s)."""
    while True:
        time.sleep(5)
        if batch.last_ping is not None and time.monotonic() - batch.last_ping > _IDLE_EXIT_S:
            print("window closed - stopping")
            server.shutdown()
            return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch", nargs="?", type=Path)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    root = args.batch
    if root is not None and not root.is_dir() and (REVIEW_ROOT / root).is_dir():
        root = REVIEW_ROOT / root  # a bare batch name, e.g. "wp33-tees"
    if root is not None and not (root / "pending").is_dir():
        sys.exit(f"no batch at {root} (expected a pending/ folder)")
    if root is None:
        batches = [p for p in REVIEW_ROOT.glob("*") if (p / "pending").is_dir()]
        if not batches:
            sys.exit(f"no batch under {REVIEW_ROOT}")
        root = max(batches, key=lambda p: max(f.stat().st_mtime for f in [p, *p.rglob("*")]))
    batch = Batch(root)
    for port in range(args.port, args.port + 20):  # the next free one if taken
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(batch))
            break
        except OSError:
            continue
    else:
        sys.exit(f"no free port in {args.port}-{args.port + 19}")
    url = f"http://127.0.0.1:{port}/"
    print(f"reviewing {batch.root} at {url}")
    threading.Thread(target=watchdog, args=(batch, server), daemon=True).start()
    if not args.no_browser and sys.platform == "win32":
        # An app-mode Edge window: no tabs or address bar, its own taskbar entry.
        subprocess.Popen(["cmd", "/c", "start", "", "msedge", f"--app={url}", "--window-size=1600,1000"])
    server.serve_forever()


if __name__ == "__main__":
    main()
