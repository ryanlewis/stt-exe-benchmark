"""whisper.cpp via pywhispercpp (bundled binary)."""
from __future__ import annotations

import time

from benchmark.engines.base import Engine, TranscribeResult


class WhisperCppEngine(Engine):
    name = "whispercpp"

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def load(self) -> float:
        from pywhispercpp.model import Model

        t0 = time.monotonic()
        self._model = Model(self.model_name, n_threads=4, print_progress=False, print_realtime=False)
        return time.monotonic() - t0

    def transcribe(self, wav_path: str) -> TranscribeResult:
        t0 = time.monotonic()
        segments = self._model.transcribe(wav_path)
        text = " ".join(seg.text for seg in segments).strip()
        return TranscribeResult(text=text, compute_time_s=time.monotonic() - t0)

    def unload(self) -> None:
        self._model = None


def build(model_name: str) -> Engine:
    return WhisperCppEngine(model_name)
