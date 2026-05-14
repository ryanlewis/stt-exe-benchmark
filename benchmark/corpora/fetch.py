"""Download ~20 LibriSpeech test-clean utterances via HF datasets streaming."""
from __future__ import annotations

import json
from pathlib import Path

import soundfile as sf

N_UTTERANCES = 20
ROOT = Path(__file__).resolve().parent
AUDIO_DIR = ROOT / "audio" / "librispeech"
MANIFEST = ROOT / "librispeech_manifest.jsonl"


def main() -> None:
    if MANIFEST.exists():
        print(f"manifest exists at {MANIFEST}, skipping")
        return
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    from datasets import load_dataset

    print(f"streaming librispeech_asr/clean/test (first {N_UTTERANCES})...")
    ds = load_dataset("openslr/librispeech_asr", "clean", split="test", streaming=True, trust_remote_code=True)

    records = []
    for sample in ds:
        if len(records) >= N_UTTERANCES:
            break
        uid = sample["id"]
        audio = sample["audio"]
        sr = audio["sampling_rate"]
        array = audio["array"]
        wav = AUDIO_DIR / f"{uid}.wav"
        sf.write(wav, array, sr, subtype="PCM_16")
        records.append(
            {
                "id": uid,
                "wav_path": str(wav.resolve()),
                "transcript": sample["text"],
                "duration_s": float(len(array)) / sr,
                "sample_rate": int(sr),
            }
        )

    with open(MANIFEST, "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    total = sum(r["duration_s"] for r in records)
    print(f"wrote {len(records)} utterances ({total:.1f}s audio) → {MANIFEST}")


if __name__ == "__main__":
    main()
