#!/usr/bin/env bash
# Muse CLI & Bridge Launcher (handles symlinks safely)
PRG="$0"
while [ -h "$PRG" ]; do
    ls=$(ls -ld "$PRG")
    link=$(expr "$ls" : '.*-> \(.*\)$')
    if expr "$link" : '/.*' > /dev/null; then
        PRG="$link"
    else
        PRG="$(dirname "$PRG")/$link"
    fi
done
APP_DIR="$(cd "$(dirname "$PRG")" && pwd)"
cd "$APP_DIR"

export PYTHONPATH="$APP_DIR:$PYTHONPATH"

PYTHON="/Users/ducna/auto-login-omp/.venv/bin/python"
if [ ! -f "$PYTHON" ]; then
    if [ -f "./.venv/bin/python" ]; then
        PYTHON="./.venv/bin/python"
    else
        PYTHON=$(command -v python3)
    fi
fi

if [ $# -eq 0 ]; then
    echo "Khởi động Muse OpenAI Bridge Server trên cổng 8766..."
    exec "$PYTHON" -m muse.cli serve
else
    exec "$PYTHON" -m muse.cli "$@"
fi
