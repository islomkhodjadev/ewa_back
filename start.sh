#!/usr/bin/env bash
set -euo pipefail

# Minimal start script:
# - clone HF repo to models/
# - ensure git-lfs and pull LFS objects (with retries)
# - verify presence of model weights (pytorch_model.bin or model.safetensors)
# - start docker compose with docker compose.prod.yml

REPO="https://huggingface.co/intfloat/multilingual-e5-base"
MODEL_DIR="models/multilingual-e5-base"
COMPOSE_FILE="docker-compose.prod.yml"
LFS_RETRIES=5
LFS_SLEEP=10

echo
echo ">>> start.sh: clone, pull LFS, then docker compose up"
echo

# helper: check command exists
_cmd_exists() {
  command -v "$1" >/dev/null 2>&1
}

# 1) basic prechecks
if ! _cmd_exists git; then
  echo "ERROR: git is not installed. Please install git and retry." >&2
  exit 1
fi

if ! _cmd_exists docker; then
  echo "ERROR: docker is not installed or not in PATH." >&2
  exit 1
fi

# docker compose might be v2 plugin 'docker compose'
if _cmd_exists docker compose; then
  DOCKER_COMPOSE_CMD="docker compose"
elif docker compose version >/dev/null 2>&1; then
  DOCKER_COMPOSE_CMD="docker compose"
else
  echo "ERROR: docker compose not found. Install docker compose or use Docker Compose v2." >&2
  exit 1
fi

# Create parent models folder
mkdir -p models

# 2) clone if missing, otherwise fetch latest metadata
if [ ! -d "${MODEL_DIR}/.git" ]; then
  echo "Cloning ${REPO} -> ${MODEL_DIR} (shallow clone of default branch)"
  git clone --depth 1 --single-branch "${REPO}" "${MODEL_DIR}"
else
  echo "Model repo already exists. Fetching latest metadata..."
  git -C "${MODEL_DIR}" fetch --depth=1 origin || true
  git -C "${MODEL_DIR}" pull --ff-only || true
fi

# 3) ensure git-lfs initialized
if ! _cmd_exists git-lfs; then
  echo "git-lfs not found. Attempting to continue; consider installing git-lfs for faster LFS pulls."
else
  echo "Initializing git-lfs hooks..."
  git lfs install --local --force
fi

# 4) pull LFS objects with simple retry logic
pull_lfs() {
  if ! _cmd_exists git-lfs; then
    return 1
  fi

  echo "Running: git lfs fetch --all && git lfs checkout in ${MODEL_DIR}"
  git -C "${MODEL_DIR}" lfs fetch --all
  git -C "${MODEL_DIR}" lfs checkout
}

LFS_OK=0
if _cmd_exists git-lfs; then
  for attempt in $(seq 1 "${LFS_RETRIES}"); do
    echo "LFS pull attempt ${attempt}/${LFS_RETRIES}..."
    if pull_lfs; then
      echo "git-lfs pull/checkout succeeded."
      LFS_OK=1
      break
    else
      echo "git-lfs pull failed (attempt ${attempt}). Sleeping ${LFS_SLEEP}s and retrying..."
      sleep "${LFS_SLEEP}"
    fi
  done
else
  echo "Skipping git-lfs pull because git-lfs binary not found."
fi

# 5) verify we have a weights file (pytorch_model.bin or model.safetensors)
WEIGHT_FOUND=0
if [ -f "${MODEL_DIR}/pytorch_model.bin" ] || [ -f "${MODEL_DIR}/model.safetensors" ]; then
  WEIGHT_FOUND=1
fi

# Fallback: if weights missing and huggingface_hub is installed, try direct download of just weights
if [ "${WEIGHT_FOUND}" -eq 0 ]; then
  if python - <<'PY' >/dev/null 2>&1 <<'PY_EOF'
import importlib, sys
try:
    importlib.import_module('huggingface_hub')
    sys.exit(0)
except Exception:
    sys.exit(1)
PY_EOF
  then
    echo "Weights not found locally. huggingface_hub available — attempting to download weight file(s) directly (minimal files only)."
    python - <<'PY'
from huggingface_hub import hf_hub_download
import sys, os

repo = "intfloat/multilingual-e5-base"
target = os.path.join("models","multilingual-e5-base")
os.makedirs(target, exist_ok=True)

candidates = ["model.safetensors","pytorch_model.bin"]
for fname in candidates:
    try:
        print("Downloading", fname)
        hf_hub_download(repo_id=repo, filename=fname, local_dir=target)
        print("Downloaded", fname)
        sys.exit(0)
    except Exception as e:
        print("Could not download", fname, ":", e)
# if here, none succeeded
sys.exit(2)
PY
    # re-check
    if [ -f "${MODEL_DIR}/pytorch_model.bin" ] || [ -f "${MODEL_DIR}/model.safetensors" ]; then
      WEIGHT_FOUND=1
    fi
  else
    echo "huggingface_hub not available. If git-lfs pull failed and you don't want to download full repo, install huggingface_hub (`pip install huggingface_hub`) to allow minimal direct weight downloads."
  fi
fi

if [ "${WEIGHT_FOUND}" -eq 0 ]; then
  echo
  echo "WARNING: model weight not found in ${MODEL_DIR}."
  echo "Expected one of: pytorch_model.bin or model.safetensors"
  echo "You can either:"
  echo "  - install git-lfs and re-run `git -C ${MODEL_DIR} lfs pull`"
  echo "  - or install huggingface_hub and allow the script to fetch the weight directly"
  echo
  read -p "Continue to docker compose up anyway? [y/N] " yn || true
  case "$yn" in
    [Yy]* ) echo "Proceeding to docker compose up (but container may fail without weights)";;
    * ) echo "Aborting."; exit 1;;
  esac
else
  echo "Model weight file is present. Good to go."
fi

# 6) Bring up docker compose
if [ ! -f "${COMPOSE_FILE}" ]; then
  echo "ERROR: ${COMPOSE_FILE} not found in current directory $(pwd). Please run this script from the project root containing ${COMPOSE_FILE}." >&2
  exit 1
fi

echo "Starting docker compose using ${COMPOSE_FILE}..."
# Build and start in detached mode
${DOCKER_COMPOSE_CMD} -f "${COMPOSE_FILE}" up -d --build

echo
echo "Done. Containers started (if compose succeeded)."
echo "If you mounted the model as a volume in your compose file, ensure the container sees ${MODEL_DIR} at the expected path."
