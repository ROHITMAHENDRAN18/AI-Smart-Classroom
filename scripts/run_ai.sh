#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_ROOT" || exit 1

source "$PROJECT_ROOT/.venv/bin/activate"

python -m ai.face_recognition.face_track_association