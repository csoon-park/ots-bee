"""
OTS_BEE_WEB - 벌 질병탐지 (단일 기능)

bee_yolov8_detection.pt 결과만 보여주는 최소 앱.
- 로그인 없음
- 이미지 보정(선명화)·타일 추론·클릭 인스펙트 없음
- 업로드 → 추론 → 결과 이미지 1장만 반환

7개 클래스: Larva_Normal, Larva_mite, Larva_Gypsum, Larva_Butterfly,
           Insect_normal, Insect_mite, insect_wing_crippled_virus_infection
"""
import base64
import logging
import os
import threading

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ots_bee_web")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "bee_yolov8_detection.pt")
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

# ─── 클래스 정의 (bee_train.yaml 기반) ──────────────────────
CLASSES = [
    "Larva_Normal",
    "Larva_mite",
    "Larva_Gypsum",
    "Larva_Butterfly",
    "Insect_normal",
    "Insect_mite",
    "insect_wing_crippled_virus_infection",
]

CLASS_NAME_KR = {
    "Larva_Normal": "유충 정상",
    "Larva_mite": "유충 응애",
    "Larva_Gypsum": "유충 석고병",
    "Larva_Butterfly": "유충 나비",
    "Insect_normal": "성충 정상",
    "Insect_mite": "성충 응애",
    "insect_wing_crippled_virus_infection": "날개불구바이러스감염증",
}

DISEASE_CLASSES = {
    "Larva_mite", "Larva_Gypsum", "Larva_Butterfly",
    "Insect_mite", "insect_wing_crippled_virus_infection",
}

# 질병 상세 정보 (탐지 시 참고용으로 제공)
DISEASE_INFO = {
    "Larva_mite": {
        "name": "유충 응애 감염",
        "cause": "바로아 응애(Varroa destructor)에 의한 기생 감염",
        "symptoms": "유충에 응애가 부착되어 체액을 빨아먹으며, 유충이 위축되거나 변형됨",
        "response": [
            "응애 방제약 살포 (포름산, 옥살산 등)",
            "감염된 소비 제거 및 교체",
            "봉군 강세 유지로 자연적 방어력 강화",
            "정기적인 응애 모니터링 실시",
        ],
        "economic_impact": "응애 감염 시 꿀 생산량 40~60% 감소, 군체 붕괴 위험",
        "seasonal_info": "봄~가을 전 기간 발생, 특히 여름철 번식기에 급증",
        "detection_tips": "유충 주변에 갈색 점 형태의 응애가 보이면 즉시 방제 필요",
        "treatment_success": "초기 방제 시 85% 이상 회복 가능",
    },
    "Larva_Gypsum": {
        "name": "유충 석고병 (백묵병)",
        "cause": "Ascosphaera apis 곰팡이에 의한 감염, 고습도 환경에서 발생",
        "symptoms": "유충이 석고처럼 딱딱하게 굳어 흰색~검은색으로 변함",
        "response": [
            "벌통 환기 개선 및 습도 조절",
            "감염된 소비 제거 후 소각",
            "항진균제 처리",
            "벌통 위치를 건조한 곳으로 이동",
        ],
        "economic_impact": "감염 시 꿀 생산량 최대 30% 감소",
        "seasonal_info": "봄철(3-5월) 다습한 시기에 주로 발생",
        "detection_tips": "소문 앞에 흰색 미이라 형태의 죽은 유충 발견 시 검사 필요",
        "treatment_success": "조기 발견 시 90% 이상 회복 가능",
    },
    "Larva_Butterfly": {
        "name": "꿀벌부채명나방 피해",
        "cause": "꿀벌부채명나방(Galleria mellonella) 유충의 소비 가해",
        "symptoms": "소비에 터널을 파고 밀랍을 먹으며, 거미줄 같은 실을 남김",
        "response": [
            "감염된 소비 즉시 제거",
            "봉군 강세 유지",
            "벌통 청결 관리",
            "저온 보관으로 소비 보호",
        ],
        "economic_impact": "소비 손상으로 인한 직접적 경제 손실 발생",
        "seasonal_info": "여름~가을 고온기에 주로 발생",
        "detection_tips": "소비에 거미줄 모양의 실이 보이면 명나방 유충 의심",
        "treatment_success": "신속 제거 시 피해 최소화 가능",
    },
    "Insect_mite": {
        "name": "성충 응애 감염",
        "cause": "바로아 응애가 성충 벌의 체표에 기생",
        "symptoms": "성충 벌의 비행 능력 저하, 수명 단축, 날개 기형 발생 가능",
        "response": [
            "응애 방제약 사용 (포름산, 아피스탄 등)",
            "감염 정도에 따른 단계별 방제",
            "봉군 관리 강화",
            "정기적 모니터링",
        ],
        "economic_impact": "군체 약화로 꿀 생산량 감소 및 분봉 능력 저하",
        "seasonal_info": "연중 발생하나 여름~가을에 특히 심각",
        "detection_tips": "성충 벌 등에 갈색 타원형 응애가 보이면 즉시 방제",
        "treatment_success": "체계적 방제 시 80% 이상 효과",
    },
    "insect_wing_crippled_virus_infection": {
        "name": "날개불구바이러스 감염증 (DWV)",
        "cause": "Deformed Wing Virus(DWV), 주로 바로아 응애를 통해 전파",
        "symptoms": "성충 벌의 날개가 기형으로 발달, 비행 불가, 체구 왜소화",
        "response": [
            "바로아 응애 방제가 가장 중요 (바이러스 매개체 제거)",
            "감염된 벌 제거",
            "건강한 여왕벌로 교체",
            "봉군 영양 관리 강화",
        ],
        "economic_impact": "심각한 경우 군체 전체 붕괴(CCD) 초래, 농가 연간 수백만원 손실",
        "seasonal_info": "응애 번식기와 동일하게 여름~가을에 발생 빈도 증가",
        "detection_tips": "소문 앞에서 날개가 구겨지거나 짧은 벌이 기어다니면 즉시 검사",
        "treatment_success": "응애 방제와 병행 시 군체 회복 가능, 단 감염 개체는 회복 불가",
    },
}

# 시각화 색상 (BGR)
COLORS = {
    "Larva_Normal": (0, 255, 0),
    "Larva_mite": (0, 0, 255),
    "Larva_Gypsum": (255, 0, 0),
    "Larva_Butterfly": (255, 165, 0),
    "Insect_normal": (0, 200, 0),
    "Insect_mite": (128, 0, 255),
    "insect_wing_crippled_virus_infection": (255, 255, 0),
}

# 결과 이미지가 너무 크면 모바일 전송 비용이 커지므로 긴 변을 이 값으로 제한
MAX_OUTPUT_DIM = 1280
DEFAULT_CONF = 0.25

# 한글 폰트 (Windows / Linux 호환)
FONT_PATHS = [
    "C:/Windows/Fonts/malgun.ttf",
    "C:/Windows/Fonts/gulim.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
]


def _get_font(size: int):
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ─── 모델 로드 (lazy + thread-safe) ─────────────────────────
_model = None
_model_lock = threading.Lock()


def load_model() -> YOLO:
    global _model
    with _model_lock:
        if _model is None:
            if not os.path.exists(MODEL_PATH):
                raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {MODEL_PATH}")
            _model = YOLO(MODEL_PATH)
            logger.info("YOLO 모델 로드 완료: %s", MODEL_PATH)
        return _model


def _draw_labels(cv_img, dets, font_size: int):
    """박스 위에 한글 라벨을 PIL 로 렌더링."""
    img_pil = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    font = _get_font(font_size)

    for d in dets:
        name = CLASSES[d["cls"]]
        color = COLORS[name]
        rgb = (color[2], color[1], color[0])
        label = f"{CLASS_NAME_KR.get(name, name)} {d['conf']:.2f}"
        x1, y1 = d["bbox"][0], d["bbox"][1]
        text_y = max(y1 - font_size - 4, 0)
        bbox = draw.textbbox((x1, text_y), label, font=font)
        draw.rectangle([bbox[0] - 2, bbox[1] - 2, bbox[2] + 2, bbox[3] + 2], fill=(255, 255, 255))
        draw.text((x1, text_y), label, font=font, fill=rgb)

    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


def detect(image_bytes: bytes, conf: float = DEFAULT_CONF) -> dict:
    """원본 이미지에 바로 추론 → 박스 친 결과 이미지 1장 + 요약 반환."""
    arr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("이미지를 읽을 수 없습니다.")

    model = load_model()
    # 원본 해상도 그대로 추론 (ultralytics 가 내부적으로 letterbox 처리)
    results = model(image, conf=conf)[0]

    dets = []
    for r in results.boxes.data.tolist():
        x1, y1, x2, y2, c, cls = r
        cls = int(cls)
        if cls < 0 or cls >= len(CLASSES):
            continue
        dets.append({"cls": cls, "conf": float(c), "bbox": [int(x1), int(y1), int(x2), int(y2)]})

    # 시각화
    vis = image.copy()
    for d in dets:
        name = CLASSES[d["cls"]]
        x1, y1, x2, y2 = d["bbox"]
        cv2.rectangle(vis, (x1, y1), (x2, y2), COLORS[name], 2)

    # 긴 변 기준 다운스케일 (라벨 폰트도 비율에 맞춤)
    h, w = vis.shape[:2]
    scale = min(1.0, MAX_OUTPUT_DIM / max(h, w))
    if scale < 1.0:
        vis = cv2.resize(vis, (int(w * scale), int(h * scale)))
        for d in dets:
            d["bbox"] = [int(v * scale) for v in d["bbox"]]
    font_size = max(14, int(min(vis.shape[:2]) * 0.03))
    vis = _draw_labels(vis, dets, font_size)

    _, buf = cv2.imencode(".jpg", vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
    annotated_b64 = base64.b64encode(buf).decode("utf-8")

    # 요약: 클래스별 개수
    counts: dict[str, int] = {}
    best: dict[str, float] = {}
    for d in dets:
        name = CLASSES[d["cls"]]
        counts[name] = counts.get(name, 0) + 1
        best[name] = max(best.get(name, 0.0), d["conf"])

    detected = []
    for name, cnt in counts.items():
        detected.append({
            "class": name,
            "class_kr": CLASS_NAME_KR.get(name, name),
            "count": cnt,
            "confidence": round(best[name] * 100),
            "is_disease": name in DISEASE_CLASSES,
        })
    detected.sort(key=lambda x: (-x["confidence"]))

    disease_found = [d for d in detected if d["is_disease"]]
    if not dets:
        status = "none"
        summary = "탐지된 객체가 없습니다"
    elif not disease_found:
        status = "normal"
        summary = "정상: 질병이 감지되지 않았습니다"
    else:
        names = ", ".join(d["class_kr"] for d in disease_found)
        if len(disease_found) <= 2:
            status = "warning"
            summary = f"경고: {names} 감지"
        else:
            status = "danger"
            summary = f"심각: {names} 감지"

    disease_details = {
        d["class"]: DISEASE_INFO[d["class"]]
        for d in detected
        if d["is_disease"] and d["class"] in DISEASE_INFO
    }

    return {
        "annotated_image": annotated_b64,
        "detections": detected,
        "disease_details": disease_details,
        "total": len(dets),
        "status": status,
        "summary": summary,
    }


# ─── FastAPI ────────────────────────────────────────────────
app = FastAPI(title="OTS BEE WEB", version="1.0.0")
app.add_middleware(GZipMiddleware, minimum_size=1000)

ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MAX_BYTES = 30 * 1024 * 1024  # 30MB


@app.on_event("startup")
async def _preload():
    try:
        load_model()
    except Exception:
        logger.exception("모델 preload 실패 — 첫 요청 시 재시도")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/detect")
async def api_detect(image: UploadFile = File(...)):
    ext = os.path.splitext(image.filename or "")[1].lower()
    if ext and ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 형식입니다: {ext}")

    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="파일이 너무 큽니다 (최대 30MB).")

    try:
        import asyncio
        result = await asyncio.to_thread(detect, data, DEFAULT_CONF)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("추론 실패")
        raise HTTPException(status_code=500, detail=f"분석 중 오류가 발생했습니다: {e}")

    return JSONResponse(content=result)


# ─── 프론트엔드 서빙 ────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/ontec_logo.png")
async def logo():
    return FileResponse(os.path.join(FRONTEND_DIR, "ontec_logo.png"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "5721")), reload=False)
