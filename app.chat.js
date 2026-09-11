// app.chat.js - send/approval/interrupt
(function (APP) {
'use strict';

  APP.sendMessage = async function sendMessage(text, attachments) {
    // [FIX 2026-09-12] 대화가 아직 없으면 먼저 확보한다.
    //   legacy(app.js L917)에는 sendMessage 진입 시 ensureConversation() 을 호출했는데
    //   리팩토링 때 이 호출이 빠졌다. 그 결과 conv_id 가 null 이면 곧바로 return 되어
    //   메시지를 보내도 아무 일도 일어나지 않았다(전송·렌더 전면 불능).
    if (!APP.currentConversationId && typeof APP.ensureConversation === 'function') {
      try { await APP.ensureConversation(); }
      catch (e) { console.error('[sendMessage] ensureConversation 실패:', e); }
    }
    if (!APP.currentConversationId) return;

    // 동원 한 conv에 대한 in-flight Promise 가드
    if (APP.sendMessage._inFlight) {
      console.warn('[APP.sendMessage] 중복 호출 밀동 ❌');
      return;
    }
    APP.sendMessage._inFlight = true;

    // 더브탭/Enter+버튼 대응: 동일 내용이 2초 이내 다시 대일 제대
    const dedupKey = (text||'') + '|' + JSON.stringify(attachments||[]);
    const now = Date.now();
    if (APP.sendMessage._lastDedup && APP.sendMessage._lastDedup.key === dedupKey && (now - APP.sendMessage._lastDedup.ts) < 2000) {
      console.warn('[APP.sendMessage] 동일 메세지 중복 (ׅ) ❌');
      APP.sendMessage._inFlight = false;
      return;
    }
    APP.sendMessage._lastDedup = { key: dedupKey, ts: now };

    APP.setWorkingState(true);

    try {

      const meta = {};

      if (APP.selectedModel) meta.model = APP.selectedModel;  // 모델 선택 시 metadata에 전달

      if (attachments && attachments.length) {

      meta.attachments = attachments;

      meta.type = 'file';

      }

      const content = text || (attachments && attachments.length ? '📎 ' + attachments.map(a => a.name).join(', ') : '');

      if (!content) return;

      const { error } = await APP.sb.from('messages').insert({

      conversation_id: APP.currentConversationId,

      user_id: APP.currentUserId,

      role: 'user',

      content: content,

      metadata: meta,

      });

      if (error) {
        console.error('send:', error);
        APP.setWorkingState(false);
        alert('메시지 전송 실패: ' + (error.message || JSON.stringify(error)));
      } else {
        APP.$('send-input').value = '';
        APP.sb.from('conversations')
          .update({ updated_at: new Date().toISOString(), title: content.slice(0, 40) })
          .eq('id', APP.currentConversationId)
          .then(() => {});
      }

    } finally {
      APP.sendMessage._inFlight = false;
    }
  };
  APP.onAttachClick = function onAttachClick() { APP.$('file-input').click(); }
;
  APP.onFileSelect = function onFileSelect(e) {

    const files = Array.from(e.target.files || []);

    if (!files.length) return;

    APP.pendingFiles = APP.pendingFiles.concat(files);

    APP.updateAttachPreview();

    e.target.value = '';

  };
  APP.updateAttachPreview = function updateAttachPreview() {

    let bar = APP.$('attach-preview');

    if (!bar) {

      bar = document.createElement('div');

      bar.id = 'attach-preview';

      APP.$('send-form').insertBefore(bar, APP.$('file-input'));

    }

    if (!APP.pendingFiles.length) { bar.style.display = 'none'; bar.innerHTML = ''; return; }

    bar.style.display = 'flex';

    bar.innerHTML = APP.pendingFiles.map((f, i) =>

      '<span class="attach-chip">' + APP.escHtml(f.name).slice(0, 24) +

      ' <button type="button" data-i="' + i + '" class="attach-rm">✕</button></span>'

    ).join('');

    bar.querySelectorAll('.attach-rm').forEach(btn => {

      btn.onclick = () => { APP.pendingFiles.splice(+btn.dataset.i, 1); APP.updateAttachPreview(); };

    });

  };
  APP.uploadFiles = async function uploadFiles(files) {

    const uploaded = [];

    for (const f of files) {

      const safeName = f.name.replace(/[^\w가-힣.\-() ]/g, '_').slice(-80);

      const path = APP.currentUserId + '/' + Date.now() + '_' + Math.random().toString(36).slice(2, 8) + '_' + safeName;

      const { error } = await APP.sb.storage.from('chat-files').upload(path, f, {

        contentType: f.type || 'application/octet-stream',

        metadata: { user_id: APP.currentUserId },  // RLS: metadata->>'user_id' = auth.uid()

      });

      if (error) throw error;

      uploaded.push({

        bucket: 'chat-files',

        path: path,

        name: f.name,

        mime: f.type || 'application/octet-stream',

        size: f.size,

      });

    }

    return uploaded;

  };
  APP.renderAttachments = function renderAttachments(wrap, attachments) {

    for (const a of attachments) {

      const isImg = /^image\//.test(a.mime || '');

      if (isImg) {

        const img = document.createElement('img');

        img.className = 'attach-img';

        img.alt = a.name;

        img.onclick = () => { if (img.src) window.open(img.src, '_blank'); };

        wrap.appendChild(img);

        APP.sb.storage.from(a.bucket || 'chat-files').createSignedUrl(a.path, 86400)

          .then(({ data }) => { if (data) img.src = data.signedUrl; })

          .catch(() => {});

      } else {

        const link = document.createElement('a');

        link.className = 'attach-file';

        link.textContent = '📄 ' + a.name;

        link.target = '_blank';

        wrap.appendChild(link);

        APP.sb.storage.from(a.bucket || 'chat-files').createSignedUrl(a.path, 86400)

          .then(({ data }) => { if (data) link.href = data.signedUrl; })

          .catch(() => {});

      }

    }

  };
  APP.sendApproval = async function sendApproval(approved, sessionId, reason) {

    if (!APP.currentConversationId) return;

    await APP.sb.from('messages').insert({

      conversation_id: APP.currentConversationId,

      user_id: APP.currentUserId,

      role: 'system',

      content: approved ? '✅ 승인함' : '❌ 거절함',

      metadata: { type: 'approval_response', approved: approved, session_id: sessionId, reason: reason || '' },

    });

  };
  APP.sendInterrupt = async function sendInterrupt() {
    if (!APP.currentConversationId) return;
    APP.setWorkingState(false);
    const sid = APP.activeStreamId;
    const sessId = APP.activeSessionId;
    APP.activeStreamId = null;
    await APP.sb.from('messages').insert({
      conversation_id: APP.currentConversationId,
      user_id: APP.currentUserId,
      role: 'system',
      content: '⏹️ 작업 중단',
      metadata: { type: 'interrupt', stream_id: sid, session_id: sessId },
    });
  };
  APP.updateAutoBtn = function updateAutoBtn() {

    const b = document.getElementById('auto-btn');

    if (!b) return;

    b.textContent = APP.autoMode ? '🤖' : '🛡️';

    b.classList.toggle('auto-on', APP.autoMode);

    b.title = APP.autoMode ? '자율 실행 ON (승인 자동 처리) — 클릭 시 일반 실행' : '일반 실행 — 클릭 시 자율 실행(승인 자동 처리)';

  };
  APP.sendAutonomousToggle = async function sendAutonomousToggle() {

    if (!APP.currentConversationId) return;

    APP.autoMode = !APP.autoMode;

    APP.updateAutoBtn();

    await APP.sb.from('messages').insert({

      conversation_id: APP.currentConversationId,

      user_id: APP.currentUserId,

      role: 'system',

      content: APP.autoMode ? '🤖 자율 실행 켬' : '🛡️ 자율 실행 끔',

      metadata: { type: 'autonomous_toggle', enabled: APP.autoMode },

    });

  };
  APP.confirmClearChat = function confirmClearChat() {

    if (document.querySelector('.confirm-overlay')) return;

    const overlay = document.createElement('div');

    overlay.className = 'confirm-overlay';

    overlay.innerHTML =

      '<div class="confirm-box">' +

      '<div class="confirm-title">🗑️ 채팅을 삭제할까요?</div>' +

      '<div class="confirm-text">이 대화의 모든 메시지가 삭제되고,<br>새 대화로 시작됩니다.</div>' +

      '<div class="confirm-actions">' +

      '<button class="ghost" id="confirm-no">취소</button>' +

      '<button class="primary" id="confirm-yes" style="background:var(--danger);">삭제</button>' +

      '</div>' +

      '</div>';

    document.body.appendChild(overlay);

    overlay.querySelector('#confirm-no').onclick = () => overlay.remove();

    overlay.querySelector('#confirm-yes').onclick = async () => {

      overlay.remove();

      await APP.clearChat();

    };

  };
  APP.clearChat = async function clearChat() {

    if (!APP.currentConversationId) return;

    const convId = APP.currentConversationId;

    const { error: msgErr } = await APP.sb

      .from('messages')

      .delete()

      .eq('conversation_id', convId)

      .eq('user_id', APP.currentUserId);

    if (msgErr) { console.error('clear messages:', msgErr); alert('삭제 실패: ' + msgErr.message); return; }

    await APP.sb.from('conversations').delete().eq('id', convId).eq('user_id', APP.currentUserId);

    APP.currentConversationId = null;

    APP.activeStreamId = null;

    APP.activeSessionId = null;

    APP.pendingAssistantEl = null;

    APP.$('messages').innerHTML = '';

    APP.$('send-input').value = '';

    await APP.ensureConversation();

    await APP.loadMessages();

    APP.$('messages').innerHTML = '<div class="meta" style="text-align:center;padding:24px;">새 대화를 시작하세요 ✨</div>';

    APP.subscribeMessages();

  };
})(window.DAON_APP);

