#!/usr/bin/env bash
#
# OTS_BEE_WEB - Ubuntu 설치 + systemd 자동 실행 등록
# 프로젝트를 어디에 두든 이 스크립트가 경로를 자동으로 잡아 서비스를 만듭니다.
#
# 사용법:
#   sudo bash deploy/install.sh
#
set -euo pipefail

SERVICE_NAME="ots-bee-web"
PORT=5721

# deploy/ 위치 기준으로 프로젝트 루트 계산 (어디에 클론하든 동작)
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$DEPLOY_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"
VENV_DIR="$BACKEND_DIR/venv"

# sudo 로 실행해도 서비스는 원래 사용자로 돌도록
RUN_USER="${SUDO_USER:-$(whoami)}"

echo "▶ 프로젝트 : $PROJECT_DIR"
echo "▶ 사용자   : $RUN_USER"
echo "▶ 포트     : $PORT"

if [ "$(id -u)" -ne 0 ]; then
  echo "✗ root 권한이 필요합니다.  sudo bash deploy/install.sh 로 실행하세요." >&2
  exit 1
fi

# 1) 시스템 의존성: python venv, OpenCV 런타임(libgl), 한글 폰트(나눔)
apt-get update
apt-get install -y python3-venv python3-pip libgl1 libglib2.0-0 fonts-nanum

# 2) 가상환경 + 파이썬 의존성
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

# 3) systemd 유닛 생성 (실제 경로/사용자 주입)
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
cat > "$UNIT_PATH" <<EOF
[Unit]
Description=OTS BEE WEB - 벌 질병탐지 (YOLOv8)
After=network.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$BACKEND_DIR
Environment=PORT=$PORT
Environment=PYTHONUNBUFFERED=1
ExecStart=$VENV_DIR/bin/uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1 --timeout-keep-alive 300
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 4) 등록 + 부팅 시 자동 실행 + 즉시 기동
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
sleep 1
systemctl --no-pager status "$SERVICE_NAME" || true

echo ""
echo "✓ 설치 완료. 부팅 시 자동 실행됩니다."
echo "  접속:  http://<서버IP>:$PORT"
echo "  로그:  sudo journalctl -u $SERVICE_NAME -f"
