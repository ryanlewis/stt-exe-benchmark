"""sherpa-onnx (k2-fsa). Offline NeMo Parakeet TDT 0.6B v2 (int8)."""
from __future__ import annotations

import tarfile
import time
import urllib.request
from pathlib import Path

import soundfile as sf

from benchmark.engines.base import Engine, TranscribeResult

MODELS_DIR = Path(__file__).resolve().parents[1] / "corpora" / "models" / "sherpa_onnx"

MODELS = {
    "parakeet-tdt-0.6b-v2": {
        "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8.tar.bz2",
        "dir": "sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8",
        "kind": "transducer",
    },
}


def _ensure(model_name: str) -> Path:
    cfg = MODELS[model_name]
    target = MODELS_DIR / cfg["dir"]
    if target.exists():
        return target
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    arc = MODELS_DIR / Path(cfg["url"]).name
    print(f"  downloading {cfg['url']}")
    urllib.request.urlretrieve(cfg["url"], arc)
    print("  extracting...")
    with tarfile.open(arc, "r:bz2") as tf:
        tf.extractall(MODELS_DIR, filter="data")
    arc.unlink()
    return target


class SherpaOnnxEngine(Engine):
    name = "sherpa_onnx"

    def __init__(self, model_name: str):
        if model_name not in MODELS:
            raise ValueError(f"unknown sherpa-onnx model: {model_name}")
        self.model_name = model_name
        self._recognizer = None

    def load(self) -> float:
        import sherpa_onnx

        d = _ensure(self.model_name)
        cfg = MODELS[self.model_name]
        t0 = time.monotonic()
        if cfg["kind"] == "transducer":
            self._recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=str(d / "encoder.int8.onnx"),
                decoder=str(d / "decoder.int8.onnx"),
                joiner=str(d / "joiner.int8.onnx"),
                tokens=str(d / "tokens.txt"),
                num_threads=4,
                decoding_method="greedy_search",
                model_type="nemo_transducer",
            )
        else:
            raise RuntimeError(f"unhandled kind {cfg['kind']}")
        return time.monotonic() - t0

    def transcribe(self, wav_path: str) -> TranscribeResult:
        audio, sr = sf.read(wav_path, dtype="float32", always_2d=False)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        t0 = time.monotonic()
        stream = self._recognizer.create_stream()
        stream.accept_waveform(sr, audio)
        self._recognizer.decode_stream(stream)
        text = stream.result.text
        return TranscribeResult(text=text, compute_time_s=time.monotonic() - t0)

    def unload(self) -> None:
        self._recognizer = None


def build(model_name: str) -> Engine:
    return SherpaOnnxEngine(model_name)
