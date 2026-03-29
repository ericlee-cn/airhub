@echo off
chcp 65001 > nul
echo ========================================
echo    Cesium 空域航路管理系统
echo ========================================
echo.
echo 正在启动本地服务器...
echo 浏览器将自动打开 http://localhost:8080
echo.
echo 按 Ctrl+C 可停止服务器
echo ========================================
echo.

cd /d "%~dp0"
python -m http.server 8080

pause