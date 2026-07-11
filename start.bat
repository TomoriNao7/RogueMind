@echo off
title RogueMind
echo ================================
echo   RogueMind 集成战略助手
echo ================================
echo.

echo [1/2] 启动后端服务...
start "RogueMind Backend" /MIN "%~dp0backend\backend.exe"

echo [2/2] 等待后端就绪（约30秒）...
:wait
ping 127.0.0.1 -n 3 >nul
curl -s http://127.0.0.1:8000/api/health >nul 2>&1
if errorlevel 1 goto wait

echo 启动 RogueMind...
start "" "%~dp0RogueMind.exe"
echo 已启动！
