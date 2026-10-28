#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"

if [[ ! -x .venv/bin/python ]]; then
    task_python=""
    for task_candidate in "${COLLABO_PYTHON:-}" python3.12 python3.13 python3.11 python3; do
        if [[ -n "$task_candidate" ]] && command -v "$task_candidate" >/dev/null 2>&1; then
            if "$task_candidate" -c 'import sys, tkinter; assert sys.version_info >= (3,11)' >/dev/null 2>&1; then
                task_python="$task_candidate"
                break
            fi
        fi
    done
    if [[ -z "$task_python" ]]; then
        echo '请先从 https://www.python.org/downloads/macos/ 安装 Python 3.12 或更新版本，再运行此文件。'
        exit 1
    fi
    "$task_python" -m venv .venv
fi

.venv/bin/python -c 'import tkinter'
.venv/bin/python -m pip install -r requirements.txt
echo '安装完成。双击 Setup.command 填写连接信息，双击 Permissions.command 管理目录权限。'
