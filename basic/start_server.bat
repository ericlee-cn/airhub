@echo off
chcp 65001 >nul
echo.
echo ========================================
echo    低空仿真系统 - 统一导航平台
echo ========================================
echo.
echo 正在启动本地 HTTP 服务器...
echo 请稍候，浏览器将自动打开...
echo.
echo 提示：按 Ctrl+C 可停止服务器
echo ========================================
echo.

python -m http.server 8080 --directory "%~dp0"

pause
