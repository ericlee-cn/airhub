@echo off
chcp 65001 >nul
title AirFogSim 低空仿真推演系统

echo.
echo  ╔══════════════════════════════════════╗
echo  ║    AirFogSim 低空仿真推演系统         ║
echo  ║    正在启动后台服务...                ║
echo  ╚══════════════════════════════════════╝
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 检查 Python
where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 杀掉占用端口 8080 / 8765 的旧进程
echo [1/3] 清理旧进程...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8080 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8765 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: 后台启动 server.py（新窗口，最小化）
echo [2/3] 启动后台服务 (HTTP:8080  WS:8765)...
start /min "AirFogSim-Server" python server.py

:: 等待服务就绪（最多等15秒）
echo [3/3] 等待服务就绪...
set /a tries=0
:wait_loop
timeout /t 1 /nobreak >nul
set /a tries+=1
netstat -ano 2>nul | findstr ":8080 " | findstr "LISTENING" >nul
if not errorlevel 1 goto ready
if %tries% geq 15 (
    echo.
    echo [警告] 服务启动超时，请检查窗口"AirFogSim-Server"中的错误信息
    pause
    exit /b 1
)
goto wait_loop

:ready
echo.
echo  ✓ 服务已就绪！正在打开浏览器...
echo  ✓ 地址: http://localhost:8080
echo.
start http://localhost:8080

echo  按任意键关闭此窗口（服务将继续在后台运行）
echo  如需停止服务，请关闭 "AirFogSim-Server" 窗口
pause >nul
