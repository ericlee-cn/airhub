@echo off
echo ========================================
echo    MGS 空域管理系统启动脚本
echo ========================================
echo.
echo 请选择启动方式：
echo.
echo [1] 打开独立版本（推荐，无需服务器）
echo [2] 启动本地服务器并打开浏览器
echo [3] 退出
echo.
set /p choice=请输入选项（1-3）：

if "%choice%"=="1" goto standalone
if "%choice%"=="2" goto server
if "%choice%"=="3" goto end

echo 无效选项，请重新运行脚本
goto end

:standalone
echo.
echo 正在打开独立版本...
start cesium_airspace_standalone.html
goto end

:server
echo.
echo 正在启动本地HTTP服务器...
echo 服务器地址: http://localhost:8000
echo 按 Ctrl+C 停止服务器
echo.
python -m http.server 8000
if %errorlevel% neq 0 (
    echo Python未安装或启动失败，尝试使用Node.js...
    npx http-server -p 8000
)

:end
