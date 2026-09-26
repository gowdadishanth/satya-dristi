@echo off
title Satya Dristi Launcher
echo ========================================================
echo        Starting Satya Dristi Earth Observation
echo ========================================================
echo.

REM 1. Start FastAPI Backend in a new window
echo [1/2] Starting Backend Server (FastAPI on port 8000)...
start "Satya Dristi Backend" cmd /k "cd /d "%~dp0backend" && call .venv\Scripts\activate && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

REM 2. Start Vite Frontend in a new window
echo [2/2] Starting Frontend Server (Vite on port 8443)...
start "Satya Dristi Frontend" cmd /k "cd /d "%~dp0" && pnpm run dev"

echo.
echo ========================================================
echo  Both services launched in separate windows!
echo  - Frontend: http://localhost:8443
echo  - Backend:  http://127.0.0.1:8000
echo ========================================================
pause
