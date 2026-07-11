@echo off
title RogueMind
echo ================================
echo   RogueMind v0.1
echo ================================
echo.
echo [1/2] Starting backend...
start "RogueMind Backend" /MIN "%~dp0backend\backend.exe"
echo [2/2] Waiting for backend (about 30s)...
:wait
ping 127.0.0.1 -n 3 >nul
curl -s http://127.0.0.1:8000/api/health >nul 2>&1
if errorlevel 1 goto wait
echo Launching RogueMind...
start "" "%~dp0RogueMind.exe"
echo Done!
