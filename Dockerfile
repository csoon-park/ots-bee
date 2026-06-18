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

# ultralytics 가 의존성으로 풀버전 opencv-python(libxcb 등 X11 필요)을 다시 끌어온다.
# slim 이미지엔 X11 라이브러리가 없어 `import cv2` 가 ImportError 로 죽으므로,
# 모든 opencv 변형을 제거하고 GUI 의존성이 없는 headless 만 남긴다.
RUN pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python || true \
    && pip install --no-cache-dir opencv-python-headless

# 애플리케이션 소스
COPY backend ./backend
COPY frontend ./frontend

# Railway 가 $PORT 를 주입함. main.py 가 os.getenv("PORT") 로 읽음.
ENV PORT=8080
EXPOSE 8080

WORKDIR /app/backend
CMD ["python", "main.py"]
