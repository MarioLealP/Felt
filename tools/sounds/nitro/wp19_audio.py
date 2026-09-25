"""WP-19 shared helpers for the Nitro5 batch scripts: silence trimming,
WAV writing, and the two RVC Teto settings every candidate goes through.

Runs inside ~/felt-voice-next's venv on the Nitro5 (it already has
chatterbox, infer_rvc_python, soundfile, numpy). Imports felt-voice's own
config read-only for the model/index paths; never touches the live service.
"""

from __future__ import annotations

import io
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

FELT_VOICE = Path.home() / "felt-voice"
sys.path.insert(0, str(FELT_VOICE / "src"))

# The two RVC settings (WP-19 step 3). "A" is byte-for-byte the live
# felt-voice rvc.py configuration; "B" is the breath-preserving variant.
# protect (consonant_breath_protection) 0.5 = no index blending on
# unvoiced frames at all, index 0.33 = less pull toward the training
# set's phonemes (the "lone laugh became 'See ya!'" failure mode).
RVC_SETTINGS = {
    "A": dict(pitch_algo="rmvpe+", index_influence=0.66, respiration_median_filtering=3,
              envelope_ratio=0.25, consonant_breath_protection=0.33),
    "B": dict(pitch_algo="rmvpe+", index_influence=0.33, respiration_median_filtering=3,
              envelope_ratio=0.25, consonant_breath_protection=0.5),
    # Alternatives tried because rmvpe+ still turned sounds into words (WP-19 notes):
    # crepe f0, and crepe with no index pull at all.
    "Bc": dict(pitch_algo="crepe", index_influence=0.33, respiration_median_filtering=3,
               envelope_ratio=0.25, consonant_breath_protection=0.5),
    "Bc0": dict(pitch_algo="crepe", index_influence=0.0, respiration_median_filtering=3,
                envelope_ratio=0.25, consonant_breath_protection=0.5),
}


def to_mono(x: np.ndarray) -> np.ndarray:
    return x.mean(axis=1) if x.ndim == 2 else x


def trim(x: np.ndarray, sr: int, floor_db: float = -42.0, pre: float = 0.04, post: float = 0.10,
         fade: float = 0.012) -> np.ndarray:
    """Cut leading/trailing silence. A 10 ms frame counts as sound when its
    RMS is within `floor_db` of the clip's loudest frame (and above -60
    dBFS absolute). Keeps a little padding and fades both ends so the cut
    never clicks."""
    x = to_mono(x).astype(np.float32)
    hop = max(1, int(sr * 0.01))
    n = len(x) // hop
    if n == 0:
        return x
    frames = x[: n * hop].reshape(n, hop)
    rms_db = 20 * np.log10(np.sqrt((frames**2).mean(axis=1)) + 1e-9)
    thr = max(rms_db.max() + floor_db, -60.0)
    loud = np.flatnonzero(rms_db > thr)
    if len(loud) == 0:
        return x[:0]
    a = max(0, loud[0] * hop - int(pre * sr))
    b = min(len(x), (loud[-1] + 1) * hop + int(post * sr))
    y = x[a:b].copy()
    f = min(int(fade * sr), len(y) // 2)
    if f > 0:
        ramp = np.linspace(0.0, 1.0, f, dtype=np.float32)
        y[:f] *= ramp
        y[-f:] *= ramp[::-1]
    return y


def wav_bytes(x: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, np.clip(x, -1, 1), sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def write_wav(path: Path, x: np.ndarray, sr: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.clip(x, -1, 1), sr, subtype="PCM_16")


def duration(path: Path) -> float:
    info = sf.info(str(path))
    return info.frames / info.samplerate


class Revoicer:
    """infer_rvc_python loader with one tag per RVC setting. Model and
    index paths come from felt-voice's own .env (read-only)."""

    def __init__(self, only_cpu: bool = False):
        from felt_voice.config import VoiceConfig
        from infer_rvc_python import BaseLoader

        cfg = VoiceConfig(_env_file=str(FELT_VOICE / ".env"))
        assert cfg.rvc_model_path, "FELT_VOICE_RVC_MODEL_PATH not set"
        self.loader = BaseLoader(only_cpu=only_cpu, hubert_path=None, rmvpe_path=None)
        for tag, params in RVC_SETTINGS.items():
            self.loader.apply_conf(tag=tag, file_model=cfg.rvc_model_path, pitch_lvl=0,
                                   file_index=cfg.rvc_index_path or "", **params)

    def convert(self, src: Path, dst: Path, setting: str) -> None:
        """src -> RVC(setting) -> dst. Never writes over src."""
        dst.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            shutil.copyfile(src, tmp_path)
            self.loader(str(tmp_path), setting, overwrite=True, show_progress=False)
            shutil.copyfile(tmp_path, dst)
        finally:
            tmp_path.unlink(missing_ok=True)
