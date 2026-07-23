#!/usr/bin/env bash
# Shell script to run master runner on Linux
cd "$(dirname "$0")"
if [ -d "venv" ]; then
    PYTHON_CMD="./venv/bin/python3"
else
    PYTHON_CMD="python3"
fi
$PYTHON_CMD run.py
