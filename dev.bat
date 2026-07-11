@echo off
cd /d "%~dp0"

echo Starting RogueMind...
echo Backend path: %~dp0backend
echo.

echo [1/3] Starting backend...
start "RogueMind-Backend" cmd /k "cd /d %~dp0backend && e:\anaconda\envs\RogueMind\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [2/3] Waiting for backend to be ready...
:loop
ping 127.0.0.1 -n 4 >nul
curl -s http://127.0.0.1:8000/api/health >nul 2>&1
if errorlevel 1 (
    echo   still waiting...
    goto loop
)
echo   Backend is ready!

echo [3/3] Starting frontend...
start "RogueMind-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Waiting for frontend...
:loop2
ping 127.0.0.1 -n 3 >nul
curl -s http://localhost:5173 >nul 2>&1
if errorlevel 1 (
    echo   still waiting...
    goto loop2
)

echo Opening desktop window...
start msedge --app=http://localhost:5173 --new-window --window-size=1280,800

echo.
echo All done! You can close this window.
pause
