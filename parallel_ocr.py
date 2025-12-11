"""
parallel_ocr.py - 병렬 OCR 처리 모듈

여러 환자의 이미지를 병렬로 OCR 처리하는 기능을 제공합니다.
ThreadPoolExecutor를 사용하여 효율적인 병렬 처리를 수행합니다.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import threading

from dcas_client import DcasClient, PatientInfo, StudyInfo, DcasConnectionError
from ocr_processor import OCRProcessor, OCRError

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class OCRTaskResult:
    """단일 OCR 작업 결과"""
    patient: PatientInfo
    success: bool
    text: str = ""
    lines: List[Dict[str, Any]] = field(default_factory=list)
    image_url: str = ""
    error: str = ""
    processing_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "patient_id": self.patient.patient_id,
            "patient_name": self.patient.patient_name,
            "cine_no": self.patient.cine_no,
            "success": self.success,
            "text": self.text,
            "lines": self.lines,
            "image_url": self.image_url,
            "error": self.error,
            "processing_time": self.processing_time
        }


@dataclass
class BatchOCRResult:
    """배치 OCR 결과"""
    total: int
    success_count: int
    failure_count: int
    results: List[OCRTaskResult]
    start_time: datetime
    end_time: Optional[datetime] = None
    
    @property
    def elapsed_seconds(self) -> float:
        """총 처리 시간 (초)"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "total": self.total,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "elapsed_seconds": self.elapsed_seconds,
            "results": [r.to_dict() for r in self.results]
        }


class ParallelOCRProcessor:
    """
    병렬 OCR 처리기
    
    여러 환자의 검사 이미지를 동시에 OCR 처리합니다.
    """
    
    def __init__(
        self,
        dcas_client: DcasClient,
        max_workers: int = 4,  # 이미지 다운로드용 병렬 워커 (OCR은 순차)
        language: str = "korean",
        confidence_threshold: float = 0.3,
        ocr_processor: Optional[OCRProcessor] = None  # 외부에서 주입 가능
    ):
        """
        병렬 OCR 처리기 초기화
        
        Args:
            dcas_client: Dcas 클라이언트
            max_workers: 이미지 다운로드용 병렬 워커 수
            language: OCR 언어
            confidence_threshold: 신뢰도 임계값
            ocr_processor: 외부에서 주입할 OCR 프로세서 (None이면 내부 생성)
        """
        self.dcas_client = dcas_client
        self.max_workers = max_workers
        self.language = language
        self.confidence_threshold = confidence_threshold
        
        # OCR 프로세서 (외부 주입 또는 내부 생성)
        self._ocr_processor: Optional[OCRProcessor] = ocr_processor
        self._ocr_lock = threading.Lock()
        
        # 진행 상황 추적
        self._progress: Dict[str, Any] = {
            "total": 0,
            "completed": 0,
            "current": "",
            "status": "idle"
        }
        self._progress_lock = threading.Lock()
        self._progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    
    @property
    def ocr_processor(self) -> OCRProcessor:
        """OCR 프로세서 인스턴스 (외부 주입 또는 지연 초기화)"""
        if self._ocr_processor is None:
            logger.warning("⚠️ OCR 프로세서가 주입되지 않아 새로 생성합니다.")
            self._ocr_processor = OCRProcessor(
                lang=self.language,
                confidence_threshold=self.confidence_threshold
            )
        return self._ocr_processor
    
    def set_progress_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """진행 상황 콜백 설정"""
        self._progress_callback = callback
    
    def get_progress(self) -> Dict[str, Any]:
        """현재 진행 상황 반환"""
        with self._progress_lock:
            return self._progress.copy()
    
    def _update_progress(self, **kwargs):
        """진행 상황 업데이트"""
        with self._progress_lock:
            self._progress.update(kwargs)
            progress = self._progress.copy()
        
        if self._progress_callback:
            try:
                self._progress_callback(progress)
            except Exception as e:
                logger.warning(f"진행 상황 콜백 오류: {e}")
    
    def _download_image(self, patient: PatientInfo) -> Dict[str, Any]:
        """
        단일 환자의 리포트 이미지를 다운로드합니다. (병렬 처리 가능)
        
        Args:
            patient: 환자 정보
            
        Returns:
            Dict: 다운로드 결과 (temp_file, report_url, error 등)
        """
        import tempfile
        import os
        from PIL import Image
        from io import BytesIO
        
        try:
            # 검사 정보 조회
            study_info = self.dcas_client.get_study_info(patient)
            report_url = study_info.get_last_image_url()
            
            if not report_url:
                return {
                    "patient": patient,
                    "success": False,
                    "error": "리포트 이미지를 찾을 수 없습니다."
                }
            
            # 이미지 다운로드
            print(f"📥 이미지 다운로드: {report_url}")
            response = self.dcas_client.session.get(report_url, timeout=30)
            response.raise_for_status()
            
            # PIL로 이미지 로드 후 RGB 변환하여 저장
            image = Image.open(BytesIO(response.content))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 임시 파일로 저장
            temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            image.save(temp_file.name, 'JPEG', quality=95)
            temp_file.close()
            print(f"   ✅ 임시 파일 저장: {temp_file.name}")
            
            return {
                "patient": patient,
                "success": True,
                "temp_file": temp_file.name,
                "report_url": report_url
            }
            
        except DcasConnectionError as e:
            logger.error(f"Dcas 연결 오류 ({patient.patient_id}): {e}")
            return {
                "patient": patient,
                "success": False,
                "error": f"Dcas 연결 오류: {str(e)}"
            }
        except Exception as e:
            logger.error(f"다운로드 오류 ({patient.patient_id}): {e}")
            return {
                "patient": patient,
                "success": False,
                "error": f"다운로드 오류: {str(e)}"
            }
    
    def _perform_ocr(self, download_result: Dict[str, Any]) -> OCRTaskResult:
        """
        다운로드된 이미지에 OCR을 수행합니다. (순차 처리)
        
        Args:
            download_result: 다운로드 결과
            
        Returns:
            OCRTaskResult: OCR 결과
        """
        import os
        
        patient = download_result["patient"]
        start_time = datetime.now()
        temp_file = download_result.get("temp_file")
        
        try:
            # 다운로드 실패 시
            if not download_result["success"]:
                return OCRTaskResult(
                    patient=patient,
                    success=False,
                    error=download_result.get("error", "다운로드 실패")
                )
            
            self._update_progress(current=f"{patient.patient_id} - OCR 처리 중")
            
            # OCR 처리 (순차적으로 - 락 없이)
            page_results = self.ocr_processor.process_file(
                temp_file,
                confidence_threshold=self.confidence_threshold
            )
            
            # 결과 변환
            results = page_results[0].results if page_results else []
            lines = [
                {"text": r.text, "confidence": round(r.confidence, 4)}
                for r in results
            ]
            text = "\n".join([r.text for r in results])
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"OCR 완료: {patient.patient_id} - {len(results)}줄, {processing_time:.2f}초")
            
            return OCRTaskResult(
                patient=patient,
                success=True,
                text=text,
                lines=lines,
                image_url=download_result.get("report_url", ""),
                processing_time=processing_time
            )
            
        except OCRError as e:
            logger.error(f"OCR 오류 ({patient.patient_id}): {e}")
            return OCRTaskResult(
                patient=patient,
                success=False,
                error=f"OCR 오류: {str(e)}",
                processing_time=(datetime.now() - start_time).total_seconds()
            )
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"\n❌ OCR 오류 ({patient.patient_id}): {e}")
            print(f"📋 스택 트레이스:\n{error_trace}")
            return OCRTaskResult(
                patient=patient,
                success=False,
                error=f"OCR 오류: {str(e)}",
                processing_time=(datetime.now() - start_time).total_seconds()
            )
        finally:
            # 임시 파일 정리
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass
    
    def process_patients(
        self,
        patients: List[PatientInfo],
        on_complete: Optional[Callable[[OCRTaskResult], None]] = None
    ) -> BatchOCRResult:
        """
        여러 환자의 리포트를 처리합니다.
        - 이미지 다운로드: 병렬 (빠른 네트워크 I/O)
        - OCR 처리: 순차 (PaddleOCR 충돌 방지)
        
        Args:
            patients: 환자 리스트
            on_complete: 각 환자 처리 완료 시 호출되는 콜백
            
        Returns:
            BatchOCRResult: 배치 처리 결과
        """
        if not patients:
            return BatchOCRResult(
                total=0,
                success_count=0,
                failure_count=0,
                results=[],
                start_time=datetime.now(),
                end_time=datetime.now()
            )
        
        self._update_progress(
            total=len(patients),
            completed=0,
            current="이미지 다운로드 중...",
            status="processing"
        )
        
        start_time = datetime.now()
        results: List[OCRTaskResult] = []
        success_count = 0
        failure_count = 0
        
        logger.info(f"처리 시작: {len(patients)}명 (다운로드: 병렬 {self.max_workers}개, OCR: 순차)")
        
        # 1단계: 이미지 다운로드 (병렬)
        download_results: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_patient = {
                executor.submit(self._download_image, patient): patient
                for patient in patients
            }
            
            for future in as_completed(future_to_patient):
                download_result = future.result()
                download_results.append(download_result)
                self._update_progress(
                    current=f"다운로드 완료: {len(download_results)}/{len(patients)}"
                )
        
        logger.info(f"이미지 다운로드 완료: {len(download_results)}개")
        
        # 2단계: OCR 처리 (순차)
        self._update_progress(current="OCR 처리 중...")
        
        for i, download_result in enumerate(download_results):
            result = self._perform_ocr(download_result)
            results.append(result)
            
            if result.success:
                success_count += 1
            else:
                failure_count += 1
            
            self._update_progress(
                completed=i + 1,
                current=f"OCR 완료: {result.patient.patient_id}"
            )
            
            if on_complete:
                try:
                    on_complete(result)
                except Exception as e:
                    logger.warning(f"완료 콜백 오류: {e}")
        
        end_time = datetime.now()
        
        self._update_progress(
            status="completed",
            current=""
        )
        
        batch_result = BatchOCRResult(
            total=len(patients),
            success_count=success_count,
            failure_count=failure_count,
            results=results,
            start_time=start_time,
            end_time=end_time
        )
        
        logger.info(
            f"처리 완료: 성공 {success_count}/{len(patients)}, "
            f"소요시간 {batch_result.elapsed_seconds:.2f}초"
        )
        
        return batch_result
    
    def process_by_cine_nos(
        self,
        cine_nos: List[str],
        patient_ids: List[str]
    ) -> BatchOCRResult:
        """
        cine_no와 patient_id 리스트로 OCR 처리합니다.
        
        Args:
            cine_nos: cine_no 리스트
            patient_ids: patient_id 리스트
            
        Returns:
            BatchOCRResult: 배치 처리 결과
        """
        if len(cine_nos) != len(patient_ids):
            raise ValueError("cine_nos와 patient_ids의 길이가 일치해야 합니다.")
        
        patients = [
            PatientInfo(cine_no=cine_no, patient_id=patient_id)
            for cine_no, patient_id in zip(cine_nos, patient_ids)
        ]
        
        return self.process_patients(patients)


class OCRJobManager:
    """
    OCR 작업 관리자
    
    비동기 OCR 작업을 관리하고 상태를 추적합니다.
    """
    
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def create_job(self, job_id: str, total: int) -> Dict[str, Any]:
        """새 작업 생성"""
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "status": "pending",
                "total": total,
                "completed": 0,
                "success": 0,
                "failure": 0,
                "current": "",
                "results": [],
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "finished_at": None
            }
            return self._jobs[job_id].copy()
    
    def update_job(self, job_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """작업 상태 업데이트"""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(kwargs)
                return self._jobs[job_id].copy()
        return None
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """작업 상태 조회"""
        with self._lock:
            if job_id in self._jobs:
                return self._jobs[job_id].copy()
        return None
    
    def delete_job(self, job_id: str) -> bool:
        """작업 삭제"""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                return True
        return False
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """모든 작업 목록"""
        with self._lock:
            return [job.copy() for job in self._jobs.values()]


# 전역 작업 관리자
job_manager = OCRJobManager()

