@echo off
echo ========================================================
echo   Starting ContentPulse (Frontend: 4444, Backend: 8888)
echo ========================================================
echo.

start "ContentPulse Backend (FastAPI - Port 8888)" cmd /k "cd backend && python -m uvicorn main:app --reload --host 127.0.0.1 --port 8888"
start "ContentPulse Frontend (React Vite - Port 4444)" cmd /k "cd frontend && npm run dev -- --host 127.0.0.1 --port 4444"

echo.
echo Backend running on http://127.0.0.1:8888
echo Frontend running on http://127.0.0.1:4444
echo.
pause
