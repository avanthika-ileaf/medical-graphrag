@echo off
echo ============================================
echo  medknow - Starting FastAPI Backend
echo ============================================
echo.
echo API will be available at: http://localhost:8080
echo API Docs at:              http://localhost:8080/api/docs
echo.
cd /d "%~dp0"
.venv\Scripts\python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8080
