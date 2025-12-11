"""
간단한 OCR 테스트 스크립트
"""
import sys
import os

# 테스트용 이미지 경로 (임시 파일 또는 실제 파일)
TEST_IMAGE = None

def test_paddleocr_direct():
    """PaddleOCR 직접 테스트"""
    print("=" * 50)
    print("PaddleOCR 직접 테스트")
    print("=" * 50)
    
    try:
        from paddleocr import PaddleOCR
        print("✅ PaddleOCR import 성공")
        
        # OCR 초기화
        print("\n🔄 OCR 초기화 중...")
        ocr = PaddleOCR(use_angle_cls=True, lang='korean')
        print("✅ OCR 초기화 성공")
        
        # 테스트 이미지가 있으면 실행
        if TEST_IMAGE and os.path.exists(TEST_IMAGE):
            print(f"\n🔄 이미지 OCR 테스트: {TEST_IMAGE}")
            
            # predict 메서드 테스트
            try:
                result = ocr.predict(TEST_IMAGE)
                print(f"✅ predict 성공: {type(result)}")
                print(f"   결과: {result[:200] if str(result) else '빈 결과'}...")
            except Exception as e:
                print(f"❌ predict 오류: {e}")
                import traceback
                traceback.print_exc()
            
            # ocr 메서드 테스트 (구버전 호환)
            try:
                result = ocr.ocr(TEST_IMAGE, cls=True)
                print(f"✅ ocr 성공: {type(result)}")
                if result and result[0]:
                    for line in result[0][:3]:
                        print(f"   - {line[1][0]} (신뢰도: {line[1][1]:.2f})")
            except Exception as e:
                print(f"❌ ocr 오류: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("\n⚠️ 테스트 이미지가 없습니다. 이미지 경로를 지정해주세요.")
            
    except ImportError as e:
        print(f"❌ PaddleOCR import 실패: {e}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


def test_with_url():
    """URL에서 이미지 다운로드 후 테스트"""
    print("\n" + "=" * 50)
    print("URL 이미지 OCR 테스트")
    print("=" * 50)
    
    import tempfile
    import requests
    from PIL import Image
    from io import BytesIO
    
    # 테스트할 URL (실제 서버에서 받아온 것)
    test_url = "http://10.20.248.41/dicom/Data/2025/12/10/003103921_X/1.3.46.670589.29.44774394701671202512101125297521020.dcm/W0001.jpg"
    
    try:
        print(f"🔄 이미지 다운로드 중: {test_url[:60]}...")
        response = requests.get(test_url, timeout=30)
        response.raise_for_status()
        print(f"✅ 다운로드 성공: {len(response.content)} bytes")
        
        # 이미지 로드 및 저장
        image = Image.open(BytesIO(response.content))
        print(f"✅ 이미지 로드 성공: {image.size}, mode={image.mode}")
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
            print(f"✅ RGB 변환 완료")
        
        # 임시 파일 저장
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        image.save(temp_file.name, 'JPEG', quality=95)
        temp_file.close()
        print(f"✅ 임시 파일 저장: {temp_file.name}")
        
        # OCR 테스트
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang='korean')
        
        print("\n🔄 OCR 처리 중...")
        
        # ocr 메서드 사용 (더 안정적)
        result = ocr.ocr(temp_file.name, cls=True)
        
        if result and result[0]:
            print(f"✅ OCR 성공! {len(result[0])}개 텍스트 검출")
            for i, line in enumerate(result[0][:5]):
                text = line[1][0]
                conf = line[1][1]
                print(f"   {i+1}. {text} (신뢰도: {conf:.2%})")
        else:
            print("⚠️ 텍스트를 찾을 수 없습니다.")
        
        # 정리
        os.unlink(temp_file.name)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 다운로드 오류: {e}")
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 명령줄에서 이미지 경로 받기
    if len(sys.argv) > 1:
        TEST_IMAGE = sys.argv[1]
    
    test_paddleocr_direct()
    
    # URL 테스트는 네트워크 접근이 필요하므로 선택적
    # test_with_url()



