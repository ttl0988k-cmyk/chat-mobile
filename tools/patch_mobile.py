# -*- coding: utf-8 -*-
"""모바일 앱 패치 v2: app.js / index.html / style.css — \\r\\r\\n 개행 대응"""
import io, sys

def rep(path, old, new, tag, count=1):
    src = io.open(path, 'r', encoding='utf-8', newline='').read()
    eol = '\r\r\n' if '\r\r\n' in src[:2000] else ('\r\n' if '\r\n' in src[:2000] else '\n')
    old_n = old.replace('\n', eol)
    new_n = new.replace('\n', eol)
    if old_n not in src:
        if old in src:
            old_n, new_n = old, new
        else:
            print('[FAIL] %s — 매칭 실패' % tag); sys.exit(1)
    src = src.replace(old_n, new_n, count)
    io.open(path, 'w', encoding='utf-8', newline='').write(src)
    print('[OK] %s (eol=%r)' % (tag, eol))

APP = r'C:\daon\cafe\LLM\chat\app.js'
HTML = r'C:\daon\cafe\LLM\chat\index.html'
CSS = r'C:\daon\cafe\LLM\chat\style.css'

io.open(APP + '.bak-2026-08-30-auto', 'w', encoding='utf-8', newline='').write(io.open(APP, 'r', encoding='utf-8', newline='').read())

# A) delta에서 stream_id 획득 → ⏹️ 작업중단 버튼 평시 활성
rep(APP,
"""    if (mtype === 'delta' && row.role === 'assistant') {
      if (!pendingAssistantEl) {""",
"""    if (mtype === 'delta' && row.role === 'assistant') {
      if (row.metadata && row.metadata.stream_id) activeStreamId = row.metadata.stream_id;
      if (!pendingAssistantEl) {""",
'A-delta-stream-id')

# B) 승인 카드: 처리완료(auto_approved)면 읽기전용
rep(APP,
"""      activeStreamId = d.stream_id || activeStreamId;
      activeSessionId = d.session_id || activeSessionId;
      const el = createBubble('tool', row.content, true);""",
"""      activeStreamId = d.stream_id || activeStreamId;
      activeSessionId = d.session_id || activeSessionId;
      if (d.status && d.status !== 'pending') {
        // 자동 승인/만료 등 이미 처리된 요청 → 읽기 전용 안내 (버튼 없음)
        createBubble('tool', row.content, true);
        scrollBottom();
        return;
      }
      const el = createBubble('tool', row.content, true);""",
'B-승인읽기전용')

# C) notice로 자율실행 상태 동기화
rep(APP,
"""    // 첨부 파일이 있는 메시지 (이미지 인라인 / 기타 파일 링크)""",
"""    // 자율 실행 상태 동기화 (커넥터 notice)
    if (mtype === 'notice' && typeof meta.auto === 'boolean') {
      autoMode = meta.auto;
      updateAutoBtn();
    }

    // 첨부 파일이 있는 메시지 (이미지 인라인 / 기타 파일 링크)""",
'C-상태동기화')

# D) 버튼 이벤트 연결
rep(APP,
"  $('interrupt-btn').addEventListener('click', sendInterrupt);",
"  $('interrupt-btn').addEventListener('click', sendInterrupt);\n"
"  const _autoBtn = document.getElementById('auto-btn');\n"
"  if (_autoBtn) _autoBtn.addEventListener('click', sendAutonomousToggle);",
'D-버튼연결')

# E) index.html: 자율실행 토글 버튼 추가
rep(HTML,
'          <button id="interrupt-btn" class="ghost small" title="작업 중단">⏹️</button>',
'          <button id="auto-btn" class="ghost small" title="자율 실행">🛡️</button>\n'
'          <button id="interrupt-btn" class="ghost small" title="작업 중단">⏹️</button>',
'E-버튼추가')

# F) style.css: system 메시지 + 자율 토글 ON 스타일
rep(CSS,
".approval-btns { display: flex; gap: 8px; margin-top: 8px; }",
".msg-row.system { align-self: center; max-width: 90%; }\n"
".msg-row.system .bubble {\n"
"  background: transparent;\n"
"  border: 1px dashed #475569;\n"
"  color: #94a3b8;\n"
"  font-size: 12px;\n"
"  padding: 6px 10px;\n"
"  text-align: center;\n"
"  border-radius: 10px;\n"
"}\n"
"#auto-btn.auto-on { background: #f59e0b; color: #1c1917; border-color: #f59e0b; }\n"
".approval-btns { display: flex; gap: 8px; margin-top: 8px; }",
'F-스타일')

print('=== 모바일 앱 패치 완료 ===')
