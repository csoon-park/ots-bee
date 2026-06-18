# OTS_BEE_WEB

`bee_yolov8_detection.pt` 결과만 보여주는 단일 기능 벌 질병탐지 앱.
모바일 웹에 최적화된 한 페이지로, 사진을 올리면 탐지 결과를 바로 보여줍니다.

[OTS_BeeDiseaseDetect](../OTS_BeeDiseaseDetect) 기반이지만 다음을 모두 제거한 최소 버전입니다.

- 로그인 / 인증 / DB
- 이미지 보정(선명화) · 타일 추론 · 클릭 인스펙트
- 비디오 분석 · 라벨링 · 질병 상세 정보 패널

## 기능 정리

| 기능 | 설명 |
|---|---|
| **사진 탐지** | 갤러리 선택 또는 카메라 촬영 → YOLOv8(`bee_yolov8_detection.pt`) 추론 → 박스·한글 라벨이 그려진 결과 이미지 표시 |
| **탐지 요약** | 상태 색상 배너(정상/경고/심각) + 클래스별 건수·신뢰도(%) 목록 |
| **질병 상세 정보** | 탐지된 질병 행을 탭하면 원인·증상·대처법·발생 시기·탐지 팁·경제적 영향·치료 전망을 펼쳐 표시 |
| **사진 저장** | 결과 이미지를 기기에 저장. iOS는 공유 시트의 "이미지 저장"으로 사진 앱에 저장, 안드로이드·데스크톱은 다운로드 |
| **공유** | Web Share API로 카카오톡·메시지 등에 결과 이미지 + 요약 텍스트 공유 |
| **권한·개인정보 안내** | 사진은 분석용으로만 서버 전송, 별도 저장·공유하지 않음을 명시 |
| **면책 문구** | "참고용이며 수의사 진단을 대체하지 않음"을 상단·하단·결과 카드 3곳에 표시 |

탐지만 하던 원본([OTS_BeeDiseaseDetect](../OTS_BeeDiseaseDetect))에서 **로그인·DB, 이미지 보정(선명화), 타일 추론, 클릭 인스펙트, 비디오 분석, 라벨링**은 모두 제거했습니다.

## 모바일·iOS 호환

- **iPhone / iPad (iOS Safari, WKWebView)** 대응
  - `viewport-fit=cover` + `env(safe-area-inset-*)` 로 노치·홈 인디케이터 영역 회피
  - `100dvh` 로 iOS 주소창 높이 변동에도 레이아웃 정상
  - `apple-mobile-web-app-*` 메타 + `apple-touch-icon` 으로 "홈 화면에 추가" 시 앱처럼 표시
  - `-webkit-backdrop-filter` 등 iOS 프리픽스 적용
- **사진 저장(iOS)** — iOS Safari는 `<a download>` 를 무시하므로, 공유 시트를 띄워 사용자가 "이미지 저장"으로 사진 앱에 넣도록 처리 (구형 iOS는 새 탭 + 길게 눌러 저장 안내로 폴백)
- iPad는 데스크톱 UA로 위장하므로 `maxTouchPoints` 로 함께 판별

## 구조

```
OTS_BEE_WEB/
├─ backend/
│  ├─ main.py                   # FastAPI: 모델 로드 + /api/detect + 프론트 서빙
│  ├─ bee_yolov8_detection.pt   # 임베딩된 모델 (50MB)
│  └─ requirements.txt
├─ frontend/
│  ├─ index.html                # 모바일 우선 단일 페이지
│  └─ ontec_logo.png
├─ deploy/
│  ├─ install.sh                # Ubuntu 설치 + systemd 자동 실행 등록
│  └─ ots-bee-web.service       # systemd 유닛 (참고용 템플릿)
├─ run.bat                      # Windows 로컬 실행
└─ run.sh                       # Linux 로컬 실행
```

기본 포트: **5721** (환경변수 `PORT` 로 변경 가능)

## 실행 (로컬 개발)

**Windows**
```bat
cd backend
pip install -r requirements.txt
python main.py
```
또는 `run.bat` 더블클릭.

**Linux/macOS**
```bash
cd backend
pip install -r requirements.txt
python3 main.py
```
또는 `bash run.sh`.

브라우저에서 http://localhost:5721 접속.
같은 와이파이의 휴대폰에서는 `http://<PC-IP>:5721` 로 접속하면 모바일 화면을 확인할 수 있습니다.

## 배포 (Ubuntu, systemd 자동 실행)

서버에 프로젝트를 올린 뒤 한 줄로 설치 + 부팅 시 자동 실행 등록까지 끝납니다.
`install.sh` 가 클론 위치를 자동으로 잡아 가상환경·의존성·서비스 파일을 만듭니다.

```bash
# 1) 프로젝트 배치 (예: /opt/OTS_BEE_WEB) 후 설치 스크립트 실행
sudo bash deploy/install.sh
```

이 스크립트가 하는 일:
1. 시스템 의존성 설치 — `python3-venv`, `libgl1`, `libglib2.0-0`(OpenCV), `fonts-nanum`(한글 라벨)
2. `backend/venv` 가상환경 생성 + `requirements.txt` 설치
3. `/etc/systemd/system/ots-bee-web.service` 생성 (실제 경로·사용자 자동 주입, 포트 5721)
4. `enable`(부팅 자동 실행) + `restart`(즉시 기동)

### 서비스 관리 명령어

```bash
sudo systemctl start    ots-bee-web    # 시작
sudo systemctl stop     ots-bee-web    # 중지
sudo systemctl restart  ots-bee-web    # 재시작 (코드 업데이트 후)
sudo systemctl status   ots-bee-web    # 상태 확인
sudo systemctl enable   ots-bee-web    # 부팅 시 자동 실행 켜기
sudo systemctl disable  ots-bee-web    # 자동 실행 끄기
sudo journalctl -u ots-bee-web -f      # 실시간 로그
```

### 포트 변경

`deploy/install.sh` 의 `PORT=5721` 또는 서비스 파일의 `Environment=PORT=...` 와 `--port` 값을
바꾼 뒤 `sudo systemctl daemon-reload && sudo systemctl restart ots-bee-web`.

### 방화벽 (필요 시)

```bash
sudo ufw allow 5721/tcp
```

## API

`POST /api/detect` — `image` (multipart 파일) 한 개를 받아 아래를 반환:

```json
{
  "annotated_image": "<base64 jpg>",
  "detections": [
    { "class": "Larva_Gypsum", "class_kr": "유충 석고병", "count": 2, "confidence": 91, "is_disease": true }
  ],
  "disease_details": {
    "Larva_Gypsum": {
      "name": "유충 석고병 (백묵병)",
      "cause": "...", "symptoms": "...", "response": ["...", "..."],
      "economic_impact": "...", "seasonal_info": "...",
      "detection_tips": "...", "treatment_success": "..."
    }
  },
  "total": 2,
  "status": "warning",
  "summary": "경고: 유충 석고병 감지"
}
```

## 클래스 (7종)

| 클래스 | 한글 | 질병 |
|---|---|---|
| Larva_Normal | 유충 정상 | |
| Larva_mite | 유충 응애 | ● |
| Larva_Gypsum | 유충 석고병 | ● |
| Larva_Butterfly | 유충 나비 | ● |
| Insect_normal | 성충 정상 | |
| Insect_mite | 성충 응애 | ● |
| insect_wing_crippled_virus_infection | 날개불구바이러스감염증 | ● |
