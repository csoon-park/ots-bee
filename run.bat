@echo off
REM OTS_BEE_WEB 실행 스크립트
cd /d "%~dp0backend"
echo 벌 질병탐지 서버를 시작합니다... http://localhost:5721
python main.py
