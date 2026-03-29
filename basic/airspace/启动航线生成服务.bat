@echo off
chcp 65001 >nul
title 航线自动生成服务

echo ============================================
echo    航线自动生成服务启动器
echo ============================================
echo.

cd /d "%~dp0"

echo 正在启动服务...
echo.
echo 启动后请访问:
echo   http://127.0.0.1:5500/flight_generator.html
echo.
echo 按 Ctrl+C 停止服务
echo.

python flight_generator_server.py

pause
