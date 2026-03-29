@echo off
chcp 65001 >nul
title 航线生成工具服务器

cd /d "%~dp0"
echo ========================================
echo   航线自动生成工具 - 服务器启动
echo ========================================
echo.
echo 正在启动服务器...
python -m http.server 5500
pause
