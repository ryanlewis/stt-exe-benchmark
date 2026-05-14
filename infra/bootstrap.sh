#!/usr/bin/env bash
# Run on a fresh exe.dev VM from the repo root: bash infra/bootstrap.sh
set -euo pipefail

echo "[bootstrap] apt deps"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    ffmpeg build-essential cmake git curl ca-certificates \
    python3-dev python3-venv libsndfile1

echo "[bootstrap] uv"
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
uv --version

echo "[bootstrap] python deps"
uv venv --python 3.11 .venv
# shellcheck disable=SC1091
source .venv/bin/activate
uv pip install -e ".[all]"

echo "[bootstrap] done. To run benchmark:"
echo "  source .venv/bin/activate"
echo "  python -m benchmark.corpora.fetch"
echo "  python -m benchmark.harness --all"
