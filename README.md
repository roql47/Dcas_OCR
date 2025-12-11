# 📄 PaddleOCR 웹 애플리케이션

PaddleOCR을 활용한 이미지 텍스트 추출 웹 애플리케이션입니다.
React + Vite + Tailwind CSS 프론트엔드와 FastAPI 백엔드로 구성되어 있습니다.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![React](https://img.shields.io/badge/React-18.3-61dafb.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)
![Tailwind](https://img.shields.io/badge/Tailwind-3.4-38bdf8.svg)

## ✨ 주요 기능

- 🖼️ **다양한 이미지 포맷 지원**: PNG, JPG, JPEG, BMP, TIFF, WebP
- 📑 **PDF 파일 처리**: 다중 페이지 PDF 자동 처리
- 🌐 **다국어 OCR**: 한국어, 영어, 일본어, 중국어 등 지원
- 🎯 **신뢰도 필터링**: 낮은 신뢰도 결과 자동 제외
- 📊 **실시간 통계**: 줄 수, 글자 수, 평균 신뢰도 표시
- 🎨 **모던 UI**: Tailwind CSS 기반 다크 테마 인터페이스
- 📋 **클립보드 복사**: 원클릭 결과 복사
- 💾 **텍스트 다운로드**: TXT 파일로 저장

## 📁 프로젝트 구조

```
OCR2/
├── backend/
│   ├── main.py              # FastAPI 서버
│   └── __init__.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # 메인 React 컴포넌트
│   │   ├── main.jsx         # 엔트리 포인트
│   │   └── index.css        # Tailwind 스타일
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
├── ocr_processor.py         # PaddleOCR 로직 모듈
├── utils.py                 # 유틸리티 함수
├── requirements.txt         # Python 의존성
└── README.md
```

## 🚀 설치 및 실행

### 1. 사전 요구사항

- **Python 3.8 이상**
- **Node.js 18 이상**
- **Poppler** (PDF 처리용 - 선택사항)

### 2. 백엔드 설정

```bash
# 프로젝트 폴더로 이동
cd C:\Users\emr4\Desktop\OCR2

# 가상 환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate

# Python 패키지 설치
pip install -r requirements.txt
```

### 3. 프론트엔드 설정

```bash
# 프론트엔드 폴더로 이동
cd frontend

# npm 패키지 설치
npm install
```

### 4. 실행

**터미널 1 - 백엔드 서버:**
```bash
cd C:\Users\emr4\Desktop\OCR2
venv\Scripts\activate
cd backend
python main.py
```
백엔드 서버가 http://localhost:8000 에서 실행됩니다.

**터미널 2 - 프론트엔드 개발 서버:**
```bash
cd C:\Users\emr4\Desktop\OCR2\frontend
npm run dev
```
프론트엔드가 http://localhost:5173 에서 실행됩니다.

### 5. 접속

브라우저에서 **http://localhost:5173** 에 접속하면 애플리케이션을 사용할 수 있습니다.

## 🔧 API 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/` | API 상태 확인 |
| GET | `/api/health` | 헬스 체크 |
| GET | `/api/languages` | 지원 언어 목록 |
| POST | `/api/ocr` | OCR 처리 |

### OCR API 사용 예시

```bash
curl -X POST "http://localhost:8000/api/ocr" \
  -F "file=@image.png" \
  -F "confidence_threshold=0.3" \
  -F "language=korean"
```

## ⚙️ 설정 옵션

### 신뢰도 임계값

- **기본값**: 0.3 (30%)
- **범위**: 0.0 ~ 1.0
- **설명**: 이 값 이하의 신뢰도를 가진 인식 결과는 필터링됩니다.

### 지원 언어

| 언어 코드 | 언어명 |
|-----------|--------|
| `korean` | 한국어 |
| `en` | 영어 |
| `japan` | 일본어 |
| `ch` | 중국어 (간체) |
| `chinese_cht` | 중국어 (번체) |

## 📋 의존성

### Backend (Python)
- paddlepaddle >= 3.0.0
- paddleocr >= 2.9.0
- fastapi >= 0.115.0
- uvicorn >= 0.32.0
- opencv-python >= 4.8.0
- Pillow >= 10.0.0
- pdf2image >= 1.16.0
- numpy >= 2.0.0

### Frontend (Node.js)
- react 18.3
- vite 6.0
- tailwindcss 3.4
- axios 1.7
- lucide-react 0.468
- react-dropzone 14.3

## 🐛 문제 해결

### CORS 오류
백엔드 서버의 CORS 설정이 프론트엔드 주소를 허용하는지 확인하세요.

### OCR 초기화 실패
PaddleOCR과 PaddlePaddle이 올바르게 설치되었는지 확인하세요.

### PDF 처리 오류
Poppler가 시스템에 설치되어 있는지 확인하세요.

## 📜 라이선스

MIT License

## 🙏 크레딧

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - 다국어 OCR 엔진
- [FastAPI](https://fastapi.tiangolo.com/) - Python 웹 프레임워크
- [React](https://react.dev/) - UI 라이브러리
- [Tailwind CSS](https://tailwindcss.com/) - CSS 프레임워크
- [Lucide React](https://lucide.dev/) - 아이콘 라이브러리
