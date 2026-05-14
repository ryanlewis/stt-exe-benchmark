# stt-exe-benchmark

**What does a $20/mo exe.dev plan get you for self-hosted CPU-only speech-to-text?**

A small benchmark of five open-source STT engines on the entry-tier exe.dev VM
— 2 vCPU / 4 GB RAM / no GPU. LibriSpeech test-clean, 20 utterances, ~164 s of
audio. Each engine transcribes the whole corpus; we record WER, RTF (compute
time / audio duration), cold-start, and peak RSS. The harness writes JSONL,
the reporter renders an HTML page.

## TL;DR

- **All five engines hit realtime** (RTF < 1.0) on 2 vCPU / 4 GB / no GPU.
- **Best accuracy**: sherpa-onnx running NVIDIA Parakeet-TDT 0.6B int8 —
  **0.91 % WER, RTF median 0.158** (P95 0.232). ~6× headroom over realtime.
- **Fastest**: faster-whisper `tiny.en` — RTF 0.070, but 3.63 % WER.
- One borderline: whisper.cpp `base.en` P95 RTF 1.238 — occasionally slips
  past realtime.
- The $20 exe.dev plan is **enough** for self-hosted realtime STT if you pick
  the right engine.

## Results

LibriSpeech test-clean, 20 utterances, 164.5 s of audio.
VM: 2 vCPU / 4 GB RAM / Linux x86_64 / Python 3.11.
Single run per utterance, offline (whole-file) mode, greedy decoding.

| Engine | Model | WER | RTF med | RTF P95 | Cold start | Peak RSS | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| sherpa-onnx | parakeet-tdt-0.6b-v2 (int8) | **0.91 %** | 0.158 | 0.232 | 1.65 s | 1302 MB | realtime + headroom |
| moonshine | moonshine/tiny | 2.72 % | 0.136 | 0.540 | 7.19 s | 1608 MB | realtime + headroom |
| faster-whisper | small.en | 2.95 % | 0.360 | 0.702 | 2.57 s | 1470 MB | realtime, low headroom |
| faster-whisper | base.en | 3.17 % | 0.125 | 0.238 | 1.42 s | 1319 MB | realtime + headroom |
| whisper.cpp | base.en | 3.40 % | 0.493 | 1.238 | 1.08 s | 1559 MB | realtime, low headroom |
| faster-whisper | tiny.en | 3.63 % | **0.070** | 0.154 | 1.50 s | 1252 MB | realtime + headroom |
| whisper.cpp | tiny.en | 3.85 % | 0.223 | 0.446 | 0.57 s | 1412 MB | realtime + headroom |
| vosk | small-en-us-0.15 | 9.30 % | 0.133 | 0.193 | 0.24 s | 1619 MB | realtime + headroom |

**What the columns mean**

- **Engine** — the inference framework that runs the model (e.g. faster-whisper uses CTranslate2 under the hood; sherpa-onnx uses ONNX Runtime).
- **Model** — the actual model weights. Same engine + different model often means very different accuracy and speed.
- **WER** — Word Error Rate. Percentage of words the engine got wrong vs the reference transcript (after lowercasing and stripping punctuation). Lower is better. **1 %** means roughly one wrong word per hundred.
- **RTF med** — Real-Time Factor, median across utterances. `compute_time / audio_duration`. **RTF 0.5** means transcribing 10 s of audio took 5 s. **Anything under 1.0 is realtime**; under 0.3 has comfortable headroom (you can also do other work, or fall behind briefly without losing the stream).
- **RTF P95** — same thing but the 95th percentile — the slowest 1-in-20 utterance. This matters more than the median for streaming pipelines: if your P95 is over 1.0, you'll occasionally fall behind, even though the average is fine.
- **Cold start** — seconds to load the model into memory and prepare it for the first transcription. A one-time cost per process — irrelevant for a long-running server, painful for a serverless / on-demand setup.
- **Peak RSS** — Peak Resident Set Size: the most RAM the process held at any point, in megabytes. Tells you whether the engine fits on the VM you're considering. Bear in mind this includes Python + libraries, not just the model.
- **Verdict** — a one-line summary of the RTF column, using these cutoffs:
  - **realtime + headroom** — median RTF < 0.3
  - **realtime, low headroom** — median RTF 0.3 – 1.0
  - **borderline** — median < 1.0 but P95 ≥ 1.0 (i.e. sometimes slips)
  - **slower than realtime** — median ≥ 1.0

Open `benchmark/results/REPORT.html` for the styled version with per-utterance
reference / hypothesis pairs.

## Engines tested

- [**sherpa-onnx**](https://github.com/k2-fsa/sherpa-onnx) (Apache-2.0) —
  `sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8`. NVIDIA Parakeet ported to
  ONNX, int8 quantized. ~600 M parameters but quantized to a ~600 MB archive.
- [**faster-whisper**](https://github.com/SYSTRAN/faster-whisper) (MIT) —
  CTranslate2 int8 build of OpenAI Whisper. Models tested: `tiny.en`,
  `base.en`, `small.en`.
- [**whisper.cpp**](https://github.com/ggerganov/whisper.cpp) (MIT) via
  [pywhispercpp](https://github.com/absadiki/pywhispercpp). Models tested:
  `tiny.en`, `base.en` (GGML q5_1).
- [**Moonshine**](https://github.com/usefulsensors/moonshine) (MIT) — ONNX
  build via `useful-moonshine-onnx`. Model tested: `moonshine/tiny`.
- [**Vosk**](https://github.com/alphacep/vosk-api) (Apache-2.0) —
  `vosk-model-small-en-us-0.15`. Streaming-first Kaldi reference; kept here
  as a floor.

All model weights are downloaded automatically on first run (engine adapters
and `benchmark.corpora.fetch`). Nothing is committed to this repo.

## Reproduce

### Locally

```fish
uv venv && source .venv/bin/activate.fish
uv pip install -e ".[all]"
python -m benchmark.corpora.fetch     # ~20 utterances from LibriSpeech via HF
python -m benchmark.harness --all     # ~10 min on modern x86_64
python -m benchmark.report            # writes REPORT.html + REPORT.md
open benchmark/results/REPORT.html
```

### On a fresh exe.dev VM

```fish
ssh exe.dev new --name=myvm --cpu=2 --memory=4GB --disk=30GB --json

# rsync the project up
rsync -az --exclude .venv --exclude __pycache__ --exclude 'benchmark/results/*' \
  ./ myvm.exe.xyz:~/stt-exe-benchmark/

ssh myvm.exe.xyz "cd stt-exe-benchmark && bash infra/bootstrap.sh"
ssh myvm.exe.xyz "cd stt-exe-benchmark && source .venv/bin/activate && \
  python -m benchmark.corpora.fetch && python -m benchmark.harness --all"

# pull results back
rsync -az myvm.exe.xyz:~/stt-exe-benchmark/benchmark/results/ ./benchmark/results/

# render locally
python -m benchmark.report
```

## What's measured

- **WER** vs LibriSpeech ground-truth transcripts, normalized
  (lowercase + punctuation stripped via jiwer).
- **RTF** = `compute_time / audio_duration`. Median, P95, P99 reported.
  RTF < 1.0 means the engine processes audio faster than realtime.
- **Cold-start** — model load (instantiation) time, measured separately
  from the first transcription.
- **Peak RSS** — measured via `psutil` over the lifetime of the run.

## Caveats

- 20 utterances is a small slice. LibriSpeech is read-aloud audiobook
  English in a studio — clean audio, formal prose. Numbers on noisy
  short-utterance audio will be different.
- No warm-up, single repetition per utterance. RTF has measurement
  noise from OS jitter / shared-VM hardware variance.
- Offline (whole-file) mode only. Streaming + endpointing + concurrent-stream
  capacity are not measured here. The numbers tell you whether realtime is
  *possible*; a streaming benchmark would tell you what the *latency*
  actually looks like in a pipeline.
- The exe.dev free / entry-tier plan caps `--cpu` at 2, which is why this
  is a 2 vCPU benchmark. Larger VM tiers exist on higher-tier plans.

## Repo layout

```
.
├── benchmark/
│   ├── corpora/           # fetch.py — downloads LibriSpeech subset (gitignored audio)
│   ├── engines/           # one adapter per engine, plus base.py
│   ├── harness.py         # entry point
│   ├── metrics.py         # WER, RTF, percentiles
│   ├── report.py          # JSONL → REPORT.html + REPORT.md
│   └── results/           # JSONL per run + the rendered reports
├── infra/
│   ├── bootstrap.sh       # on a fresh VM: apt deps + uv + .venv + .[all]
│   └── EXE_NOTES.md       # observed exe.dev quirks
├── server/                # placeholder for future streaming work
├── pyproject.toml
├── LICENSE
└── README.md
```

## License

MIT. See `LICENSE`.
