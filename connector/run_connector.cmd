@echo off
rem ========================================================
rem DAON Mobile Remote Connector - Auto-Restart Watchdog
rem ========================================================
title DAON Mobile Remote Connector Watchdog

:loop
echo [%date% %time%] Starting DAON Mobile Connector... >> "C:\daon\mobile\LLM\chat\connector\connector_runtime.log"
"C:\Users\ttl09\AppData\Local\Programs\Python\Python312\python.exe" -u "C:\daon\mobile\LLM\chat\connector\daon_remote_connector.py" >> "C:\daon\mobile\LLM\chat\connector\connector_runtime.log" 2>&1
echo [%date% %time%] Connector exited (code: %ERRORLEVEL%). Restarting in 5s... >> "C:\daon\mobile\LLM\chat\connector\connector_runtime.log"
timeout /t 5 /nobreak >nul
goto loop
