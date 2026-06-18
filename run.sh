#!/usr/bin/env bash
# Ubuntu/Linux 에서 수동 실행 (systemd 없이 빠른 테스트용)
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR/backend"
PY="$DIR/backend/venv/bin/python"
[ -x "$PY" ] || PY="python3"
echo "벌 질병탐지 서버 시작... http://localhost:5721"
exec "$PY" main.py
