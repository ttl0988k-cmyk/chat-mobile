# patch_mobile_stop_mode.py
import re
import time

app_path = r"C:\daon\cafe\LLM\chat\app.js"
css_path = r"C:\daon\cafe\LLM\chat\style.css"
html_path = r"C:\daon\cafe\LLM\chat\index.html"

# 1. Patch style.css
with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

stop_btn_css = '''
/* 작업 중단 버튼 (스트리밍 / 작업 중 상태) */
button.stop-btn {
  background: #ef4444 !important;
  color: #ffffff !important;
  border-color: #dc2626 !important;
  font-weight: 600 !important;
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.4) !important;
}
button.stop-btn:hover, button.stop-btn:active {
  background: #dc2626 !important;
}
'''

if "button.stop-btn" not in css:
    css = css + "\n" + stop_btn_css
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css)
    print("1. style.css updated with stop-btn styles")
else:
    print("1. style.css already contains stop-btn styles")

# 2. Patch app.js
with open(app_path, "r", encoding="utf-8") as f:
    app = f.read()

# Add isWorking and setWorkingState
old_selected_model = "let selectedModel = '';      // 모바일에서 선택한 모델"
new_selected_model = '''let selectedModel = '';      // 모바일에서 선택한 모델
  let isWorking = false;       // 작업 진행 중 플래그 (중단 모드 전환용)

  function setWorkingState(working) {
    isWorking = !!working;
    const btn = $('send-btn');
    const input = $('send-input');
    if (!btn) return;
    if (isWorking) {
      btn.textContent = '⏹️ 중단';
      btn.classList.remove('primary');
      btn.classList.add('stop-btn');
      btn.title = '작업 중단';
      if (input) input.placeholder = '라온이 작업 중입니다… (중단하려면 ⏹️)';
    } else {
      btn.textContent = '전송';
      btn.classList.remove('stop-btn');
      btn.classList.add('primary');
      btn.title = '전송';
      if (input) input.placeholder = '라온에게 보낼 작업 지시…';
    }
  }'''

if old_selected_model in app:
    app = app.replace(old_selected_model, new_selected_model, 1)
    print("2.1 setWorkingState added to app.js")
else:
    print("WARNING: old_selected_model not found")

# Update sendInterrupt
old_send_interrupt = '''  async function sendInterrupt() {





    if (!currentConversationId || !activeStreamId) return;





    await sb.from('messages').insert({





      conversation_id: currentConversationId,





      user_id: currentUserId,





      role: 'system',





      content: '⏹️ 작업 중단',





      metadata: { type: 'interrupt', stream_id: activeStreamId, session_id: activeSessionId },





    });





    activeStreamId = null;





  }'''

new_send_interrupt = '''  async function sendInterrupt() {
    if (!currentConversationId) return;
    setWorkingState(false);
    const sid = activeStreamId;
    const sessId = activeSessionId;
    activeStreamId = null;
    await sb.from('messages').insert({
      conversation_id: currentConversationId,
      user_id: currentUserId,
      role: 'system',
      content: '⏹️ 작업 중단',
      metadata: { type: 'interrupt', stream_id: sid, session_id: sessId },
    });
  }'''

if old_send_interrupt in app:
    app = app.replace(old_send_interrupt, new_send_interrupt, 1)
    print("2.2 sendInterrupt updated")
else:
    # Try normalized match
    patt = re.compile(r"async function sendInterrupt\(\)\s*\{[\s\S]*?activeStreamId = null;\s*\}")
    m = patt.search(app)
    if m:
        app = app[:m.start()] + new_send_interrupt + app[m.end():]
        print("2.2 sendInterrupt updated via regex")
    else:
        print("WARNING: sendInterrupt not found")

# Update sendMessage
old_send_msg = '''  async function sendMessage(text, attachments) {





    if (!currentConversationId) return;'''

new_send_msg = '''  async function sendMessage(text, attachments) {
    if (!currentConversationId) return;
    setWorkingState(true);'''

if old_send_msg in app:
    app = app.replace(old_send_msg, new_send_msg, 1)
    print("2.3 sendMessage updated with setWorkingState(true)")
else:
    patt_send = re.compile(r"async function sendMessage\(text,\s*attachments\)\s*\{\s*if \(!currentConversationId\) return;")
    m_send = patt_send.search(app)
    if m_send:
        app = app[:m_send.start()] + new_send_msg + app[m_send.end():]
        print("2.3 sendMessage updated via regex")
    else:
        print("WARNING: sendMessage not found")

# Update renderMessage for status, delta, complete, notice, error
# In renderMessage:
# 1) status:
app = app.replace("if (mtype === 'status') { renderStatusBadge(row); return; }",
                  "if (mtype === 'status') { renderStatusBadge(row); setWorkingState(true); return; }")

# 2) delta:
old_delta = "if (mtype === 'delta' && row.role === 'assistant') {"
new_delta = "if (mtype === 'delta' && row.role === 'assistant') {\n      setWorkingState(true);"
app = app.replace(old_delta, new_delta, 1)

# 3) complete:
old_complete_end = "pendingAssistantEl = null;\n      activeStreamId = null;\n      return;"
new_complete_end = "pendingAssistantEl = null;\n      activeStreamId = null;\n      setWorkingState(false);\n      return;"
app = app.replace(old_complete_end, new_complete_end, 1)

# 4) approval:
old_approval = "if (mtype === 'approval') {"
new_approval = "if (mtype === 'approval') {\n      setWorkingState(true);"
app = app.replace(old_approval, new_approval, 1)

# 5) notice / error:
old_notice = "// 자율 실행 상태 동기화 (커넥터 notice)"
new_notice = '''// [v3] 취소/에러/완료 notice 시 작업 상태 해제
    if (mtype === 'notice') {
      const c = row.content || '';
      if (c.includes('취소') || c.includes('중단') || c.includes('완료')) {
        setWorkingState(false);
      }
    }
    if (mtype === 'error') {
      setWorkingState(false);
    }

    // 자율 실행 상태 동기화 (커넥터 notice)'''
app = app.replace(old_notice, new_notice, 1)

# 6) realtime DELETE event:
old_delete = '''              if (delEl) delEl.remove();





            }'''
new_delete = '''              if (delEl) delEl.remove();
            }
            setWorkingState(false);'''
if old_delete in app:
    app = app.replace(old_delete, new_delete, 1)
    print("2.4 DELETE event updated")
else:
    patt_del = re.compile(r"if \(delEl\) delEl\.remove\(\);\s*\}")
    m_del = patt_del.search(app)
    if m_del:
        app = app[:m_del.start()] + "if (delEl) delEl.remove();\n            }\n            setWorkingState(false);" + app[m_del.end():]
        print("2.4 DELETE event updated via regex")

# 7) send-form submit listener:
old_submit = "preventDefault();\n\n\n\n\n\n    const txt = $('send-input').value.trim();"
new_submit = "preventDefault();\n    if (isWorking) {\n      await sendInterrupt();\n      return;\n    }\n    const txt = $('send-input').value.trim();"

if old_submit in app:
    app = app.replace(old_submit, new_submit, 1)
    print("2.5 submit listener updated with isWorking guard")
else:
    patt_sub = re.compile(r"e\.preventDefault\(\);\s*const txt = \$\('send-input'\)\.value\.trim\(\);")
    m_sub = patt_sub.search(app)
    if m_sub:
        app = app[:m_sub.start()] + "e.preventDefault();\n    if (isWorking) {\n      await sendInterrupt();\n      return;\n    }\n    const txt = $('send-input').value.trim();" + app[m_sub.end():]
        print("2.5 submit listener updated via regex")
    else:
        print("WARNING: submit listener not found")

with open(app_path, "w", encoding="utf-8") as f:
    f.write(app)
print("app.js saved!")

# 3. Patch index.html cache-buster
v = str(int(time.time()))
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

html = re.sub(r'style\.css\?v=\d+', f'style.css?v={v}', html)
html = re.sub(r'app\.js\?v=\d+', f'app.js?v={v}', html)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"3. index.html cache-buster updated to v={v}")
