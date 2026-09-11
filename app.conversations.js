// app.conversations.js - conversation list mgmt
(function (APP) {
'use strict';

  APP.loadConversationList = async function loadConversationList() {

    if (!APP.currentUserId) return;

    const { data, error } = await APP.sb

      .from('conversations')

      .select('id, title, updated_at, created_at')

      .eq('user_id', APP.currentUserId)

      .order('updated_at', { ascending: false })

      .limit(50);

    if (error) { console.error('conv list:', error); return; }

    const box = APP.$('conv-list');

    box.innerHTML = '';

    if (!data || data.length === 0) {

      box.innerHTML = '<div class="conv-empty">대화가 없습니다</div>';

      return;

    }

    for (const c of data) {

      const el = document.createElement('div');

      el.className = 'conv-item' + (c.id === APP.currentConversationId ? ' active' : '');

      // 첫 메시지로 제목 대체 시도 (가벼운 조회)

      let title = c.title || '대화';

      if (title === '새 작업') title = '대화 ' + (c.created_at || '').slice(0, 10);

      const time = (c.updated_at || '').slice(0, 16).replace('T', ' ');

      el.innerHTML = '<div class="conv-title">' + APP.escHtml(title) + '</div><div class="conv-time">' + APP.escHtml(time) + '</div>';

      el.onclick = () => APP.switchConversation(c.id);

      box.appendChild(el);

    }

  };
  APP.toggleConvPanel = function toggleConvPanel(show) {

    const panel = APP.$('conv-list-panel');

    const force = show !== undefined ? show : panel.style.display === 'none';

    panel.style.display = force ? 'flex' : 'none';

    if (force) APP.loadConversationList();

  };
  APP.switchConversation = async function switchConversation(convId) {

    APP.currentConversationId = convId;

    APP.activeStreamId = null;

    APP.activeSessionId = null;

    APP.pendingAssistantEl = null;

    APP.toggleConvPanel(false);

    await APP.loadMessages();

    APP.subscribeMessages();

  };
  APP.newConversation = async function newConversation() {

    if (!APP.currentUserId) return;

    const { data, error } = await APP.sb

      .from('conversations')

      .insert({ user_id: APP.currentUserId, device: 'mobile', title: '새 작업' })

      .select()

      .single();

    if (error) { console.error('conv create:', error); return; }

    APP.currentConversationId = data.id;

    APP.pendingAssistantEl = null;

    APP.$('messages').innerHTML = '';

    APP.toggleConvPanel(false);

    await APP.loadMessages();

    APP.subscribeMessages();

  };
  APP.ensureConversation = async function ensureConversation() {
    // [FIX 2026-09-11] idempotent guard: 미리 설정된 conv_id 있으면 반병
    if (APP.currentConversationId) return;

    // 동시 멀티치 창단 (더볌탭/StrictMode 랴스)
    if (APP.ensureConversation._inFlight) {
      await APP.ensureConversation._inFlight;
      return;
    }
    APP.ensureConversation._inFlight = (async () => {
      const { data: existing } = await APP.sb
        .from('conversations')
        .select('id')
        .eq('user_id', APP.currentUserId)
        .order('updated_at', { ascending: false })
        .limit(1);

      if (existing && existing.length > 0) {
        APP.currentConversationId = existing[0].id;
      } else {
        const { data: created, error } = await APP.sb
          .from('conversations')
          .insert({ user_id: APP.currentUserId, device: 'mobile', title: '새 작업' })
          .select()
          .single();
        if (error) { console.error('conv create:', error); return; }
        APP.currentConversationId = created.id;
      }
    })().finally(() => {
      APP.ensureConversation._inFlight = null;
    });
    await APP.ensureConversation._inFlight;
  };
})(window.DAON_APP);

