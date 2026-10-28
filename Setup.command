#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [[ ! -x .venv/bin/python ]]; then
    echo '请先运行 Install.command。'
    exit 1
fi
exec .venv/bin/python tools/macos_ui.py setup "$@"
