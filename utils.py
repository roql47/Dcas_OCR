"""
utils.py - 파일 처리 및 텍스트 정제 유틸리티 모듈

이 모듈은 다음 기능을 제공합니다:
- 파일 유효성 검사
- 이미지 전처리
- PDF -> 이미지 변환
- 텍스트 정제 및 파싱
"""

import os
import re
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image


# 지원하는 파일 확장자
SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'}
SUPPORTED_PDF_EXTENSION = '.pdf'
ALL_SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | {SUPPORTED_PDF_EXTENSION}


class FileValidationError(Exception):
    """파일 유효성 검사 실패 예외"""
    pass


class ImageProcessingError(Exception):
    """이미지 처리 실패 예외"""
    pass


class PDFProcessingError(Exception):
    """PDF 처리 실패 예외"""
    pass


def validate_file(file_path: str) -> Tuple[bool, str]:
    """
    파일 유효성을 검사합니다.
    
    Args:
        file_path: 검사할 파일 경로
        
    Returns:
        Tuple[bool, str]: (유효 여부, 메시지)
    """
    if not file_path:
        return False, "파일 경로가 비어있습니다."
    
    path = Path(file_path)
    
    # 파일 존재 여부 확인
    if not path.exists():
        return False, f"파일을 찾을 수 없습니다: {file_path}"
    
    # 파일 여부 확인 (디렉토리가 아닌지)
    if not path.is_file():
        return False, f"유효한 파일이 아닙니다: {file_path}"
    
    # 확장자 확인
    ext = path.suffix.lower()
    if ext not in ALL_SUPPORTED_EXTENSIONS:
        supported = ', '.join(sorted(ALL_SUPPORTED_EXTENSIONS))
        return False, f"지원하지 않는 파일 형식입니다: {ext}\n지원 형식: {supported}"
    
    # 파일 크기 확인 (0바이트 파일 체크)
    if path.stat().st_size == 0:
        return False, "파일이 비어있습니다."
    
    return True, "유효한 파일입니다."


def is_pdf_file(file_path: str) -> bool:
    """PDF 파일 여부를 확인합니다."""
    return Path(file_path).suffix.lower() == SUPPORTED_PDF_EXTENSION


def is_image_file(file_path: str) -> bool:
    """이미지 파일 여부를 확인합니다."""
    return Path(file_path).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def load_image(file_path: str) -> np.ndarray:
    """
    이미지 파일을 로드합니다.
    
    Args:
        file_path: 이미지 파일 경로
        
    Returns:
        np.ndarray: RGB 형식의 이미지 배열
        
    Raises:
        ImageProcessingError: 이미지 로드 실패 시
    """
    try:
        # PIL로 먼저 시도 (더 넓은 포맷 지원)
        pil_image = Image.open(file_path)
        
        # RGBA -> RGB 변환 (필요한 경우)
        if pil_image.mode == 'RGBA':
            # 흰색 배경으로 알파 채널 합성
            background = Image.new('RGB', pil_image.size, (255, 255, 255))
            background.paste(pil_image, mask=pil_image.split()[3])
            pil_image = background
        elif pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # numpy 배열로 변환
        image_array = np.array(pil_image)
        
        return image_array
        
    except Exception as e:
        # OpenCV로 재시도
        try:
            image = cv2.imread(file_path)
            if image is None:
                raise ImageProcessingError(f"이미지를 읽을 수 없습니다: {file_path}")
            # BGR -> RGB 변환
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            return image
        except Exception as cv_e:
            raise ImageProcessingError(f"이미지 로드 실패: {str(e)}, OpenCV 시도: {str(cv_e)}")


def convert_pdf_to_images(pdf_path: str, dpi: int = 200) -> List[np.ndarray]:
    """
    PDF 파일을 이미지 리스트로 변환합니다.
    
    Args:
        pdf_path: PDF 파일 경로
        dpi: 변환 해상도 (기본값: 200)
        
    Returns:
        List[np.ndarray]: RGB 형식의 이미지 배열 리스트
        
    Raises:
        PDFProcessingError: PDF 변환 실패 시
    """
    try:
        from pdf2image import convert_from_path
        from pdf2image.exceptions import PDFPageCountError, PDFSyntaxError
    except ImportError:
        raise PDFProcessingError(
            "pdf2image 라이브러리가 설치되지 않았습니다.\n"
            "'pip install pdf2image' 명령으로 설치해주세요.\n"
            "또한 poppler가 시스템에 설치되어 있어야 합니다."
        )
    
    try:
        # PDF를 이미지로 변환
        pil_images = convert_from_path(pdf_path, dpi=dpi)
        
        if not pil_images:
            raise PDFProcessingError("PDF에서 이미지를 추출할 수 없습니다.")
        
        # numpy 배열로 변환
        images = []
        for pil_image in pil_images:
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            images.append(np.array(pil_image))
        
        return images
        
    except PDFPageCountError:
        raise PDFProcessingError("PDF 페이지 수를 확인할 수 없습니다. 파일이 손상되었을 수 있습니다.")
    except PDFSyntaxError:
        raise PDFProcessingError("PDF 구문 오류가 있습니다. 파일이 손상되었거나 암호화되어 있을 수 있습니다.")
    except Exception as e:
        if "poppler" in str(e).lower():
            raise PDFProcessingError(
                "Poppler가 설치되지 않았거나 PATH에 추가되지 않았습니다.\n"
                "Windows: https://github.com/oschwartz10612/poppler-windows/releases 에서 다운로드 후 PATH에 추가\n"
                "설치 후 프로그램을 재시작해주세요."
            )
        raise PDFProcessingError(f"PDF 변환 중 오류 발생: {str(e)}")


def preprocess_image(image: np.ndarray, enhance: bool = True) -> np.ndarray:
    """
    OCR 성능 향상을 위한 이미지 전처리를 수행합니다.
    
    Args:
        image: 입력 이미지 (RGB 형식)
        enhance: 이미지 향상 적용 여부
        
    Returns:
        np.ndarray: 전처리된 이미지
    """
    if not enhance:
        return image
    
    try:
        # RGB -> BGR (OpenCV 처리용)
        img = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        # 노이즈 제거 (가벼운 블러)
        img = cv2.GaussianBlur(img, (3, 3), 0)
        
        # 대비 향상 (CLAHE)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # BGR -> RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        return img
        
    except Exception:
        # 전처리 실패 시 원본 반환
        return image


def clean_text(text: str) -> str:
    """
    인식된 텍스트를 정제합니다.
    
    Args:
        text: 원본 텍스트
        
    Returns:
        str: 정제된 텍스트
    """
    if not text:
        return ""
    
    # 앞뒤 공백 제거
    text = text.strip()
    
    # 연속된 공백을 단일 공백으로
    text = re.sub(r'\s+', ' ', text)
    
    # 불필요한 특수문자 정제 (필요에 따라 조정)
    # 여기서는 기본적인 정제만 수행
    
    return text


def parse_lines(results: List[Tuple[str, float]], 
                confidence_threshold: float = 0.3,
                clean: bool = True) -> List[dict]:
    """
    OCR 결과를 줄 단위로 파싱합니다.
    
    Args:
        results: OCR 결과 리스트 [(텍스트, 신뢰도), ...]
        confidence_threshold: 최소 신뢰도 임계값
        clean: 텍스트 정제 적용 여부
        
    Returns:
        List[dict]: 파싱된 결과 [{"text": str, "confidence": float}, ...]
    """
    parsed = []
    
    for text, confidence in results:
        # 신뢰도 필터링
        if confidence < confidence_threshold:
            continue
        
        # 텍스트 정제
        if clean:
            text = clean_text(text)
        
        # 빈 텍스트 제외
        if not text:
            continue
        
        parsed.append({
            "text": text,
            "confidence": round(confidence, 4)
        })
    
    return parsed


def format_output(parsed_results: List[dict], 
                  include_confidence: bool = False,
                  separator: str = "\n") -> str:
    """
    파싱된 결과를 문자열로 포맷팅합니다.
    
    Args:
        parsed_results: 파싱된 OCR 결과
        include_confidence: 신뢰도 포함 여부
        separator: 줄 구분자
        
    Returns:
        str: 포맷팅된 텍스트
    """
    lines = []
    
    for item in parsed_results:
        if include_confidence:
            lines.append(f"{item['text']} (신뢰도: {item['confidence']:.2%})")
        else:
            lines.append(item['text'])
    
    return separator.join(lines)


def get_file_info(file_path: str) -> dict:
    """
    파일 정보를 반환합니다.
    
    Args:
        file_path: 파일 경로
        
    Returns:
        dict: 파일 정보
    """
    path = Path(file_path)
    stat = path.stat()
    
    return {
        "name": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "size_readable": format_file_size(stat.st_size),
        "is_pdf": is_pdf_file(file_path),
        "is_image": is_image_file(file_path)
    }


def format_file_size(size_bytes: int) -> str:
    """파일 크기를 읽기 쉬운 형식으로 변환합니다."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def save_text_to_file(text: str, output_path: str, encoding: str = 'utf-8') -> bool:
    """
    텍스트를 파일로 저장합니다.
    
    Args:
        text: 저장할 텍스트
        output_path: 출력 파일 경로
        encoding: 파일 인코딩
        
    Returns:
        bool: 저장 성공 여부
    """
    try:
        with open(output_path, 'w', encoding=encoding) as f:
            f.write(text)
        return True
    except Exception:
        return False

