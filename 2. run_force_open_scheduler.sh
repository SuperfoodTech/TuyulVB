#!/usr/bin/env bash
# Shell script to run force open scheduler on Linux
cd "$(dirname "$0")"
if [ -d "venv" ]; then
    PYTHON_CMD="./venv/bin/python3"
else
    PYTHON_CMD="python3"
fi
$PYTHON_CMD modules/shopee/force_open/scheduler.py
