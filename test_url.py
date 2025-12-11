"""
DCAS 이미지 OCR 테스트 - 이미지 리사이즈 적용
"""
import requests
import traceback
import tempfile
import os
from PIL import Image
from io import BytesIO

# DCAS 이미지 URL
url = "http://10.20.248.41/dicom/Data/2025/12/10/00238560_X/1.3.46.670589.29.44774394701671202512100852270841020.dcm/W0001.jpg"

print("=" * 60)
print("DCAS 이미지 OCR 테스트 (이미지 리사이즈)")
print("=" * 60)
print(f"URL: {url}")

try:
    # 1. 이미지 다운로드
    print("\n[1] 이미지 다운로드...")
    r = requests.get(url, timeout=10)
    print(f"   Status: {r.status_code}, Size: {len(r.content)} bytes")
    
    # 2. PIL로 이미지 로드
    print("\n[2] PIL 이미지 로드...")
    image = Image.open(BytesIO(r.content))
    print(f"   원본: {image.format}, Mode: {image.mode}, Size: {image.size}")
    
    # RGB 변환
    if image.mode != 'RGB':
        image = image.convert('RGB')
        print("   ✅ RGB로 변환됨")
    
    # 이미지 리사이즈 (최대 1024px)
    max_size = 1024
    w, h = image.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        new_w, new_h = int(w * ratio), int(h * ratio)
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        print(f"   ✅ 리사이즈: {w}x{h} → {new_w}x{new_h}")
    
    # 3. 임시 파일로 저장
    print("\n[3] 임시 파일로 저장...")
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    image.save(temp_file.name, 'JPEG', quality=95)
    temp_file.close()
    file_size = os.path.getsize(temp_file.name)
    print(f"   파일: {temp_file.name}")
    print(f"   크기: {file_size} bytes")
    
    # 4. PaddleOCR 직접 사용
    print("\n[4] PaddleOCR 초기화...")
    from paddleocr import PaddleOCR
    import numpy as np
    
    ocr = PaddleOCR(use_angle_cls=True, lang='korean')
    
    print("\n[5] OCR 처리...")
    # numpy 배열로 변환해서 전달
    img_array = np.array(image)
    result = ocr.predict(img_array)
    
    print(f"   ✅ OCR 성공!")
    
    # 결과 출력
    if result:
        print(f"\n[6] OCR 결과:")
        for item in result:
            if isinstance(item, dict) and 'rec_texts' in item:
                texts = item.get('rec_texts', [])
                scores = item.get('rec_scores', [])
                for i, text in enumerate(texts[:15]):
                    score = scores[i] if i < len(scores) else 0
                    print(f"   {i+1}. {text} ({score:.2%})")
                if len(texts) > 15:
                    print(f"   ... 외 {len(texts) - 15}줄")
    
    # 임시 파일 삭제
    os.unlink(temp_file.name)
    print(f"\n✅ 테스트 완료!")
    
except Exception as e:
    print(f"\n❌ 오류: {e}")
    print(f"\n📋 스택 트레이스:\n{traceback.format_exc()}")
