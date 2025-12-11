"""
dcas_client.py - Dcas 웹서버 통신 모듈

Dcas 웹서버에서 환자 검사 기록지를 조회하고
이미지 URL을 추출하는 클라이언트 클래스를 제공합니다.
"""

import re
import logging
import warnings
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from io import BytesIO

import requests
from bs4 import BeautifulSoup
import numpy as np
from PIL import Image
import urllib3

# urllib3 헤더 파싱 경고 무시 (DCAS PHP 서버의 비정상적인 헤더 때문)
urllib3.disable_warnings(urllib3.exceptions.HeaderParsingError)
warnings.filterwarnings('ignore', message='Failed to parse headers')

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DcasAuthError(Exception):
    """Dcas 인증 오류"""
    pass


class DcasConnectionError(Exception):
    """Dcas 연결 오류"""
    pass


class DcasParseError(Exception):
    """Dcas 응답 파싱 오류"""
    pass


@dataclass
class PatientInfo:
    """환자 정보 데이터 클래스"""
    cine_no: str  # 검사 번호
    patient_id: str  # 환자 ID
    patient_name: str = ""
    gender: str = ""
    age: str = ""
    study_date: str = ""
    modality: str = "XA"
    
    def __str__(self):
        return f"[{self.patient_id}] {self.patient_name} ({self.gender}/{self.age})"


@dataclass
class StudyInfo:
    """검사 정보 데이터 클래스"""
    patient: PatientInfo
    image_dir: str  # 이미지 디렉토리 경로
    file_count: int  # 이미지 파일 개수
    image_urls: List[str] = field(default_factory=list)  # 이미지 URL 리스트
    
    def get_last_image_url(self) -> Optional[str]:
        """마지막 이미지 (리포트) URL 반환"""
        if self.image_urls:
            return self.image_urls[-1]
        return None


class DcasClient:
    """
    Dcas 웹서버 클라이언트
    
    환자 리스트 조회 및 검사 이미지 URL 추출 기능을 제공합니다.
    """
    
    BASE_URL = "http://10.20.248.41"
    LOGIN_URL = f"{BASE_URL}/login.php"
    LIST_AJAX_URL = f"{BASE_URL}/inc/listAreaAjax.php"
    VIEW_AJAX_URL = f"{BASE_URL}/inc/viewAreaAjax.php"
    
    def __init__(self, user_id: str = "", password: str = ""):
        """
        DcasClient 초기화
        
        Args:
            user_id: Dcas 사용자 ID
            password: Dcas 비밀번호
        """
        self.user_id = user_id
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'Accept': 'text/html, */*; q=0.01',
            'Accept-Language': 'ko,en;q=0.9,en-US;q=0.8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': self.BASE_URL,
            'Referer': f'{self.BASE_URL}/list.php'
        })
        self._logged_in = False
    
    @property
    def is_logged_in(self) -> bool:
        """로그인 상태 확인"""
        return self._logged_in
    
    def login(self, user_id: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Dcas에 로그인합니다.
        
        Args:
            user_id: 사용자 ID (None이면 초기화 시 설정된 값 사용)
            password: 비밀번호 (None이면 초기화 시 설정된 값 사용)
            
        Returns:
            bool: 로그인 성공 여부
            
        Raises:
            DcasAuthError: 로그인 실패 시
        """
        user_id = user_id or self.user_id
        password = password or self.password
        
        if not user_id or not password:
            raise DcasAuthError("사용자 ID와 비밀번호를 입력해주세요.")
        
        try:
            # 로그인 페이지 접속 (세션 쿠키 획득)
            self.session.get(self.LOGIN_URL, timeout=10)
            
            # 로그인 POST 요청
            login_data = {
                'id': user_id,
                'pw': password,
            }
            
            response = self.session.post(
                self.LOGIN_URL,
                data=login_data,
                timeout=10,
                allow_redirects=True
            )
            
            # list.php 접근 시도하여 로그인 성공 확인
            test_response = self.session.get(f"{self.BASE_URL}/list.php", timeout=10)
            
            # login.php로 리다이렉트되면 로그인 실패
            if 'login.php' in test_response.url.lower():
                logger.warning(f"Dcas 로그인 실패: {user_id}")
                raise DcasAuthError("로그인에 실패했습니다. ID와 비밀번호를 확인해주세요.")
            
            self._logged_in = True
            self.user_id = user_id
            self.password = password
            logger.info(f"Dcas 로그인 성공: {user_id}")
            return True
            
        except DcasAuthError:
            raise
        except requests.RequestException as e:
            raise DcasConnectionError(f"Dcas 서버 연결 실패: {str(e)}")
    
    def get_patient_list(
        self,
        modality: str = "XA",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        patient_id: str = "",
        patient_name: str = ""
    ) -> List[PatientInfo]:
        """
        환자 리스트를 조회합니다.
        
        Args:
            modality: 검사 종류 (기본값: XA - 관상동맥조영술)
            start_date: 시작일 (YYYY-MM-DD, 기본값: 오늘)
            end_date: 종료일 (YYYY-MM-DD)
            patient_id: 환자 ID 필터
            patient_name: 환자명 필터
            
        Returns:
            List[PatientInfo]: 환자 정보 리스트
        """
        # 기본값 설정
        if start_date is None:
            start_date = date.today().strftime("%Y-%m-%d")
        
        try:
            # 먼저 list.php에 접근하여 세션 쿠키 획득
            self.session.get(f"{self.BASE_URL}/list.php", timeout=10)
            
            # 환자 리스트 조회 요청 (plusmore 모드로 실제 리스트 가져오기)
            payload = {
                'mode': 'plusmore',
                'nowPage': '0',
                'm_patid': patient_id,
                'm_name': patient_name,
                'remark': '',
                'modal': modality,
                'start_dt': start_date,
                'end_dt': end_date or '',
                'ConfirmSono': '',
                'Physician': '',
                'orderByText': '',
                'orderByDivs': 'desc'
            }
            
            # POST 요청 헤더
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': f'{self.BASE_URL}/list.php'
            }
            
            response = self.session.post(
                self.LIST_AJAX_URL,
                data=payload,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            
            # HTML 파싱하여 환자 리스트 추출
            patients = self._parse_patient_list(response.text)
            logger.info(f"환자 리스트 조회 완료: {len(patients)}명")
            
            return patients
            
        except requests.RequestException as e:
            raise DcasConnectionError(f"환자 리스트 조회 실패: {str(e)}")
    
    def _parse_patient_list(self, html: str) -> List[PatientInfo]:
        """
        HTML에서 환자 리스트를 파싱합니다.
        
        DCAS 응답 형식:
        <ul onclick="clkList('67170','00306304',this);">
            <li>00306304</li>      <!-- patient_id -->
            <li>임병철</li>         <!-- patient_name -->
            <li>XA</li>            <!-- modality -->
            <li>10:52:53 2025-12-10</li>  <!-- datetime -->
            <li>57</li>            <!-- age -->
            <li>M</li>             <!-- gender -->
            ...
        </ul>
        
        Args:
            html: 환자 리스트 HTML
            
        Returns:
            List[PatientInfo]: 환자 정보 리스트
        """
        patients = []
        
        # 정규식으로 <ul onclick="clkList('cine_no','patient_id',this);"> 패턴 파싱
        ul_pattern = r"<ul onclick=\"clkList\('(\d+)','([^']+)',this\);\">(.*?)</ul>"
        ul_matches = re.findall(ul_pattern, html, re.DOTALL)
        
        logger.debug(f"정규식으로 찾은 환자 수: {len(ul_matches)}")
        
        for match in ul_matches:
            try:
                cine_no = match[0]
                patient_id = match[1]
                li_content = match[2]
                
                # <li> 태그 내용 추출
                li_pattern = r"<li[^>]*>([^<]*)</li>"
                li_values = re.findall(li_pattern, li_content)
                
                # 최소 6개의 li가 있어야 함
                # 0: patient_id, 1: name, 2: modality, 3: datetime, 4: age, 5: gender
                if len(li_values) >= 6:
                    patient_name = li_values[1].strip()
                    study_date = li_values[3].strip()
                    age = li_values[4].strip()
                    gender = li_values[5].strip()
                    
                    patient = PatientInfo(
                        cine_no=cine_no,
                        patient_id=patient_id,
                        patient_name=patient_name,
                        gender=gender,
                        age=age,
                        study_date=study_date
                    )
                    patients.append(patient)
                    logger.debug(f"환자 파싱 성공: {patient}")
                else:
                    # li가 부족한 경우에도 기본 정보로 저장
                    patient_name = li_values[1].strip() if len(li_values) > 1 else ""
                    patient = PatientInfo(
                        cine_no=cine_no,
                        patient_id=patient_id,
                        patient_name=patient_name
                    )
                    patients.append(patient)
                    logger.debug(f"환자 파싱 성공 (부분): {patient}")
                    
            except Exception as e:
                logger.debug(f"환자 정보 파싱 오류: {e}")
                continue
        
        # 최종 결과 로깅
        if not patients:
            logger.warning(f"환자 리스트 파싱 실패. HTML 구조 확인 필요.")
            logger.info(f"HTML 응답 전체 길이: {len(html)}")
            # 디버그용: HTML 처음 1000자 로깅
            logger.debug(f"HTML 응답 미리보기:\n{html[:1000]}")
        else:
            logger.info(f"환자 {len(patients)}명 파싱 완료")
        
        return patients
    
    def get_study_info(self, patient: PatientInfo) -> StudyInfo:
        """
        환자의 검사 정보 및 이미지 URL을 조회합니다.
        
        Args:
            patient: 환자 정보
            
        Returns:
            StudyInfo: 검사 정보 (이미지 URL 포함)
        """
        import time
        
        try:
            print(f"🔍 검사 정보 조회: {patient.patient_id} (cine_no: {patient.cine_no})")
            
            # 환자 선택 (clkList 호출) - 썸네일 이미지 URL이 포함된 응답
            click_payload = {
                'mode': 'clkList',
                'cine_no': patient.cine_no,
                'm_patid': patient.patient_id
            }
            
            # POST 요청 헤더
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            }
            
            t1 = time.time()
            response = self.session.post(
                self.LIST_AJAX_URL,
                data=click_payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            print(f"   📡 clkList POST 요청: {time.time() - t1:.2f}초")
            
            logger.debug(f"clkList 응답 길이: {len(response.text)}")
            
            # clkList 응답에서 이미지 URL 파싱
            t2 = time.time()
            study_info = self._parse_study_info(response.text, patient)
            print(f"   🔧 HTML 파싱: {time.time() - t2:.2f}초")
            
            logger.info(f"검사 정보 조회 완료: {patient.patient_id} - 이미지 {study_info.file_count}개")
            
            return study_info
            
        except requests.RequestException as e:
            raise DcasConnectionError(f"검사 정보 조회 실패: {str(e)}")
    
    def _parse_study_info(self, html: str, patient: PatientInfo) -> StudyInfo:
        """
        HTML에서 검사 정보를 파싱합니다.
        
        clkList 응답 형식:
        <li onclick="clkThumbnail('67143','2590306',this)">
            <img src="./dicom/Data/2025/12/10/00238560_X/swf_s/xxx.dcm.JPG">
        </li>
        
        썸네일 URL → 실제 이미지 URL 변환:
        - 썸네일: .../00238560_X/swf_s/xxx.dcm.JPG
        - 실제:   .../00238560_X/xxx.dcm/W0001.jpg
        
        Args:
            html: clkList 응답 HTML
            patient: 환자 정보
            
        Returns:
            StudyInfo: 검사 정보
        """
        image_urls = []
        image_dir = ""
        
        # 정규식으로 썸네일 img src 추출
        # 리포트 이미지는 "1020.dcm.JPG"로 끝나는 파일 중 첫 번째만 해당
        # <img src="./dicom/Data/2025/12/10/00306304_X/swf_s/xxx1020.dcm.JPG" alt="thumbNail">
        img_pattern = r'<img\s+src="([^"]+/swf_s/[^"]+1020\.dcm\.JPG)"'
        img_matches = re.findall(img_pattern, html, re.IGNORECASE)
        
        logger.info(f"🔍 리포트 이미지 (1020.dcm) 발견: {len(img_matches)}개")
        
        # 첫 번째 리포트 이미지만 사용
        if img_matches:
            thumb_src = img_matches[0]  # 첫 번째만!
            
            # 상대 경로 처리
            if thumb_src.startswith('./'):
                thumb_src = thumb_src[2:]
            
            # 썸네일 URL → 실제 이미지 URL 변환
            # ./dicom/Data/2025/12/10/00306304_X/swf_s/xxx1020.dcm.JPG
            # → dicom/Data/2025/12/10/00306304_X/xxx1020.dcm/W0001.jpg
            
            # /swf_s/ 제거하고 .JPG를 /W0001.jpg로 변경
            real_src = thumb_src.replace('/swf_s/', '/')
            real_src = re.sub(r'\.dcm\.JPG$', '.dcm/W0001.jpg', real_src, flags=re.IGNORECASE)
            
            url = f"{self.BASE_URL}/{real_src}"
            image_urls.append(url)
            logger.info(f"✅ 리포트 URL (1개): {url}")
            
            # 디렉토리 경로 추출
            dir_match = re.match(r'(.*/)([^/]+)$', real_src)
            if dir_match:
                image_dir = dir_match.group(1)
        
        if not image_urls:
            logger.warning(f"이미지 URL을 찾을 수 없습니다: {patient.patient_id}")
            logger.debug(f"HTML 응답 미리보기:\n{html[:2000]}")
            raise DcasParseError("이미지를 찾을 수 없습니다.")
        
        logger.info(f"이미지 URL {len(image_urls)}개 파싱 완료 (마지막: {image_urls[-1]})")
        
        return StudyInfo(
            patient=patient,
            image_dir=image_dir,
            file_count=len(image_urls),
            image_urls=image_urls
        )
    
    def download_image(self, url: str) -> np.ndarray:
        """
        이미지를 다운로드하여 numpy 배열로 반환합니다.
        
        Args:
            url: 이미지 URL
            
        Returns:
            np.ndarray: RGB 형식의 이미지 배열
        """
        try:
            print(f"📥 이미지 다운로드: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # 응답 확인
            content_type = response.headers.get('Content-Type', '')
            print(f"   Content-Type: {content_type}, 크기: {len(response.content)} bytes")
            
            if 'image' not in content_type.lower() and len(response.content) < 1000:
                print(f"   ⚠️ 이미지가 아닌 응답: {response.content[:500]}")
                raise DcasParseError(f"이미지가 아닌 응답을 받았습니다: {content_type}")
            
            # 이미지 로드
            image = Image.open(BytesIO(response.content))
            print(f"   ✅ 이미지 로드 성공: {image.size}, mode={image.mode}")
            
            # RGB 변환
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            return np.array(image)
            
        except requests.RequestException as e:
            raise DcasConnectionError(f"이미지 다운로드 실패: {str(e)}")
        except DcasParseError:
            raise
        except Exception as e:
            import traceback
            logger.error(f"이미지 처리 오류: {e}\n{traceback.format_exc()}")
            raise DcasParseError(f"이미지 처리 실패: {str(e)}")
    
    def download_report_image(self, patient: PatientInfo) -> Optional[np.ndarray]:
        """
        환자의 리포트 이미지 (마지막 이미지)를 다운로드합니다.
        
        Args:
            patient: 환자 정보
            
        Returns:
            Optional[np.ndarray]: 리포트 이미지 (없으면 None)
        """
        study_info = self.get_study_info(patient)
        report_url = study_info.get_last_image_url()
        
        if report_url:
            return self.download_image(report_url)
        return None
    
    def logout(self):
        """세션을 종료합니다."""
        self.session.close()
        self._logged_in = False
        logger.info("Dcas 로그아웃 완료")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logout()


# 편의 함수
def create_dcas_client(user_id: str, password: str) -> DcasClient:
    """
    DcasClient를 생성하고 로그인합니다.
    
    Args:
        user_id: 사용자 ID
        password: 비밀번호
        
    Returns:
        DcasClient: 로그인된 클라이언트
    """
    client = DcasClient(user_id, password)
    client.login()
    return client

