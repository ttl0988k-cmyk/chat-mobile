' ============================================================
'  DAON Mobile Connector - 무음 런처 (대체용)
'  ※ daon_connector_hidden.vbs 를 권장합니다. 이 파일은 호환용입니다.
'  경로 하드코딩 없음 — 이 스크립트 위치를 기준으로 동작
' ============================================================
Option Explicit

Dim sh, fso, base
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

base = fso.GetParentFolderName(WScript.ScriptFullName)

sh.CurrentDirectory = base
sh.Run "cmd.exe /c """ & base & "\run_connector.cmd""", 0, False
