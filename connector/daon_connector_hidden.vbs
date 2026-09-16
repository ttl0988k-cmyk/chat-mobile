' ============================================================
'  DAON Mobile Connector - 완전 숨김 런처
'  창을 아예 만들지 않아 Ctrl+C / 창닫기 시그널에 죽지 않음
'  (기존 Start-Process -WindowStyle Minimized 는 ^C 로 종료됨)
'
'  ※ 변수명 log 는 VBScript 내장 함수 Log() 와 충돌해
'     "잘못된 할당(501)" 런타임 오류가 발생한다.
'     반드시 logFile 을 사용할 것. (2026-09-17 수정)
' ============================================================
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

base = "C:\daon\mobile\LLM\chat\connector"

' 작업 폴더 이동
sh.CurrentDirectory = base

' 워치독을 창 없이(0 = hidden) 실행
sh.Run "cmd /c """ & base & "\run_connector.cmd""", 0, False

' 실행 증거 남기기 (실패해도 창을 띄우지 않음)
On Error Resume Next
Set logFile = fso.OpenTextFile(base & "\launcher_hidden.log", 8, True)
logFile.WriteLine "[" & Now & "] VBScript hidden launcher invoked (WScript window style 0)"
logFile.Close
On Error GoTo 0
