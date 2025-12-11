"""
ocr_processor.py - PaddleOCR 기반 텍스트 검출 및 인식 모듈

이 모듈은 다음 기능을 제공합니다:
- PaddleOCR 엔진 초기화 및 관리
- 이미지에서 텍스트 검출 및 인식
- 신뢰도 기반 필터링
- 다중 페이지 PDF 처리
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union
from pathlib import Path

import numpy as np

from utils import (
    validate_file,
    is_pdf_file,
    load_image,
    convert_pdf_to_images,
    preprocess_image,
    parse_lines,
    format_output,
    FileValidationError,
    ImageProcessingError,
    PDFProcessingError
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OCRError(Exception):
    """OCR 처리 오류 예외"""
    pass


class OCRInitError(Exception):
    """OCR 엔진 초기화 오류 예외"""
    pass


@dataclass
class OCRResult:
    """OCR 결과 데이터 클래스"""
    text: str
    confidence: float
    bbox: Optional[List[List[float]]] = None  # 바운딩 박스 좌표


@dataclass
class PageResult:
    """페이지별 OCR 결과"""
    page_number: int
    results: List[OCRResult]
    raw_text: str
    
    def get_text_with_confidence(self, threshold: float = 0.0) -> str:
        """지정된 신뢰도 이상의 텍스트만 반환"""
        filtered = [r for r in self.results if r.confidence >= threshold]
        return "\n".join([r.text for r in filtered])


class OCRProcessor:
    """
    PaddleOCR 기반 텍스트 인식 프로세서
    
    Attributes:
        lang: 인식 언어 (기본값: 'korean')
        use_angle_cls: 텍스트 방향 분류 사용 여부
        det: 텍스트 검출 사용 여부
        rec: 텍스트 인식 사용 여부
        confidence_threshold: 최소 신뢰도 임계값
    """
    
    # 지원하는 언어 목록
    SUPPORTED_LANGUAGES = {
        'korean': '한국어',
        'en': '영어',
        'ch': '중국어(간체)',
        'chinese_cht': '중국어(번체)',
        'japan': '일본어',
        'french': '프랑스어',
        'german': '독일어',
        'arabic': '아랍어',
        'cyrillic': '러시아어/키릴 문자',
    }
    
    def __init__(
        self,
        lang: str = 'korean',
        use_angle_cls: bool = True,
        det: bool = True,
        rec: bool = True,
        confidence_threshold: float = 0.3
    ):
        """
        OCR 프로세서를 초기화합니다.
        
        Args:
            lang: 인식 언어 (기본값: 'korean')
            use_angle_cls: 텍스트 방향 분류 사용 여부 (180도 회전 텍스트 인식)
            det: 텍스트 검출 사용 여부
            rec: 텍스트 인식 사용 여부
            confidence_threshold: 최소 신뢰도 임계값 (0.0 ~ 1.0)
        """
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self.det = det
        self.rec = rec
        self.confidence_threshold = confidence_threshold
        
        self._ocr = None
        self._initialized = False
    
    def _initialize_ocr(self):
        """PaddleOCR 엔진을 지연 초기화합니다."""
        if self._initialized:
            return
        
        try:
            from paddleocr import PaddleOCR
            
            logger.info(f"PaddleOCR 초기화 중... (언어: {self.lang})")
            
            self._ocr = PaddleOCR(
                use_angle_cls=self.use_angle_cls,
                lang=self.lang
            )
            
            self._initialized = True
            logger.info("PaddleOCR 초기화 완료")
            
        except ImportError:
            raise OCRInitError(
                "PaddleOCR가 설치되지 않았습니다.\n"
                "'pip install paddleocr paddlepaddle' 명령으로 설치해주세요."
            )
        except Exception as e:
            raise OCRInitError(f"PaddleOCR 초기화 실패: {str(e)}")
    
    def _extract_results_v2(self, ocr_output) -> List[OCRResult]:
        """
        ocr() 메서드 출력을 OCRResult 리스트로 변환합니다.
        
        ocr() 메서드는 [[[bbox, (text, confidence)], ...]] 형식 반환
        """
        results = []
        
        if not ocr_output:
            return results
        
        try:
            # ocr() 반환 형식: [page_result, ...] 
            # 각 page_result: [[bbox, (text, conf)], ...]
            for page_result in ocr_output:
                if not page_result:
                    continue
                    
                for line in page_result:
                    if not line or len(line) < 2:
                        continue
                    
                    bbox = line[0]
                    text_info = line[1]
                    
                    if isinstance(text_info, (tuple, list)) and len(text_info) >= 2:
                        text = str(text_info[0])
                        confidence = float(text_info[1])
                        
                        if text.strip():
                            results.append(OCRResult(
                                text=text,
                                confidence=confidence,
                                bbox=bbox
                            ))
        except Exception as e:
            logger.warning(f"결과 추출 v2 오류: {e}")
        
        return results
    
    def _extract_results(self, ocr_output) -> List[OCRResult]:
        """
        PaddleOCR 출력을 OCRResult 리스트로 변환합니다.
        
        Args:
            ocr_output: PaddleOCR.predict() 반환값
            
        Returns:
            List[OCRResult]: 변환된 결과 리스트
        """
        results = []
        
        if not ocr_output:
            return results
        
        try:
            # PaddleOCR 2.9+ 새로운 형식 처리
            # predict()는 딕셔너리 또는 리스트를 반환할 수 있음
            if isinstance(ocr_output, dict):
                # 딕셔너리 형식인 경우
                rec_texts = ocr_output.get('rec_texts', ocr_output.get('rec_text', []))
                rec_scores = ocr_output.get('rec_scores', ocr_output.get('rec_score', []))
                dt_polys = ocr_output.get('dt_polys', ocr_output.get('dt_poly', []))
                
                if isinstance(rec_texts, list):
                    for i, text in enumerate(rec_texts):
                        confidence = rec_scores[i] if i < len(rec_scores) else 1.0
                        bbox = dt_polys[i] if i < len(dt_polys) else None
                        
                        if text:
                            results.append(OCRResult(
                                text=str(text),
                                confidence=float(confidence),
                                bbox=bbox
                            ))
            elif isinstance(ocr_output, list):
                # 리스트 형식 - 여러 가지 가능한 형식 처리
                for item in ocr_output:
                    if item is None:
                        continue
                    
                    # 딕셔너리 아이템인 경우
                    if isinstance(item, dict):
                        rec_texts = item.get('rec_texts', item.get('rec_text', []))
                        rec_scores = item.get('rec_scores', item.get('rec_score', []))
                        dt_polys = item.get('dt_polys', item.get('dt_poly', []))
                        
                        if isinstance(rec_texts, str):
                            rec_texts = [rec_texts]
                            rec_scores = [rec_scores] if not isinstance(rec_scores, list) else rec_scores
                        
                        for i, text in enumerate(rec_texts):
                            confidence = rec_scores[i] if i < len(rec_scores) else 1.0
                            bbox = dt_polys[i] if i < len(dt_polys) else None
                            
                            if text:
                                results.append(OCRResult(
                                    text=str(text),
                                    confidence=float(confidence) if confidence else 1.0,
                                    bbox=bbox
                                ))
                    # 기존 형식 (리스트 of 리스트)
                    elif isinstance(item, list):
                        for line in item:
                            if not line or len(line) < 2:
                                continue
                            
                            bbox = line[0]
                            text_info = line[1]
                            
                            if isinstance(text_info, tuple) and len(text_info) >= 2:
                                text = str(text_info[0])
                                confidence = float(text_info[1])
                                
                                results.append(OCRResult(
                                    text=text,
                                    confidence=confidence,
                                    bbox=bbox
                                ))
        except Exception as e:
            logger.warning(f"결과 추출 중 오류: {e}, 원본 출력 타입: {type(ocr_output)}")
            # 디버깅을 위해 원본 출력 로깅
            logger.debug(f"OCR 원본 출력: {ocr_output}")
        
        return results
    
    def process_image(
        self,
        image: Union[str, np.ndarray],
        confidence_threshold: Optional[float] = None,
        preprocess: bool = False
    ) -> List[OCRResult]:
        """
        단일 이미지에서 텍스트를 인식합니다.
        
        Args:
            image: 이미지 파일 경로 또는 numpy 배열
            confidence_threshold: 신뢰도 임계값 (None이면 인스턴스 기본값 사용)
            preprocess: 이미지 전처리 적용 여부
            
        Returns:
            List[OCRResult]: OCR 결과 리스트
            
        Raises:
            OCRError: OCR 처리 실패 시
        """
        # OCR 엔진 초기화
        self._initialize_ocr()
        
        threshold = confidence_threshold if confidence_threshold is not None else self.confidence_threshold
        
        try:
            # 파일 경로인 경우 직접 전달 (더 안정적)
            if isinstance(image, str):
                # 파일 경로를 직접 PaddleOCR에 전달
                ocr_output = self._ocr.predict(image)
            else:
                # numpy 배열인 경우
                img_array = image
                if preprocess:
                    img_array = preprocess_image(img_array)
                ocr_output = self._ocr.predict(img_array)
            
            # 결과 추출
            results = self._extract_results(ocr_output)
            
            # 신뢰도 필터링
            filtered_results = [r for r in results if r.confidence >= threshold]
            
            logger.info(f"인식 완료: 전체 {len(results)}개, 필터링 후 {len(filtered_results)}개")
            
            return filtered_results
            
        except ImageProcessingError as e:
            raise OCRError(f"이미지 처리 오류: {str(e)}")
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"OCR 처리 상세 오류:\n{error_detail}")
            raise OCRError(f"OCR 처리 중 오류 발생: {str(e)}")
    
    def process_file(
        self,
        file_path: str,
        confidence_threshold: Optional[float] = None,
        preprocess: bool = False,
        pdf_dpi: int = 200
    ) -> List[PageResult]:
        """
        파일(이미지 또는 PDF)에서 텍스트를 인식합니다.
        
        Args:
            file_path: 파일 경로
            confidence_threshold: 신뢰도 임계값
            preprocess: 이미지 전처리 적용 여부
            pdf_dpi: PDF 변환 해상도
            
        Returns:
            List[PageResult]: 페이지별 OCR 결과 리스트
            
        Raises:
            FileValidationError: 파일 유효성 검사 실패 시
            OCRError: OCR 처리 실패 시
        """
        # 파일 유효성 검사
        is_valid, message = validate_file(file_path)
        if not is_valid:
            raise FileValidationError(message)
        
        page_results = []
        
        try:
            if is_pdf_file(file_path):
                # PDF 처리
                logger.info(f"PDF 파일 처리 중: {file_path}")
                images = convert_pdf_to_images(file_path, dpi=pdf_dpi)
                
                for page_num, img in enumerate(images, start=1):
                    logger.info(f"페이지 {page_num}/{len(images)} 처리 중...")
                    
                    results = self.process_image(
                        img,
                        confidence_threshold=confidence_threshold,
                        preprocess=preprocess
                    )
                    
                    raw_text = "\n".join([r.text for r in results])
                    
                    page_results.append(PageResult(
                        page_number=page_num,
                        results=results,
                        raw_text=raw_text
                    ))
            else:
                # 이미지 처리
                logger.info(f"이미지 파일 처리 중: {file_path}")
                
                results = self.process_image(
                    file_path,
                    confidence_threshold=confidence_threshold,
                    preprocess=preprocess
                )
                
                raw_text = "\n".join([r.text for r in results])
                
                page_results.append(PageResult(
                    page_number=1,
                    results=results,
                    raw_text=raw_text
                ))
            
            return page_results
            
        except PDFProcessingError as e:
            raise OCRError(f"PDF 처리 오류: {str(e)}")
        except Exception as e:
            raise OCRError(f"파일 처리 중 오류 발생: {str(e)}")
    
    def get_text(
        self,
        file_path: str,
        confidence_threshold: Optional[float] = None,
        include_confidence: bool = False,
        page_separator: str = "\n\n--- 페이지 {page} ---\n\n"
    ) -> str:
        """
        파일에서 텍스트를 추출하여 문자열로 반환합니다.
        
        Args:
            file_path: 파일 경로
            confidence_threshold: 신뢰도 임계값
            include_confidence: 결과에 신뢰도 포함 여부
            page_separator: 페이지 구분자 (PDF의 경우)
            
        Returns:
            str: 추출된 텍스트
        """
        page_results = self.process_file(file_path, confidence_threshold)
        
        if len(page_results) == 1:
            # 단일 페이지
            results = page_results[0].results
            lines = []
            for r in results:
                if include_confidence:
                    lines.append(f"{r.text} (신뢰도: {r.confidence:.2%})")
                else:
                    lines.append(r.text)
            return "\n".join(lines)
        else:
            # 다중 페이지 (PDF)
            all_text = []
            for page_result in page_results:
                if page_separator:
                    all_text.append(page_separator.format(page=page_result.page_number))
                
                for r in page_result.results:
                    if include_confidence:
                        all_text.append(f"{r.text} (신뢰도: {r.confidence:.2%})")
                    else:
                        all_text.append(r.text)
            
            return "\n".join(all_text)
    
    def get_results_with_bbox(
        self,
        file_path: str,
        confidence_threshold: Optional[float] = None
    ) -> List[dict]:
        """
        바운딩 박스 좌표를 포함한 상세 결과를 반환합니다.
        
        Args:
            file_path: 파일 경로
            confidence_threshold: 신뢰도 임계값
            
        Returns:
            List[dict]: 상세 OCR 결과 리스트
        """
        page_results = self.process_file(file_path, confidence_threshold)
        
        detailed_results = []
        for page_result in page_results:
            for r in page_result.results:
                detailed_results.append({
                    "page": page_result.page_number,
                    "text": r.text,
                    "confidence": r.confidence,
                    "bbox": r.bbox
                })
        
        return detailed_results
    
    @classmethod
    def get_supported_languages(cls) -> dict:
        """지원하는 언어 목록을 반환합니다."""
        return cls.SUPPORTED_LANGUAGES.copy()
    
    def set_language(self, lang: str):
        """
        인식 언어를 변경합니다. (엔진 재초기화 필요)
        
        Args:
            lang: 새 언어 코드
        """
        if lang != self.lang:
            self.lang = lang
            self._initialized = False
            self._ocr = None
            logger.info(f"언어 변경됨: {lang}")
    
    def set_confidence_threshold(self, threshold: float):
        """
        기본 신뢰도 임계값을 변경합니다.
        
        Args:
            threshold: 새 임계값 (0.0 ~ 1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self.confidence_threshold = threshold
            logger.info(f"신뢰도 임계값 변경됨: {threshold}")
        else:
            raise ValueError("임계값은 0.0에서 1.0 사이여야 합니다.")


# 편의를 위한 싱글톤 인스턴스
_default_processor: Optional[OCRProcessor] = None


def get_default_processor() -> OCRProcessor:
    """기본 OCR 프로세서 인스턴스를 반환합니다."""
    global _default_processor
    if _default_processor is None:
        _default_processor = OCRProcessor()
    return _default_processor


def quick_ocr(file_path: str, lang: str = 'korean') -> str:
    """
    빠른 OCR 수행을 위한 편의 함수
    
    Args:
        file_path: 파일 경로
        lang: 언어 코드
        
    Returns:
        str: 추출된 텍스트
    """
    processor = OCRProcessor(lang=lang)
    return processor.get_text(file_path)

