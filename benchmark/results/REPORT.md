# STT bake-off on exe.dev

- VM `benchmark-vm` · 2 cores (2 logical) · 4.11 GB RAM
- Corpus: 20 utterances (164.5s total)
- Repeats per utterance: 1
- Timestamp: 2026-05-14T17:38:58

| Engine | Model | WER | RTF med | RTF P95 | Cold start | Peak RSS | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| faster_whisper | base.en | 3.17% | 0.125 | 0.238 | 1.42 s | 1319 MB | realtime + headroom |
| faster_whisper | small.en | 2.95% | 0.360 | 0.702 | 2.57 s | 1470 MB | realtime, low headroom |
| faster_whisper | tiny.en | 3.63% | 0.070 | 0.154 | 1.50 s | 1252 MB | realtime + headroom |
| moonshine | moonshine/tiny | 2.72% | 0.136 | 0.540 | 7.19 s | 1608 MB | realtime + headroom |
| sherpa_onnx | parakeet-tdt-0.6b-v2 | 0.91% | 0.158 | 0.232 | 1.65 s | 1302 MB | realtime + headroom |
| vosk | vosk-model-small-en-us-0.15 | 9.30% | 0.133 | 0.193 | 0.24 s | 1619 MB | realtime + headroom |
| whispercpp | base.en | 3.40% | 0.493 | 1.238 | 1.08 s | 1559 MB | realtime, low headroom |
| whispercpp | tiny.en | 3.85% | 0.223 | 0.446 | 0.57 s | 1412 MB | realtime + headroom |
