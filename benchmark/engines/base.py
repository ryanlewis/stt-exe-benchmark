"""Engine adapter interface."""
from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass
class TranscribeResult:
    text: str
    compute_time_s: float


class Engine(abc.ABC):
    name: str
    model_name: str

    @abc.abstractmethod
    def load(self) -> float:
        """Load the model. Returns cold-start seconds."""

    @abc.abstractmethod
    def transcribe(self, wav_path: str) -> TranscribeResult:
        """Transcribe a 16 kHz mono WAV file (offline mode)."""

    def unload(self) -> None:
        pass
