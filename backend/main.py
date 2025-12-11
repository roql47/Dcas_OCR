"""
main.py - FastAPI OCR API Server

Dcas 연동 및 병렬 OCR 처리 API를 제공합니다.
"""

import os
import sys

# ⚠️ 모든 import 전에 환경변수 설정 (최상단에 있어야 함!)
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'
os.environ['FLAGS_use_mkldnn'] = '1'

import tempfile
import shutil
import uuid
import threading
from pathlib import Path

from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 상위 디렉토리의 모듈 import를 위해 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from ocr_processor import OCRProcessor, OCRError, OCRInitError
from dcas_client import (
    DcasClient, 
    DcasAuthError, 
    DcasConnectionError, 
    DcasParseError,
    PatientInfo
)
from parallel_ocr import ParallelOCRProcessor, BatchOCRResult, job_manager

# OCR 프로세서 인스턴스 (전역 싱글톤 - 스레드 안전)
_global_ocr_processor: Optional[OCRProcessor] = None
_ocr_processor_lock = threading.Lock()
_ocr_initialized = False

# Dcas 클라이언트 세션 관리
dcas_sessions: Dict[str, DcasClient] = {}
dcas_sessions_lock = threading.Lock()

# 검사 정보 캐시 (cine_no -> study_info)
study_info_cache: Dict[str, Any] = {}
study_info_cache_lock = threading.Lock()

# 지원하는 파일 확장자
SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp', '.pdf'}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작/종료 시 이벤트 처리"""
    # Startup
    print("[START] PaddleOCR API Server starting...")
    
    # OCR 엔진 미리 초기화 (워밍업)
    warmup_ocr("korean")
    
    print("[OK] Dcas integration enabled")
    print("[OK] Server ready!")
    
    yield
    
    # Shutdown
    print("[STOP] Server shutting down...")
    # Dcas 세션 정리
    with dcas_sessions_lock:
        for session_id, client in dcas_sessions.items():
            try:
                client.logout()
            except:
                pass
        dcas_sessions.clear()


# FastAPI 앱 생성
app = FastAPI(
    title="PaddleOCR API",
    description="PaddleOCR 기반 이미지 텍스트 추출 API (Dcas 연동)",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 설정 (React 개발 서버 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============= Request/Response 모델 =============

class OCRRequest(BaseModel):
    confidence_threshold: float = 0.3
    include_confidence: bool = False
    language: str = "korean"


class OCRResponse(BaseModel):
    success: bool
    text: str = ""
    lines: list = []
    statistics: dict = {}
    error: str = ""


class DcasLoginRequest(BaseModel):
    user_id: str
    password: str


class DcasLoginResponse(BaseModel):
    success: bool
    session_id: str = ""
    message: str = ""


class PatientListRequest(BaseModel):
    session_id: Optional[str] = None
    modality: str = "XA"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    patient_id: str = ""
    patient_name: str = ""


class PatientItem(BaseModel):
    cine_no: str
    patient_id: str
    patient_name: str = ""
    gender: str = ""
    age: str = ""
    study_date: str = ""  # 검사 날짜


class PatientListResponse(BaseModel):
    success: bool
    patients: List[PatientItem] = []
    total: int = 0
    error: str = ""


class BatchOCRRequest(BaseModel):
    session_id: Optional[str] = None
    patients: List[PatientItem]
    max_workers: int = 4  # 이미지 다운로드용 (OCR은 순차 처리)
    language: str = "korean"
    confidence_threshold: float = 0.3


class BatchOCRResponse(BaseModel):
    success: bool
    job_id: str = ""
    message: str = ""
    error: str = ""


class JobStatusResponse(BaseModel):
    success: bool
    job: Optional[Dict[str, Any]] = None
    error: str = ""


class ExtractedData(BaseModel):
    """OCR 결과에서 추출된 데이터"""
    date: str = ""
    registration_no: str = ""
    gender: str = ""
    dap: str = ""  # 39.7 Gy·cm2 -> 39700
    ak: str = ""   # Air Kerma 값
    fluoro_time: str = ""  # 0:15:42
    col1: str = "0"
    col2: str = "0"
    col3: str = "0"
    run: str = ""  # 22/780
    room: str = "" # 1 또는 2


class ExtractDataRequest(BaseModel):
    """데이터 추출 요청"""
    ocr_text: str
    date: str = ""
    registration_no: str = ""
    gender: str = ""


class ExtractDataResponse(BaseModel):
    """데이터 추출 응답"""
    success: bool
    data: Optional[ExtractedData] = None
    error: str = ""


# ============= 헬퍼 함수 =============

def get_ocr_processor(lang: str = "korean") -> OCRProcessor:
    """OCR 프로세서 인스턴스를 가져옵니다 (전역 싱글톤)."""
    global _global_ocr_processor, _ocr_initialized
    
    with _ocr_processor_lock:
        if _global_ocr_processor is None or _global_ocr_processor.lang != lang:
            print(f"[INIT] OCR processor initializing... (lang: {lang})")
            _global_ocr_processor = OCRProcessor(lang=lang)
        return _global_ocr_processor


def warmup_ocr(lang: str = "korean"):
    """서버 시작 시 OCR 엔진을 미리 초기화합니다."""
    global _ocr_initialized
    
    if _ocr_initialized:
        return
    
    print("[WARMUP] Initializing OCR engine...")
    try:
        processor = get_ocr_processor(lang)
        # 엔진 초기화 강제 실행
        processor._initialize_ocr()
        _ocr_initialized = True
        print("[OK] OCR engine initialized!")
    except Exception as e:
        print(f"[WARN] OCR warmup failed: {e}")


def get_dcas_client(session_id: str) -> Optional[DcasClient]:
    """세션 ID로 Dcas 클라이언트를 가져옵니다."""
    with dcas_sessions_lock:
        return dcas_sessions.get(session_id)


def create_dcas_session(client: DcasClient) -> str:
    """새 Dcas 세션을 생성합니다."""
    session_id = str(uuid.uuid4())
    with dcas_sessions_lock:
        dcas_sessions[session_id] = client
    return session_id


# ============= 기본 엔드포인트 =============

@app.get("/")
async def root():
    """API 상태 확인"""
    return {"status": "ok", "message": "PaddleOCR API Server", "version": "2.0.0"}


@app.get("/api/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}


@app.get("/api/languages")
async def get_languages():
    """지원하는 언어 목록"""
    return {
        "languages": [
            {"code": "korean", "name": "한국어"},
            {"code": "en", "name": "영어"},
            {"code": "japan", "name": "일본어"},
            {"code": "ch", "name": "중국어(간체)"},
            {"code": "chinese_cht", "name": "중국어(번체)"},
        ]
    }


# ============= 기존 OCR 엔드포인트 =============

@app.post("/api/ocr", response_model=OCRResponse)
async def perform_ocr(
    file: UploadFile = File(...),
    confidence_threshold: float = Form(0.3),
    include_confidence: bool = Form(False),
    language: str = Form("korean")
):
    """
    이미지 파일에서 텍스트를 추출합니다.
    
    - **file**: 이미지 또는 PDF 파일
    - **confidence_threshold**: 신뢰도 임계값 (0.0 ~ 1.0)
    - **include_confidence**: 결과에 신뢰도 포함 여부
    - **language**: 인식 언어 코드
    """
    # 파일 확장자 확인
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다: {file_ext}. 지원 형식: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    
    # 임시 파일로 저장
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}{file_ext}")
    
    try:
        # 파일 저장
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # OCR 프로세서 가져오기
        processor = get_ocr_processor(language)
        
        # OCR 실행
        page_results = processor.process_file(
            temp_file_path,
            confidence_threshold=confidence_threshold
        )
        
        # 결과 처리
        all_lines = []
        all_text_parts = []
        
        for page_result in page_results:
            for r in page_result.results:
                line_data = {
                    "text": r.text,
                    "confidence": round(r.confidence, 4)
                }
                all_lines.append(line_data)
                
                if include_confidence:
                    all_text_parts.append(f"{r.text} (신뢰도: {r.confidence:.2%})")
                else:
                    all_text_parts.append(r.text)
        
        result_text = "\n".join(all_text_parts)
        
        # 통계 계산
        statistics = {
            "total_lines": len(all_lines),
            "total_characters": len(result_text.replace("\n", "").replace(" ", "")),
            "pages": len(page_results),
            "average_confidence": round(
                sum(line["confidence"] for line in all_lines) / len(all_lines), 4
            ) if all_lines else 0
        }
        
        return OCRResponse(
            success=True,
            text=result_text,
            lines=all_lines,
            statistics=statistics
        )
        
    except OCRInitError as e:
        return OCRResponse(success=False, error=f"OCR 초기화 오류: {str(e)}")
    except OCRError as e:
        return OCRResponse(success=False, error=f"OCR 처리 오류: {str(e)}")
    except Exception as e:
        return OCRResponse(success=False, error=f"오류 발생: {str(e)}")
    finally:
        # 임시 파일 정리
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


# ============= Dcas 연동 엔드포인트 =============

@app.post("/api/dcas/login", response_model=DcasLoginResponse)
async def dcas_login(request: DcasLoginRequest):
    """
    Dcas에 로그인합니다.
    
    - **user_id**: Dcas 사용자 ID
    - **password**: Dcas 비밀번호
    """
    try:
        client = DcasClient(request.user_id, request.password)
        client.login()
        
        session_id = create_dcas_session(client)
        
        return DcasLoginResponse(
            success=True,
            session_id=session_id,
            message="로그인 성공"
        )
        
    except DcasAuthError as e:
        return DcasLoginResponse(
            success=False,
            message=str(e)
        )
    except DcasConnectionError as e:
        return DcasLoginResponse(
            success=False,
            message=f"서버 연결 실패: {str(e)}"
        )
    except Exception as e:
        return DcasLoginResponse(
            success=False,
            message=f"오류 발생: {str(e)}"
        )


@app.post("/api/dcas/logout")
async def dcas_logout(session_id: str = Form(...)):
    """Dcas 로그아웃"""
    with dcas_sessions_lock:
        client = dcas_sessions.pop(session_id, None)
        if client:
            try:
                client.logout()
            except:
                pass
            return {"success": True, "message": "로그아웃 완료"}
    
    return {"success": False, "message": "세션을 찾을 수 없습니다"}


@app.post("/api/dcas/patients", response_model=PatientListResponse)
async def get_patient_list(request: PatientListRequest):
    """
    Dcas에서 환자 리스트를 조회합니다.
    
    - **modality**: 검사 종류 (기본값: XA)
    - **start_date**: 시작일 (YYYY-MM-DD)
    - **end_date**: 종료일 (YYYY-MM-DD)
    """
    try:
        # 세션 없이 직접 DCAS 클라이언트 생성
        client = DcasClient()
        
        patients = client.get_patient_list(
            modality=request.modality,
            start_date=request.start_date,
            end_date=request.end_date,
            patient_id=request.patient_id,
            patient_name=request.patient_name
        )
        
        patient_items = [
            PatientItem(
                cine_no=p.cine_no,
                patient_id=p.patient_id,
                patient_name=p.patient_name,
                gender=p.gender,
                age=p.age,
                study_date=p.study_date
            )
            for p in patients
        ]
        
        return PatientListResponse(
            success=True,
            patients=patient_items,
            total=len(patient_items)
        )
        
    except DcasAuthError as e:
        return PatientListResponse(success=False, error=str(e))
    except DcasConnectionError as e:
        return PatientListResponse(success=False, error=f"서버 연결 실패: {str(e)}")
    except Exception as e:
        return PatientListResponse(success=False, error=f"오류 발생: {str(e)}")


class PreviewRequest(BaseModel):
    cine_no: str
    patient_id: str
    image_index: int = -1  # -1이면 마지막 이미지, 0부터 시작


class PreviewResponse(BaseModel):
    success: bool
    image_url: str = ""
    image_data: str = ""  # base64 encoded
    image_urls: List[str] = []  # 모든 이미지 URL 목록
    current_index: int = 0
    total_images: int = 0
    error: str = ""


@app.post("/api/dcas/preview", response_model=PreviewResponse)
async def get_patient_preview(request: PreviewRequest):
    """
    환자의 리포트 이미지 미리보기를 가져옵니다.
    
    - **cine_no**: 검사 번호
    - **patient_id**: 환자 ID
    - **image_index**: 이미지 인덱스 (-1이면 마지막 이미지)
    """
    import base64
    from io import BytesIO
    from PIL import Image
    import time
    
    start_time = time.time()
    
    try:
        # DCAS 클라이언트 생성
        client = DcasClient()
        
        # 환자 정보 생성
        patient = PatientInfo(cine_no=request.cine_no, patient_id=request.patient_id)
        
        # 검사 정보 조회 (이미지 URL 획득)
        t1 = time.time()
        study_info = client.get_study_info(patient)
        print(f"⏱️ 검사 정보 조회: {time.time() - t1:.2f}초")
        
        if not study_info.image_urls:
            return PreviewResponse(success=False, error="이미지를 찾을 수 없습니다.")
        
        # 이미지 인덱스 결정 (-1이면 마지막)
        image_index = request.image_index
        if image_index < 0:
            image_index = len(study_info.image_urls) - 1
        elif image_index >= len(study_info.image_urls):
            image_index = len(study_info.image_urls) - 1
        
        target_url = study_info.image_urls[image_index]
        
        # 이미지 다운로드
        t2 = time.time()
        response = client.session.get(target_url, timeout=30)
        response.raise_for_status()
        print(f"⏱️ 이미지 다운로드: {time.time() - t2:.2f}초 ({len(response.content)} bytes)")
        
        # 이미지 리사이즈 및 압축 (미리보기 최적화)
        t3 = time.time()
        img = Image.open(BytesIO(response.content))
        
        # RGB 변환
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 리사이즈 (최대 800px)
        max_size = 800
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # JPEG 압축 (품질 70%)
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=70, optimize=True)
        buffer.seek(0)
        
        # base64 인코딩
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        print(f"⏱️ 이미지 최적화: {time.time() - t3:.2f}초 ({len(buffer.getvalue())} bytes)")
        print(f"✅ 총 처리 시간: {time.time() - start_time:.2f}초")
        
        return PreviewResponse(
            success=True,
            image_url=target_url,
            image_data=f"data:image/jpeg;base64,{image_data}",
            image_urls=study_info.image_urls,
            current_index=image_index,
            total_images=len(study_info.image_urls)
        )
        
    except DcasParseError as e:
        return PreviewResponse(success=False, error=str(e))
    except DcasConnectionError as e:
        return PreviewResponse(success=False, error=f"서버 연결 실패: {str(e)}")
    except Exception as e:
        return PreviewResponse(success=False, error=f"오류 발생: {str(e)}")


def run_batch_ocr(
    job_id: str,
    client: DcasClient,
    patients: List[PatientInfo],
    max_workers: int,
    language: str,
    confidence_threshold: float
):
    """백그라운드에서 배치 OCR 실행"""
    try:
        job_manager.update_job(
            job_id,
            status="processing",
            started_at=datetime.now().isoformat()
        )
        
        # 전역 OCR 프로세서 재사용 (중요!)
        ocr_processor = get_ocr_processor(language)
        
        processor = ParallelOCRProcessor(
            dcas_client=client,
            max_workers=max_workers,
            language=language,
            confidence_threshold=confidence_threshold,
            ocr_processor=ocr_processor  # 전역 프로세서 주입
        )
        
        def on_progress(progress):
            job_manager.update_job(
                job_id,
                completed=progress.get("completed", 0),
                current=progress.get("current", "")
            )
        
        processor.set_progress_callback(on_progress)
        
        def on_complete(result):
            job = job_manager.get_job(job_id)
            if job:
                results = job.get("results", [])
                results.append(result.to_dict())
                if result.success:
                    job_manager.update_job(
                        job_id,
                        results=results,
                        success=job.get("success", 0) + 1
                    )
                else:
                    job_manager.update_job(
                        job_id,
                        results=results,
                        failure=job.get("failure", 0) + 1
                    )
        
        batch_result = processor.process_patients(patients, on_complete=on_complete)
        
        job_manager.update_job(
            job_id,
            status="completed",
            finished_at=datetime.now().isoformat(),
            completed=batch_result.total,
            success=batch_result.success_count,
            failure=batch_result.failure_count
        )
        
    except Exception as e:
        job_manager.update_job(
            job_id,
            status="failed",
            finished_at=datetime.now().isoformat(),
            error=str(e)
        )


@app.post("/api/dcas/ocr", response_model=BatchOCRResponse)
async def start_batch_ocr(request: BatchOCRRequest):
    """
    선택한 환자들의 리포트를 병렬로 OCR 처리합니다.
    
    - **patients**: 처리할 환자 리스트
    - **max_workers**: 병렬 처리 워커 수 (기본값: 4)
    - **language**: OCR 언어 (기본값: korean)
    - **confidence_threshold**: 신뢰도 임계값 (기본값: 0.3)
    
    ⚠️ OCR은 별도 스레드에서 실행되므로 다른 API 요청이 블로킹되지 않습니다.
    """
    if not request.patients:
        return BatchOCRResponse(
            success=False,
            error="처리할 환자를 선택해주세요."
        )
    
    # 세션 없이 직접 DCAS 클라이언트 생성
    client = DcasClient()
    
    # 작업 생성
    job_id = str(uuid.uuid4())
    job_manager.create_job(job_id, len(request.patients))
    
    # PatientInfo 객체로 변환
    patients = [
        PatientInfo(
            cine_no=p.cine_no,
            patient_id=p.patient_id,
            patient_name=p.patient_name,
            gender=p.gender,
            age=p.age
        )
        for p in request.patients
    ]
    
    # 별도 스레드에서 OCR 실행 (다른 API 요청 블로킹 방지)
    ocr_thread = threading.Thread(
        target=run_batch_ocr,
        args=(job_id, client, patients, request.max_workers, request.language, request.confidence_threshold),
        daemon=True,  # 메인 프로세스 종료 시 함께 종료
        name=f"OCR-{job_id[:8]}"
    )
    ocr_thread.start()
    
    return BatchOCRResponse(
        success=True,
        job_id=job_id,
        message=f"{len(patients)}명의 환자 OCR 처리를 시작했습니다."
    )


@app.get("/api/dcas/ocr/status/{job_id}", response_model=JobStatusResponse)
async def get_ocr_status(job_id: str):
    """OCR 작업 상태를 조회합니다."""
    job = job_manager.get_job(job_id)
    
    if not job:
        return JobStatusResponse(
            success=False,
            error="작업을 찾을 수 없습니다."
        )
    
    return JobStatusResponse(
        success=True,
        job=job
    )


@app.get("/api/dcas/ocr/jobs")
async def list_ocr_jobs():
    """모든 OCR 작업 목록을 조회합니다."""
    jobs = job_manager.list_jobs()
    return {"success": True, "jobs": jobs}


# ============= 데이터 추출 엔드포인트 =============

import re

def extract_dose_data(ocr_text: str) -> dict:
    """
    OCR 텍스트에서 방사선량 데이터를 추출합니다.
    
    추출 항목:
    - DAP: "39.7 Gy·cm2" -> "39700"
    - AK: "465 mGy" -> "465"
    - Fluoro Time: "0:15:42" -> "0:15:42"
    - RUN: "22 Exposure Series 780 Exposure Images" -> "22/780"
    - ROOM: IRP 15cm 텍스트가 있으면 "2", 없으면 "1"
    """
    result = {
        "dap": "",
        "ak": "",
        "fluoro_time": "",
        "run": "",
        "room": "1"
    }
    
    # DAP 추출 (Total DAP 또는 첫번째 나오는 Gy·cm2 값)
    # 패턴: 숫자.숫자 Gy·cm2 또는 숫자 Gy·cm2 또는 숫자.숫자Gy·cm2
    dap_patterns = [
        r'Total\s*DAP\s*[\n\r]*\s*([\d.]+)\s*Gy[·\.]?cm2?',  # Total DAP 다음 줄
        r'([\d.]+)\s*Gy[·\.]?cm2?\s*[\n\r]*\s*Total\s*DAP',  # Total DAP 앞에
        r'([\d.]+)\s*Gy[·\.]?cm2?'  # 일반적인 패턴
    ]
    
    for pattern in dap_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            dap_value = float(match.group(1))
            # Gy·cm2를 mGy·cm2로 변환 (1000배)
            result["dap"] = str(int(dap_value * 1000))
            break
    
    # Air Kerma (AK) 추출
    ak_patterns = [
        r'([\d.]+)\s*mGy\s*[\n\r]*\s*Total\s*Air\s*Kerma',  # mGy 다음에 Total Air Kerma
        r'Total\s*Air\s*Kerma\s*[\(\[]?K[\)\]]?\*?\s*[\n\r]*\s*([\d.]+)\s*mGy',  # Total Air Kerma 다음
        r'Air\s*Kerma[^\d]*([\d.]+)\s*mGy',  # Air Kerma 근처
        r'([\d.]+)\s*mGy'  # 일반적인 mGy 패턴
    ]
    
    for pattern in ak_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            result["ak"] = match.group(1).split('.')[0]  # 정수만
            break
    
    # Fluoro Time 추출 (시:분:초 형식)
    fluoro_patterns = [
        r'([\d]{1,2}:[\d]{2}:[\d]{2})\s*[\n\r]*\s*Total\s*Fluoroscopy\s*Time',  # 시간 다음에 Total Fluoroscopy Time
        r'Total\s*Fluoroscopy\s*Time\s*[\n\r]*\s*([\d]{1,2}:[\d]{2}:[\d]{2})',  # Total Fluoroscopy Time 다음
        r'Fluoroscopy\s*Time[^\d]*([\d]{1,2}:[\d]{2}:[\d]{2})',  # Fluoroscopy Time 근처
        r'([\d]{1,2}:[\d]{2}:[\d]{2})'  # 일반적인 시간 패턴
    ]
    
    for pattern in fluoro_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            result["fluoro_time"] = match.group(1)
            break
    
    # RUN 추출 (Exposure Series / Exposure Images)
    # 패턴: "22 Exposure Series 780 Exposure Images" -> "22/780"
    exposure_series = None
    exposure_images = None
    
    # Exposure Series 추출
    series_patterns = [
        r'([\d]+)\s*[\n\r]*\s*Exposure\s*Series',  # 숫자 다음에 Exposure Series
        r'Exposure\s*Series\s*[\n\r]*\s*([\d]+)',  # Exposure Series 다음
    ]
    for pattern in series_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            exposure_series = match.group(1)
            break
    
    # Exposure Images 추출
    images_patterns = [
        r'([\d]+)\s*[\n\r]*\s*Exposure\s*Images',  # 숫자 다음에 Exposure Images
        r'Exposure\s*Images\s*[\n\r]*\s*([\d]+)',  # Exposure Images 다음
    ]
    for pattern in images_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            exposure_images = match.group(1)
            break
    
    if exposure_series and exposure_images:
        result["run"] = f"{exposure_series}/{exposure_images}"
    
    # ROOM 결정 (Lateral Cumulative Air Kerma 텍스트 확인)
    # "Lateral Cumulative Air Kerma (K)" 있으면 ROOM = "2", 없으면 ROOM = "1"
    lateral_pattern = r'Lateral\s*Cumulative\s*Air\s*Kerma'
    if re.search(lateral_pattern, ocr_text, re.IGNORECASE):
        result["room"] = "2"
    else:
        result["room"] = "1"
    
    return result


@app.post("/api/extract", response_model=ExtractDataResponse)
async def extract_data(request: ExtractDataRequest):
    """
    OCR 텍스트에서 방사선량 데이터를 추출합니다.
    
    - **ocr_text**: OCR로 추출된 텍스트
    - **date**: 검사 날짜 (수동 입력)
    - **registration_no**: 등록번호 (수동 입력)
    - **gender**: 성별 (수동 입력)
    """
    try:
        extracted = extract_dose_data(request.ocr_text)
        
        data = ExtractedData(
            date=request.date,
            registration_no=request.registration_no,
            gender=request.gender,
            dap=extracted["dap"],
            ak=extracted["ak"],
            fluoro_time=extracted["fluoro_time"],
            col1="0",
            col2="0",
            col3="0",
            run=extracted["run"],
            room=extracted["room"]
        )
        
        return ExtractDataResponse(success=True, data=data)
        
    except Exception as e:
        return ExtractDataResponse(success=False, error=f"데이터 추출 오류: {str(e)}")


@app.post("/api/extract/batch")
async def extract_batch_data(results: List[Dict[str, Any]]):
    """
    여러 OCR 결과에서 데이터를 일괄 추출합니다.
    
    - **results**: OCR 결과 배열 (patient_id, patient_name, text 포함)
    """
    try:
        extracted_list = []
        
        for result in results:
            ocr_text = result.get("text", "")
            extracted = extract_dose_data(ocr_text)
            
            extracted_list.append({
                "patient_id": result.get("patient_id", ""),
                "patient_name": result.get("patient_name", ""),
                "date": result.get("date", ""),
                "gender": result.get("gender", ""),
                **extracted
            })
        
        return {"success": True, "data": extracted_list}
        
    except Exception as e:
        return {"success": False, "error": f"일괄 추출 오류: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
