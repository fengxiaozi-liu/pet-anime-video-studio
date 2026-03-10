#!/usr/bin/env bash
set -euo pipefail

# Pet Anime Video Studio - install helper
# - Creates .venv
# - Installs python deps
# - Installs ffmpeg (best-effort) on common Linux/macOS distros

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQ_FILE="$ROOT_DIR/backend/requirements.txt"
VENV_DIR="$ROOT_DIR/.venv"

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

log() {
  echo "[install] $*"
}

warn() {
  echo "[install] WARN: $*" >&2
}

install_ffmpeg_linux() {
  if need_cmd apt-get; then
    log "Installing ffmpeg via apt-get (Ubuntu/Debian/WSL)"
    sudo apt-get update
    sudo apt-get install -y ffmpeg
    return 0
  fi

  if need_cmd dnf; then
    log "Installing ffmpeg via dnf (Fedora/RHEL)"
    sudo dnf install -y ffmpeg
    return 0
  fi

  if need_cmd yum; then
    log "Installing ffmpeg via yum (CentOS/RHEL)"
    # best-effort; ffmpeg is often in RPM Fusion/EPEL. We try EPEL first.
    if ! rpm -qa | grep -qi epel-release; then
      warn "epel-release not detected; attempting to install"
      sudo yum install -y epel-release || true
    fi
    sudo yum install -y ffmpeg || return 1
    return 0
  fi

  return 1
}

install_ffmpeg_macos() {
  if need_cmd brew; then
    log "Installing ffmpeg via Homebrew"
    brew install ffmpeg
    return 0
  fi
  return 1
}

ensure_ffmpeg() {
  if need_cmd ffmpeg; then
    log "ffmpeg already installed: $(ffmpeg -version | head -n 1)"
    return 0
  fi

  log "ffmpeg not found. Attempting to install (best-effort)."

  case "$(uname -s)" in
    Linux)
      install_ffmpeg_linux || true
      ;;
    Darwin)
      install_ffmpeg_macos || true
      ;;
    *)
      warn "Unsupported OS for auto-install ffmpeg: $(uname -s)"
      ;;
  esac

  if ! need_cmd ffmpeg; then
    cat >&2 <<'EOF'
[install] ERROR: ffmpeg is still not found.

Please install ffmpeg manually:
- Ubuntu/Debian/WSL: sudo apt-get update && sudo apt-get install -y ffmpeg
- macOS: brew install ffmpeg
- Windows: winget install Gyan.FFmpeg  (then reopen terminal)

Then re-run this script.
EOF
    exit 1
  fi
}

ensure_python() {
  if need_cmd python3; then
    PY=python3
  elif need_cmd python; then
    PY=python
  else
    echo "[install] ERROR: python3 not found" >&2
    exit 1
  fi

  log "Using python: $PY ($($PY --version 2>&1))"
}

create_venv_and_install() {
  ensure_python

  if [ ! -d "$VENV_DIR" ]; then
    log "Creating venv: $VENV_DIR"
    $PY -m venv "$VENV_DIR"
  else
    log "Venv already exists: $VENV_DIR"
  fi

  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"

  log "Upgrading pip"
  python -m pip install -U pip

  if [ ! -f "$REQ_FILE" ]; then
    echo "[install] ERROR: requirements not found: $REQ_FILE" >&2
    exit 1
  fi

  log "Installing python requirements: $REQ_FILE"
  pip install -r "$REQ_FILE"
}

main() {
  log "Project root: $ROOT_DIR"

  ensure_ffmpeg
  create_venv_and_install

  cat <<EOF

[install] Done.

Next:
  cd "$ROOT_DIR"
  source .venv/bin/activate
  uvicorn backend.app.main:app --reload --port 8000

Open:
  http://localhost:8000
EOF
}

main "$@"
