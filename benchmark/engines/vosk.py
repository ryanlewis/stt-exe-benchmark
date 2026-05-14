"""Vosk (Kaldi nnet3). Auto-downloads the small en-us model on first run."""
from __future__ import annotations

import json
import time
import urllib.request
import wave
import zipfile
from pathlib import Path

from benchmark.engines.base import Engine, TranscribeResult

MODEL_URLS = {
    "vosk-model-small-en-us-0.15": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
}
MODELS_DIR = Path(__file__).resolve().parents[1] / "corpora" / "models" / "vosk"


def _ensure_model(name: str) -> Path:
    target = MODELS_DIR / name
    if target.exists():
        return target
    url = MODEL_URLS[name]
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = MODELS_DIR / f"{name}.zip"
    print(f"  downloading {url}")
    urllib.request.urlretrieve(url, zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(MODELS_DIR)
    zip_path.unlink()
    return target


class VoskEngine(Engine):
    name = "vosk"

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def load(self) -> float:
        from vosk import Model, SetLogLevel

        SetLogLevel(-1)
        path = _ensure_model(self.model_name)
        t0 = time.monotonic()
        self._model = Model(str(path))
        return time.monotonic() - t0

    def transcribe(self, wav_path: str) -> TranscribeResult:
        from vosk import KaldiRecognizer

        t0 = time.monotonic()
        with wave.open(wav_path, "rb") as wf:
            sr = wf.getframerate()
            rec = KaldiRecognizer(self._model, sr)
            parts: list[str] = []
            while True:
                data = wf.readframes(4000)
                if not data:
                    break
                if rec.AcceptWaveform(data):
                    res = json.loads(rec.Result())
                    if res.get("text"):
                        parts.append(res["text"])
            final = json.loads(rec.FinalResult())
            if final.get("text"):
                parts.append(final["text"])
        text = " ".join(parts).strip()
        return TranscribeResult(text=text, compute_time_s=time.monotonic() - t0)

    def unload(self) -> None:
        self._model = None


def build(model_name: str) -> Engine:
    return VoskEngine(model_name)
