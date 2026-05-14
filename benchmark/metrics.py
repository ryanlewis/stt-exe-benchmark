"""Metrics: WER + RTF + percentiles. Offline-mode only for v1."""
from __future__ import annotations

import re
import statistics
from typing import Iterable

import jiwer

_NORMALIZE = jiwer.Compose(
    [
        jiwer.ToLowerCase(),
        jiwer.RemovePunctuation(),
        jiwer.RemoveMultipleSpaces(),
        jiwer.Strip(),
        jiwer.ReduceToListOfListOfWords(),
    ]
)


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def wer(references: list[str], hypotheses: list[str]) -> float:
    refs = [normalize(r) for r in references]
    hyps = [normalize(h) for h in hypotheses]
    if not any(refs):
        return float("nan")
    return jiwer.wer(refs, hyps)


def rtf(compute_time_s: float, audio_duration_s: float) -> float:
    if audio_duration_s <= 0:
        return float("nan")
    return compute_time_s / audio_duration_s


def percentiles(values: Iterable[float], ps: tuple[int, ...] = (50, 95, 99)) -> dict[str, float]:
    vs = sorted(v for v in values if v == v)
    if not vs:
        return {f"p{p}": float("nan") for p in ps}
    return {f"p{p}": _percentile(vs, p) for p in ps}


def _percentile(sorted_vs: list[float], p: int) -> float:
    if not sorted_vs:
        return float("nan")
    if len(sorted_vs) == 1:
        return sorted_vs[0]
    k = (len(sorted_vs) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(sorted_vs) - 1)
    frac = k - lo
    return sorted_vs[lo] * (1 - frac) + sorted_vs[hi] * frac


def median(values: Iterable[float]) -> float:
    vs = [v for v in values if v == v]
    return statistics.median(vs) if vs else float("nan")
