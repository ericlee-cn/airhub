@echo off
chcp 65001 >nul
echo ========================================
echo    启动基础模型管理系统服务器
echo ========================================
echo.
echo 服务器地址: http://localhost:8080
echo.
echo 按下 Ctrl+C 可以停止服务器
echo.
echo ========================================
echo.

cd /d "%~dp0"

python -m http.server 8080

pause
