#!/usr/bin/env bash
# Shell script to run master runner on Linux / Raspberry Pi
cd "$(dirname "$0")"

if [ -f "./venv/bin/python3" ]; then
    PYTHON_CMD="./venv/bin/python3"
elif [ -f "./.venv/bin/python3" ]; then
    PYTHON_CMD="./.venv/bin/python3"
else
    echo "⚠️ Virtual environment not found. Running setup.sh..."
    ./setup.sh
    PYTHON_CMD="./venv/bin/python3"
fi

$PYTHON_CMD run.py
