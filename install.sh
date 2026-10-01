#!/usr/bin/env bash
# Install Limpieza on Linux (Python 3.10+, no extra runtime packages).
# Usage: chmod +x install.sh && ./install.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "Limpieza installer (Linux)"
echo "=========================="

find_python() {
  local cmd
  for cmd in python3.13 python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
      if "$cmd" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        echo "$cmd"
        return 0
      fi
    fi
  done
  return 1
}

if ! PY="$(find_python)"; then
  cat <<'EOF'
Python 3.10 or newer was not found.

Debian/Ubuntu:
  sudo apt update
  sudo apt install python3 python3-venv python3-pip python3-tk

Fedora:
  sudo dnf install python3 python3-pip python3-tkinter

No se encontro Python 3.10+. Instala python3 y python3-venv, luego reintenta.
EOF
  exit 1
fi

echo "Using $($PY --version)"

if [[ ! -x .venv/bin/python ]]; then
  echo "Creating virtual environment in .venv ..."
  "$PY" -m venv .venv
fi

echo "Installing Limpieza (editable, no third-party runtime deps) ..."
.venv/bin/python -m pip install -e .

cat <<'EOF'

Installed. / Instalado.

Run / Ejecuta:

  .venv/bin/limpieza scan --safe
  .venv/bin/limpieza gui
  .venv/bin/python -m limpieza scan --safe

Activate the venv (optional) / Activar el entorno (opcional):

  source .venv/bin/activate

GUI on Debian/Ubuntu needs Tk:
  sudo apt install python3-tk

pipx (optional, isolated app install):
  sudo apt install pipx   # or: python3 -m pip install --user pipx
  pipx install .
EOF

.venv/bin/limpieza --version
exit 0
