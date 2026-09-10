# -*- coding: utf-8 -*-
"""patch_app5.py — 모바일 앱 v3 패치 (2026-09-04)
1) renderRichContent: 링크 클릭 가능 (마크다운/URL 자동 <a>)
2) renderStatusBadge: 💭 생각중… / 🔧 작업중… 미니 배지
3) 도구 로그 row 렌더 스킵
4) Realtime DELETE 이벤트 → 배지 소멸
5) delta/complete 렌더 전부 리치 렌더로 통일
"""
import io, sys

PATH = r'C:\daon\cafe\LLM\chat\app.js'

with io.open(PATH, 'r', encoding='utf-8', newline='') as f:
    raw = f.read()

content = raw.replace('\r\r\n', '\n').replace('\r\n', '\n').replace('\r', '\n')

R = []

NEW_FUNCS = """  // [v3] 안전 리치 렌더 — 링크 클릭 지원 (escHtml 선행으로 XSS 안전)
  function renderRichContent(el, text) {
    let s = escHtml(text || '');
    // 마크다운 링크 [text](url) 또는 URL 자동 감지 → <a>
    s = s.replace(/\\[([^\\]]+)\\]\\((https?:\\/\\/[^\\s<)]+)\\)|((?:https?:\\/\\/)[^\\s<)]+)/g, function (m, mt, mu, bu) {
      if (mt !== undefined && mu !== undefined) return '<a href="' + mu + '" target="_blank" rel="noopener">' + mt + '</a>';
      if (bu) return '<a href="' + bu + '" target="_blank" rel="noopener">' + bu + '</a>';
      return m;
    });
    el.innerHTML = s.replace(/\\n/g, '<br>');
  }

  // [v3] 상태 배지 (💭 생각중… / 🔧 작업중…)
  function renderStatusBadge(row) {
    let el = row.id ? document.querySelector('.msg-row[data-msg-id="' + row.id + '"]') : null;
    if (!el) {
      el = document.createElement('div');
      el.className = 'msg-row tool';
      if (row.id) el.dataset.msgId = String(row.id);
      const badge = document.createElement('div');
      badge.className = 'status-badge';
      badge.textContent = row.content || '💭 생각중…';
      el.appendChild(badge);
      $('messages').appendChild(el);
    } else {
      const badge = el.querySelector('.status-badge');
      if (badge) badge.textContent = row.content || '';
    }
    scrollBottom();
  }
"""

R.append((
"    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\"/g, '&quot;');\n\n  }",
"    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\"/g, '&quot;');\n\n  }\n\n" + NEW_FUNCS))

R.append((
"    if (row.conversation_id && row.conversation_id !== currentConversationId) return;\n\n    const meta = row.metadata || {};\n\n    const mtype = meta.type || '';\n",
"    if (row.conversation_id && row.conversation_id !== currentConversationId) return;\n\n    const meta = row.metadata || {};\n\n    const mtype = meta.type || '';\n\n    // [v3] 도구 로그는 모바일에 표시하지 않음 (상태 배지로 대체)\n\n    if (mtype === 'tool') return;\n\n    // [v3] 상태 배지 (💭 생각중… / 🔧 작업중…)\n\n    if (mtype === 'status') { renderStatusBadge(row); return; }\n"))

R.append((
"      pendingAssistantEl.querySelector('.bubble').textContent += row.content;\n",
"      const dBubble = pendingAssistantEl.querySelector('.bubble');\n      dBubble._raw = (dBubble._raw || '') + row.content;\n      renderRichContent(dBubble, dBubble._raw);\n"))

R.append((
"        const bubble = pendingAssistantEl.querySelector('.bubble');\n        if (bubble) bubble.textContent = row.content || '';\n",
"        const bubble = pendingAssistantEl.querySelector('.bubble');\n        if (bubble) { bubble._raw = row.content || ''; renderRichContent(bubble, bubble._raw); }\n"))

R.append((
"          const bubble = existing.querySelector('.bubble');\n          if (bubble) bubble.textContent = row.content || '';\n",
"          const bubble = existing.querySelector('.bubble');\n          if (bubble) { bubble._raw = row.content || ''; renderRichContent(bubble, bubble._raw); }\n"))

R.append((
"    const bubble = document.createElement('div');\n    bubble.className = 'bubble';\n    bubble.textContent = text;\n    el.appendChild(bubble);\n",
"    const bubble = document.createElement('div');\n    bubble.className = 'bubble';\n    if (isTool) { bubble.textContent = text; } else { renderRichContent(bubble, text || ''); }\n    el.appendChild(bubble);\n"))

R.append((
"          if (payload.eventType === 'INSERT') {\n            renderMessage(payload.new);\n          } else if (payload.eventType === 'UPDATE') {\n            onMessageUpdated(payload.new);\n          }\n",
"""          if (payload.eventType === 'INSERT') {
            renderMessage(payload.new);
          } else if (payload.eventType === 'UPDATE') {
            onMessageUpdated(payload.new);
          } else if (payload.eventType === 'DELETE') {
            // [v3] 상태 배지 row 삭제 → 화면에서도 제거
            const delId = payload.old && payload.old.id;
            if (delId) {
              const delEl = document.querySelector('.msg-row[data-msg-id="' + delId + '"]');
              if (delEl) delEl.remove();
            }
          }
"""))

ok, fail = 0, 0
for i, (old, new) in enumerate(R, 1):
    n = content.count(old)
    if n == 0 and new in content:
        print(f'[{i:02d}] SKIP (already applied)')
        ok += 1
        continue
    if n != 1:
        print(f'[{i:02d}] FAIL (count={n}) :: {old[:60]!r}')
        fail += 1
        continue
    content = content.replace(old, new)
    ok += 1
    print(f'[{i:02d}] OK')

if fail:
    print(f'\n❌ {fail}개 교체 실패 — 파일 미저장')
    sys.exit(1)

content = content.replace('\n', '\r\n')

with io.open(PATH, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print(f'\n✅ app.js 패치 저장 완료 ({ok}/{len(R)})')
