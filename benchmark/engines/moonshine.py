"""Moonshine (Useful Sensors), ONNX Runtime."""
from __future__ import annotations

import time

import soundfile as sf

from benchmark.engines.base import Engine, TranscribeResult


class MoonshineEngine(Engine):
    name = "moonshine"

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._tokenizer = None
        self._preprocess = None
        self._encode = None
        self._uncached_decode = None
        self._cached_decode = None
        self._transcribe_fn = None

    def load(self) -> float:
        t0 = time.monotonic()
        import moonshine_onnx  # type: ignore

        self._transcribe_fn = moonshine_onnx.transcribe
        # warm up by calling with a tiny silence buffer to force model download/load
        import numpy as np

        silence = np.zeros(16000, dtype=np.float32)
        try:
            self._transcribe_fn(silence, self.model_name)
        except TypeError:
            from tempfile import NamedTemporaryFile

            with NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                sf.write(tmp.name, silence, 16000, subtype="PCM_16")
                self._transcribe_fn(tmp.name, self.model_name)
        return time.monotonic() - t0

    def transcribe(self, wav_path: str) -> TranscribeResult:
        t0 = time.monotonic()
        result = self._transcribe_fn(wav_path, self.model_name)
        text = result[0] if isinstance(result, (list, tuple)) else str(result)
        return TranscribeResult(text=text, compute_time_s=time.monotonic() - t0)

    def unload(self) -> None:
        self._transcribe_fn = None


def build(model_name: str) -> Engine:
    return MoonshineEngine(model_name)
