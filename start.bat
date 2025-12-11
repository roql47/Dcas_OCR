@echo off
chcp 65001 >nul
title OCR 시스템 실행

echo ========================================
echo    OCR 시스템 시작
echo ========================================
echo.

REM 현재 디렉토리 저장
set ROOT_DIR=%~dp0

echo [1/2] 백엔드 서버 시작 중...
cd /d "%ROOT_DIR%"
start "백엔드 서버 (FastAPI)" cmd /k "chcp 65001 >nul && call venv\Scripts\activate && cd backend && python main.py"

echo [2/2] 프론트엔드 서버 시작 중...
cd /d "%ROOT_DIR%frontend"
start "프론트엔드 서버 (Vite)" cmd /k "chcp 65001 >nul && npm run dev"

echo.
echo ========================================
echo    모든 서버가 시작되었습니다!
echo ========================================
echo.
echo  - 백엔드:    http://localhost:8000
echo  - 프론트엔드: http://localhost:5173
echo.
echo  종료하려면 각 창을 닫아주세요.
echo ========================================
echo.
pause


