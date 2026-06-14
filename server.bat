@echo off
chcp 65001 >nul
TITLE 3D Scoring Web Server Manager

set ACTION=%~1

if /I "%ACTION%"=="start" goto start_service
if /I "%ACTION%"=="stop" goto stop_service
if /I "%ACTION%"=="restart" goto restart_service

echo ===================================================
echo 3D 评分 Web 服务管理脚本
echo ===================================================
echo 用法:
echo   server.bat start   - 启动服务
echo   server.bat stop    - 停止服务 (强杀占用 5000 端口的进程)
echo   server.bat restart - 重启服务 (先杀进程再启动)
goto end

:start_service
echo.
echo [检查] 正在检查端口 5000...
set found=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    set found=1
)
if "%found%"=="1" (
    echo [警告] 端口 5000 已被占用！服务可能已经在运行中。
    echo 请先执行 "server.bat stop" 来停止旧服务。
    goto end
)
echo [启动] 正在启动服务...
start "3D Scoring Web Server" cmd /c "python student_web\app.py"
echo [成功] 服务已在后台独立窗口中启动！
echo [访问] 请在浏览器打开: http://127.0.0.1:5000
goto end

:stop_service
echo.
echo [停止] 正在查找并关闭占用 5000 端口的 Web 进程...
set found=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    echo [操作] 正在结束占用端口的进程 (PID: %%a) ...
    taskkill /F /PID %%a
    set found=1
)
if "%found%"=="0" (
    echo [提示] 未发现运行在 5000 端口的服务。
) else (
    echo [成功] 服务已成功彻底停止！
)
goto end

:restart_service
echo.
echo [重启] 正在停止当前服务...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 >nul
echo [启动] 正在重新启动服务...
start "3D Scoring Web Server" cmd /c "python student_web\app.py"
echo [成功] 服务已重启并在后台运行！
echo [访问] 请在浏览器打开: http://127.0.0.1:5000
goto end

:end
