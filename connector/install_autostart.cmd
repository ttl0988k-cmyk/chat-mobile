@echo off
rem ============================================================
rem  DAON Mobile Connector - 자동 시작 등록 / 해제
rem  이 파일이 있는 폴더를 기준으로 바로가기를 만들어줍니다.
rem
rem   등록: install_autostart.cmd
rem   해제: install_autostart.cmd remove
rem ============================================================
setlocal EnableExtensions
title DAON Connector - Auto Start Setup

set "BASE=%~dp0"
if "%BASE:~-1%"=="\" set "BASE=%BASE:~0,-1%"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS=%BASE%\daon_connector_hidden.vbs"
set "LNK=%STARTUP%\DAON Mobile Connector.lnk"
set "PS1=%TEMP%\daon_mklnk.ps1"

if /i "%~1"=="remove" goto :REMOVE

echo.
echo  ============================================================
echo   DAON Mobile Connector - 자동 시작 등록
echo  ============================================================
echo.
echo   커넥터 폴더 : %BASE%
echo   등록 위치   : %STARTUP%
echo.

if not exist "%VBS%" goto :NOVBS
if not exist "%STARTUP%" goto :NOSTARTUP

if exist "%LNK%" echo  [알림] 이미 등록되어 있습니다. 새로 덮어씁니다.
echo.

rem ── 바로가기 생성용 PowerShell 스크립트 작성 ──
> "%PS1%" echo $ws = New-Object -ComObject WScript.Shell
>>"%PS1%" echo $l = $ws.CreateShortcut("%LNK%")
>>"%PS1%" echo $l.TargetPath = "C:\Windows\System32\wscript.exe"
>>"%PS1%" echo $l.Arguments = '"%VBS%"'
>>"%PS1%" echo $l.WorkingDirectory = "%BASE%"
>>"%PS1%" echo $l.WindowStyle = 7
>>"%PS1%" echo $l.Description = "DAON Mobile Connector (hidden auto-start)"
>>"%PS1%" echo $l.Save()

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
set "RC=%ERRORLEVEL%"
del "%PS1%" >nul 2>nul

if not "%RC%"=="0" goto :MAKEFAIL
if not exist "%LNK%" goto :MAKEFAIL

echo  [완료] 자동 시작이 등록되었습니다.
echo.
echo   ※ PC를 켜고 로그인하면 커넥터가 자동으로 실행됩니다.
echo   ※ 해제:  install_autostart.cmd remove
echo.
echo   확인: Win+R -^> shell:startup
echo         "DAON Mobile Connector" 바로가기가 보이면 성공
echo.
pause
exit /b 0


:NOVBS
echo  [오류] daon_connector_hidden.vbs 가 이 폴더에 없습니다.
echo         압축을 풀 때 파일이 누락된 것 같습니다. 다시 받아주세요.
echo.
pause
exit /b 1

:NOSTARTUP
echo  [오류] 시작프로그램 폴더를 찾지 못했습니다:
echo         %STARTUP%
echo.
pause
exit /b 1

:MAKEFAIL
echo  [오류] 바로가기 생성에 실패했습니다.
echo.
echo   수동으로 만들어주세요:
echo     1) Win+R -^> shell:startup -^> Enter
echo     2) 빈 곳 우클릭 -^> 새로 만들기 -^> 바로가기
echo     3) 대상에 아래를 붙여넣기:
echo        wscript.exe "%VBS%"
echo     4) 이름: DAON Mobile Connector
echo.
pause
exit /b 1


:REMOVE
echo.
echo  ============================================================
echo   DAON Mobile Connector - 자동 시작 해제
echo  ============================================================
echo.
if exist "%LNK%" (
  del "%LNK%"
  echo  [완료] 자동 시작을 해제했습니다.
) else (
  echo  [알림] 등록된 바로가기가 없습니다.
)
echo.
pause
exit /b 0
