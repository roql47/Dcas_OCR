@echo off
chcp 65001 >nul
title OCR 시스템 설치

echo ========================================
echo    OCR 시스템 초기 설치
echo ========================================
echo.

REM 현재 디렉토리 저장
set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%"

echo [1/4] Python 가상환경 생성 중...
echo.
if exist "venv" (
    echo  - 기존 venv 폴더가 존재합니다. 건너뜁니다.
) else (
    python -m venv venv
    if errorlevel 1 (
        echo  ❌ Python 가상환경 생성 실패!
        echo  Python이 설치되어 있는지 확인해주세요.
        pause
        exit /b 1
    )
    echo  ✓ 가상환경 생성 완료
)
echo.

echo [2/4] Python 가상환경 활성화 중...
call venv\Scripts\activate
if errorlevel 1 (
    echo  ❌ 가상환경 활성화 실패!
    pause
    exit /b 1
)
echo  ✓ 가상환경 활성화 완료
echo.

echo [3/4] Python 패키지 설치 중...
echo  (PaddleOCR 등 용량이 커서 시간이 걸릴 수 있습니다)
echo.
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo  ❌ Python 패키지 설치 실패!
    pause
    exit /b 1
)
echo.
echo  ✓ Python 패키지 설치 완료
echo.

echo [4/4] 프론트엔드 패키지 설치 중...
cd /d "%ROOT_DIR%frontend"
if not exist "package.json" (
    echo  ❌ frontend/package.json 파일을 찾을 수 없습니다!
    pause
    exit /b 1
)
call npm install
if errorlevel 1 (
    echo.
    echo  ❌ npm 패키지 설치 실패!
    echo  Node.js가 설치되어 있는지 확인해주세요.
    pause
    exit /b 1
)
echo.
echo  ✓ 프론트엔드 패키지 설치 완료
echo.

cd /d "%ROOT_DIR%"

echo ========================================
echo    설치가 완료되었습니다!
echo ========================================
echo.
echo  다음 명령어로 서버를 실행하세요:
echo    start.bat
echo.
echo ========================================
pause

