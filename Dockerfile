FROM python:3.10-slim

# 시스템 의존성
# - fonts-nanum: 결과 이미지의 한글 라벨 렌더링
# - opencv-python-headless 를 쓰므로 libGL 등 GUI 라이브러리는 불필요
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU 전용 torch 를 먼저 설치 (기본 CUDA 빌드는 2GB+ → 빌드/메모리 폭증 방지).
# 이후 ultralytics 는 이미 설치된 torch 를 그대로 사용.
RUN pip install --no-cache-dir torch torchvision \
        --index-url https://download.pytorch.org/whl/cpu

# 의존성 레이어 캐시를 위해 requirements 먼저 복사
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# 애플리케이션 소스
COPY backend ./backend
COPY frontend ./frontend

# Railway 가 $PORT 를 주입함. main.py 가 os.getenv("PORT") 로 읽음.
ENV PORT=8080
EXPOSE 8080

WORKDIR /app/backend
CMD ["python", "main.py"]
