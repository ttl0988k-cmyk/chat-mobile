@echo off
rem ========================================================
rem DAON Mobile Remote Connector - Auto-Restart Watchdog
rem ========================================================
title DAON Mobile Remote Connector Watchdog

:loop
echo [%date% %time%] Starting DAON Mobile Connector... >> "C:\daon\mobile\LLM\chat\connector\connector_runtime.log"
"C:\Users\ttl09\AppData\Local\Programs\Python\Python312\python.exe" -u "C:\daon\mobile\LLM\chat\connector\daon_remote_connector.py" >> "C:\daon\mobile\LLM\chat\connector\connector_runtime.log" 2>&1
set EXIT_CODE=%ERRORLEVEL%
if %EXIT_CODE% EQU 42 (
    echo [%date% %time%] Another connector instance is already active (code 42). Watchdog exiting cleanly. >> "C:\daon\mobile\LLM\chat\connector\connector_runtime.log"
    exit /b 0
)
echo [%date% %time%] Connector exited (code: %EXIT_CODE%). Restarting in 5s... >> "C:\daon\mobile\LLM\chat\connector\connector_runtime.log"
timeout /t 5 /nobreak >nul
goto loop
