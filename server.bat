@echo off
chcp 65001 >nul
TITLE 3D Scoring Web Server Manager

set ACTION=%~1

if /I "%ACTION%"=="start" goto start_service
if /I "%ACTION%"=="stop" goto stop_service
if /I "%ACTION%"=="restart" goto restart_service

echo ===================================================
echo 3D Scoring Web Server Script
echo ===================================================
echo Usage:
echo   server.bat start   - Start server
echo   server.bat stop    - Stop server (kill port 5000)
echo   server.bat restart - Restart server
goto end

:start_service
echo.
echo [CHECK] Checking port 5000...
set found=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    set found=1
)
if "%found%"=="1" (
    echo [WARN] Port 5000 is in use! Server may be running.
    echo Please run "server.bat stop" first.
    goto end
)
echo [START] Starting server (Hidden Console)...
start "" pythonw student_web\app.py
echo [SUCCESS] Server started in background!
echo [URL] Visit http://127.0.0.1:5000
goto end

:stop_service
echo.
echo [STOP] Finding process on port 5000...
set found=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    echo [KILL] Terminating PID: %%a ...
    taskkill /F /PID %%a
    set found=1
)
if "%found%"=="0" (
    echo [INFO] No server found on port 5000.
) else (
    echo [SUCCESS] Server stopped!
)
goto end

:restart_service
echo.
echo [RESTART] Stopping current server...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 >nul
echo [START] Starting new server (Hidden Console)...
start "" pythonw student_web\app.py
echo [SUCCESS] Server restarted!
echo [URL] Visit http://127.0.0.1:5000
goto end

:end
