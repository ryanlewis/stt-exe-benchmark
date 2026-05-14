"""Benchmark harness: runs an engine over the corpus, writes results.jsonl."""
from __future__ import annotations

import gc
import json
import platform
import socket
import sys
import time
from pathlib import Path
from typing import Iterable

import click
import psutil

from benchmark import metrics
from benchmark.engines.base import Engine

RESULTS_DIR = Path(__file__).resolve().parent / "results"
MANIFEST = Path(__file__).resolve().parent / "corpora" / "librispeech_manifest.jsonl"


ENGINES: dict[str, tuple[str, list[str]]] = {
    "sherpa_onnx": ("benchmark.engines.sherpa_onnx", ["parakeet-tdt-0.6b-v2"]),
    "faster_whisper": ("benchmark.engines.faster_whisper", ["tiny.en", "base.en", "small.en"]),
    "whispercpp": ("benchmark.engines.whispercpp", ["tiny.en", "base.en"]),
    "moonshine": ("benchmark.engines.moonshine", ["moonshine/tiny"]),
    "vosk": ("benchmark.engines.vosk", ["vosk-model-small-en-us-0.15"]),
}


def _load_manifest() -> list[dict]:
    if not MANIFEST.exists():
        raise SystemExit(f"missing manifest at {MANIFEST}; run benchmark.corpora.fetch first")
    return [json.loads(l) for l in MANIFEST.read_text().splitlines() if l.strip()]


def _import_engine(module: str, model: str) -> Engine:
    import importlib

    mod = importlib.import_module(module)
    return mod.build(model)


def _host_info() -> dict:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "ram_gb": round(psutil.virtual_memory().total / 1e9, 2),
    }


def _peak_rss_mb() -> float:
    return psutil.Process().memory_info().rss / 1e6


def run_one(engine_key: str, model: str, manifest: list[dict], repeats: int = 1) -> Path:
    module, _ = ENGINES[engine_key]
    print(f"\n=== {engine_key} / {model} ===")

    out_path = RESULTS_DIR / f"{engine_key}__{model.replace('/', '_')}.jsonl"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    host = _host_info()
    rss_before = _peak_rss_mb()

    eng = _import_engine(module, model)
    try:
        cold_start_s = eng.load()
    except Exception as e:
        print(f"  load failed: {e}")
        _write_failure(out_path, engine_key, model, host, "load", str(e))
        return out_path

    rss_loaded = _peak_rss_mb()
    print(f"  loaded in {cold_start_s:.2f}s (RSS {rss_loaded:.0f} MB)")

    rows: list[dict] = []
    peak_rss = rss_loaded

    for rec in manifest:
        per_repeat_times: list[float] = []
        last_hyp = ""
        for _ in range(repeats):
            try:
                r = eng.transcribe(rec["wav_path"])
                per_repeat_times.append(r.compute_time_s)
                last_hyp = r.text
                peak_rss = max(peak_rss, _peak_rss_mb())
            except Exception as e:
                print(f"  transcribe {rec['id']} failed: {e}")
                per_repeat_times.append(float("nan"))
                last_hyp = ""
        median_t = metrics.median(per_repeat_times)
        rows.append(
            {
                "id": rec["id"],
                "duration_s": rec["duration_s"],
                "reference": rec["transcript"],
                "hypothesis": last_hyp,
                "compute_time_s": median_t,
                "rtf": metrics.rtf(median_t, rec["duration_s"]),
            }
        )

    eng.unload()
    del eng
    gc.collect()

    refs = [r["reference"] for r in rows]
    hyps = [r["hypothesis"] for r in rows]
    summary = {
        "engine": engine_key,
        "model": model,
        "host": host,
        "cold_start_s": cold_start_s,
        "peak_rss_mb": peak_rss,
        "rss_loaded_mb": rss_loaded,
        "rss_before_load_mb": rss_before,
        "n_utterances": len(rows),
        "total_audio_s": sum(r["duration_s"] for r in rows),
        "total_compute_s": sum(r["compute_time_s"] for r in rows if r["compute_time_s"] == r["compute_time_s"]),
        "wer": metrics.wer(refs, hyps),
        "rtf_median": metrics.median([r["rtf"] for r in rows]),
        "rtf_percentiles": metrics.percentiles([r["rtf"] for r in rows]),
        "compute_time_percentiles": metrics.percentiles([r["compute_time_s"] for r in rows]),
        "repeats_per_utterance": repeats,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    print(
        f"  WER {summary['wer']*100:.2f}% | RTF median {summary['rtf_median']:.3f} "
        f"| P95 {summary['rtf_percentiles']['p95']:.3f} | peak RSS {peak_rss:.0f} MB"
    )

    _write_results(out_path, summary, rows)
    return out_path


def _write_results(path: Path, summary: dict, rows: list[dict]) -> None:
    with open(path, "w") as fh:
        fh.write(json.dumps({"_summary": True, **summary}) + "\n")
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def _write_failure(path: Path, engine: str, model: str, host: dict, phase: str, err: str) -> None:
    with open(path, "w") as fh:
        fh.write(
            json.dumps(
                {
                    "_summary": True,
                    "engine": engine,
                    "model": model,
                    "host": host,
                    "failed": True,
                    "phase": phase,
                    "error": err,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
            )
            + "\n"
        )


@click.command()
@click.option("--engine", "engine_keys", multiple=True, type=click.Choice(list(ENGINES)), help="engine(s) to run")
@click.option("--model", "models", multiple=True, help="model name(s); restricts to these")
@click.option("--all", "run_all", is_flag=True, help="run every engine × every model")
@click.option("--repeats", default=1, type=int, help="repeats per utterance, take median")
def main(engine_keys: tuple[str, ...], models: tuple[str, ...], run_all: bool, repeats: int) -> None:
    manifest = _load_manifest()
    print(f"loaded {len(manifest)} utterances ({sum(r['duration_s'] for r in manifest):.1f}s)")

    plan: list[tuple[str, str]] = []
    if run_all:
        for k, (_, ms) in ENGINES.items():
            for m in ms:
                plan.append((k, m))
    else:
        if not engine_keys:
            raise click.UsageError("specify --engine or --all")
        for k in engine_keys:
            ms = models or ENGINES[k][1]
            for m in ms:
                plan.append((k, m))

    print(f"plan: {len(plan)} runs")
    for k, m in plan:
        try:
            run_one(k, m, manifest, repeats=repeats)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"!! {k}/{m} crashed: {e}")
            out = RESULTS_DIR / f"{k}__{m.replace('/', '_')}.jsonl"
            _write_failure(out, k, m, _host_info(), "outer", str(e))


if __name__ == "__main__":
    main()
