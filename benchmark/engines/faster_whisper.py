"""faster-whisper (CTranslate2, int8)."""
from __future__ import annotations

import time

from benchmark.engines.base import Engine, TranscribeResult

MODEL_MAP = {
    "tiny.en": "tiny.en",
    "base.en": "base.en",
    "small.en": "small.en",
    "distil-small.en": "distil-whisper/distil-small.en",
    "distil-large-v3": "distil-whisper/distil-large-v3",
}


class FasterWhisperEngine(Engine):
    name = "faster_whisper"

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def load(self) -> float:
        from faster_whisper import WhisperModel

        model_id = MODEL_MAP.get(self.model_name, self.model_name)
        t0 = time.monotonic()
        self._model = WhisperModel(model_id, device="cpu", compute_type="int8")
        return time.monotonic() - t0

    def transcribe(self, wav_path: str) -> TranscribeResult:
        t0 = time.monotonic()
        segments, _info = self._model.transcribe(wav_path, language="en", beam_size=1, vad_filter=False)
        text = " ".join(seg.text for seg in segments).strip()
        return TranscribeResult(text=text, compute_time_s=time.monotonic() - t0)

    def unload(self) -> None:
        self._model = None


def build(model_name: str) -> Engine:
    return FasterWhisperEngine(model_name)
