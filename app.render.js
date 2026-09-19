// app.render.js - rendering + stream rows
(function (APP) {
  'use strict';

  APP.escHtml = function escHtml(s) {

    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  };
  APP.renderRichContent = function renderRichContent(el, text) {

    let s = APP.escHtml(text || '');

    // 마크다운 링크 [text](url) 또는 URL 자동 감지 → <a>

    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s<)]+)\)|((?:https?:\/\/)[^\s<)]+)/g, function (m, mt, mu, bu) {

      if (mt !== undefined && mu !== undefined) return '<a href="' + mu + '" target="_blank" rel="noopener">' + mt + '</a>';

      if (bu) return '<a href="' + bu + '" target="_blank" rel="noopener">' + bu + '</a>';

      return m;

    });

    el.innerHTML = s.replace(/\n/g, '<br>');

  };
  APP.renderStatusBadge = function renderStatusBadge(row) {

    let el = row.id ? document.querySelector('.msg-row[data-msg-id="' + row.id + '"]') : null;

    if (!el) {

      el = document.createElement('div');

      el.className = 'msg-row tool';

      if (row.id) el.dataset.msgId = String(row.id);

      const badge = document.createElement('div');

      badge.className = 'status-badge';

      badge.textContent = row.content || '💭 생각중…';

      el.appendChild(badge);

      APP.$('messages').appendChild(el);

    } else {

      const badge = el.querySelector('.status-badge');

      if (badge) badge.textContent = row.content || '';

    }

    APP.scrollBottom();

  };
  APP.createToolBadge = function createToolBadge(row) {

    const meta = row.metadata || {};

    const name = meta.name || '도구';

    const event = meta.event || '';

    const content = (row.content || '').trim();

    const el = document.createElement('div');

    el.className = 'msg-row tool';

    if (row.id) el.dataset.msgId = String(row.id);

    const details = document.createElement('details');

    details.className = 'tool-details';

    const summary = document.createElement('summary');

    summary.className = 'tool-summary';

    summary.innerHTML = `<span class="tool-icon">⚙️</span> <span class="tool-name">${APP.escHtml(name)}</span> <span class="tool-event">${APP.escHtml(event)}</span>`;

    const body = document.createElement('pre');

    body.className = 'tool-content';

    body.textContent = content;

    details.appendChild(summary);

    details.appendChild(body);

    el.appendChild(details);

    APP.$('messages').appendChild(el);

    return el;

  };

  // ══════════════════════════════════════════════════════════════
  // [2026-09-19] 승인 카드 렌더 — 브라우저 에이전트와 동일한 계약
  // ──────────────────────────────────────────────────────────────
  //  · DOM 구조/클래스명: sidepanel.js renderApprovalCard 와 100% 동일
  //    (.inline-approval-card / .approval-header / .approval-icon /
  //     .approval-title / .approval-body / .approval-command /
  //     .approval-actions / .btn-approval.approve|reject)
  //  · 자동승인(auto_approved): 기존 카드를 resolved 로 갱신 후 5초 뒤 제거
  //  · 중복 렌더 가드: "실제로 보이는" 카드가 있을 때만 스킵 (BTN-2 원칙)
  //    → 숨겨졌거나 분리된 카드 때문에 영구 미표시가 되는 문제 방지
  //  · 승인/거절 결과는 messages 테이블에 approval_response row INSERT
  //    (커넥터가 폴링 → 9090 /api/approval/respond 로 릴레이)
  // ══════════════════════════════════════════════════════════════
  APP.renderApprovalCard = function renderApprovalCard(row, d, thisSessionId) {
    d = d || {};
    const existingCard = document.getElementById('daonInlineApprovalCard');

    // ── 45초 무응답 자동 승인 → 카드 갱신 후 5초 뒤 제거 ──
    if (d.status === 'auto_approved') {
      if (existingCard) {
        existingCard.className = 'inline-approval-card resolved';
        existingCard.innerHTML =
          '<div class="approval-header">' +
          '<span class="approval-icon">✅</span>' +
          '<span class="approval-title">자동 승인됨</span>' +
          '</div>' +
          '<div class="approval-body" style="color:#34d399;">' +
          APP.escHtml(row.content || d.message || '45초 무응답으로 자동 승인되어 작업을 계속 진행합니다.') +
          '</div>';
        setTimeout(() => { if (existingCard.isConnected) existingCard.remove(); }, 5000);
      }
      return;
    }

    // ── 이미 처리된 요청(만료 등) → 읽기 전용 안내 (버튼 없음) ──
    if (d.status && d.status !== 'pending') {
      if (!existingCard) {
        const info = document.createElement('div');
        info.className = 'inline-approval-card resolved';
        info.innerHTML =
          '<div class="approval-header">' +
          '<span class="approval-icon">ℹ️</span>' +
          '<span class="approval-title">처리된 승인</span>' +
          '</div>' +
          '<div class="approval-body">' + APP.escHtml(row.content || '') + '</div>';
        APP.$('messages').appendChild(info);
      }
      return;
    }

    // ── 중복 렌더 방지: "실제로 보이는" 카드가 있을 때만 스킵 ──
    if (existingCard && existingCard.isConnected && existingCard.offsetParent !== null) return;

    const isDangerous = d.type === 'dangerous_command' || !!d.command;
    const cmd = d.command || '';
    const desc = d.description || d.message || (isDangerous ? '명령 실행을 허용할까요?' : '작업 실행 승인이 필요합니다.');

    const card = document.createElement('div');
    card.className = 'inline-approval-card';
    card.id = 'daonInlineApprovalCard';
    if (row && row.id) card.dataset.msgId = String(row.id);

    let bodyHtml = '<div class="approval-body">' + APP.escHtml(desc) + '</div>';
    if (cmd) {
      bodyHtml += '<pre class="approval-command"><code>' + APP.escHtml(cmd) + '</code></pre>';
    }

    card.innerHTML =
      '<div class="approval-header">' +
      '<span class="approval-icon">⚠️</span>' +
      '<span class="approval-title">도구 실행 승인 요청</span>' +
      '</div>' +
      bodyHtml +
      '<div class="approval-actions">' +
      '<button class="btn-approval approve" id="btnApproveAction"><span>승인 (계속 진행)</span></button>' +
      '<button class="btn-approval reject" id="btnRejectAction"><span>거부</span></button>' +
      '</div>';

    const btnApprove = card.querySelector('#btnApproveAction');
    const btnReject = card.querySelector('#btnRejectAction');

    btnApprove.addEventListener('click', async () => {
      btnApprove.disabled = true;
      btnReject.disabled = true;
      btnApprove.textContent = '승인 처리 중...';
      try {
        await APP.sendApproval(true, thisSessionId, '', isDangerous);
        card.className = 'inline-approval-card resolved';
        card.innerHTML =
          '<div class="approval-header">' +
          '<span class="approval-icon">✅</span>' +
          '<span class="approval-title">승인 완료</span>' +
          '</div>' +
          '<div class="approval-body" style="color:#34d399;">' +
          '승인이 완료되었습니다. 에이전트가 다음 작업을 계속 진행합니다.' +
          '</div>';
        setTimeout(() => { if (card.isConnected) card.remove(); }, 6000);
      } catch (err) {
        console.error('승인 처리 실패:', err);
        btnApprove.disabled = false;
        btnReject.disabled = false;
        btnApprove.textContent = '다시 승인 시도';
      }
    });

    btnReject.addEventListener('click', async () => {
      btnApprove.disabled = true;
      btnReject.disabled = true;
      btnReject.textContent = '거부 처리 중...';
      try {
        await APP.sendApproval(false, thisSessionId, '', isDangerous);
        card.className = 'inline-approval-card rejected';
        card.innerHTML =
          '<div class="approval-header">' +
          '<span class="approval-icon">❌</span>' +
          '<span class="approval-title">작업 거부됨</span>' +
          '</div>' +
          '<div class="approval-body" style="color:#f87171;">' +
          '도구 실행을 거부했습니다. 에이전트가 이를 인지하고 대안을 찾습니다.' +
          '</div>';
        setTimeout(() => { if (card.isConnected) card.remove(); }, 4000);
      } catch (err) {
        console.error('거부 처리 실패:', err);
        btnApprove.disabled = false;
        btnReject.disabled = false;
        btnReject.textContent = '다시 거부 시도';
      }
    });

    APP.$('messages').appendChild(card);
  };

  APP.renderMessage = function renderMessage(row) {
    // 현재 대화 소속 메시지만 렌더링 (다른 대화의 realtime INSERT 유입 차단)
    if (row.conversation_id && row.conversation_id !== APP.currentConversationId) return;

    const meta = row.metadata || {};
    const mtype = meta.type || '';

    // [v3] 승인 요청 (mtype === 'approval') → 최우선 처리 (role=tool이어도 차단 금지)
    // [2026-09-19] 렌더링을 브라우저 에이전트(sidepanel.js renderApprovalCard)와
    //   동일한 DOM 구조(.inline-approval-card 계열)로 통일한다.
    //   → 데스크탑 챗창 / 브라우저 에이전트 / 모바일이 같은 CSS를 공유한다.
    if (mtype === 'approval') {
      APP.setWorkingState(true);
      APP.pendingAssistantEl = null;
      const d = meta.data || {};
      APP.activeStreamId = d.stream_id || APP.activeStreamId;
      const thisSessionId = d.session_id || APP.activeSessionId;
      APP.activeSessionId = thisSessionId;

      APP.renderApprovalCard(row, d, thisSessionId);
      APP.scrollBottom();
      return;
    }

    // [v3] 상태 배지 (💭 생각중… / 🔧 작업중…)
    if (mtype === 'status') { APP.renderStatusBadge(row); APP.setWorkingState(true); return; }

    // [v3] 일반 도구 로그(role=tool / mtype=tool) 메시지는 항상 숨김 (상태 배지로 대체)
    if (row.role === 'tool' || mtype === 'tool') return;

    // delta (스트리밍 토큰) → 누적
    if (mtype === 'delta' && row.role === 'assistant') {
      APP.setWorkingState(true);
      if (row.metadata && row.metadata.stream_id) APP.activeStreamId = row.metadata.stream_id;
      if (!APP.pendingAssistantEl) {
        APP.pendingAssistantEl = APP.createBubble('assistant', '', false, row.id);
        APP.pendingAssistantEl.dataset.role = 'assistant';
      }
      const dBubble = APP.pendingAssistantEl.querySelector('.bubble');
      dBubble._raw = (dBubble._raw || '') + row.content;
      APP.renderRichContent(dBubble, dBubble._raw);
      APP.scrollBottom();
      return;
    }

    // complete → 완성본 표시 (커넥터가 이제 delta 조각 대신 완성본 1건만 저장)
    if (mtype === 'complete') {
      const full = (row.content || '').trim();
      if (full && full.indexOf('✅') !== 0) {
        APP.createBubble('assistant', full, false, row.id);
        APP.scrollBottom();
      }
      APP.pendingAssistantEl = null;
      APP.activeStreamId = null;
      APP.setWorkingState(false);
      return;
    }

    // [v3] 취소/에러/완료 notice 시 작업 상태 해제
    if (mtype === 'notice') {
      const c = row.content || '';
      if (c.includes('취소') || c.includes('중단') || c.includes('완료')) {
        APP.setWorkingState(false);
      }
    }
    if (mtype === 'error') {
      APP.setWorkingState(false);
    }

    // 자율 실행 상태 동기화 (커넥터 notice)
    if (mtype === 'notice' && typeof meta.auto === 'boolean') {
      APP.autoMode = meta.auto;
      APP.updateAutoBtn();
    }

    // 첨부 파일이 있는 메시지 (이미지 인라인 / 기타 파일 링크)
    if (meta.attachments && meta.attachments.length) {
      const showText = row.content && row.content.indexOf('📎') !== 0 ? row.content : '';
      const el = APP.createBubble(row.role, showText, row.role === 'tool', row.id);
      const wrap = document.createElement('div');
      wrap.className = 'attachments';
      el.appendChild(wrap);
      APP.renderAttachments(wrap, meta.attachments);
      APP.scrollBottom();
      return;
    }

    // 그 외 (user / assistant 완성 / tool / error)
    APP.pendingAssistantEl = null;
    APP.createBubble(row.role, row.content, row.role === 'tool', row.id);
    APP.scrollBottom();
  };
  APP.createBubble = function createBubble(role, text, isTool, msgId) {

    const el = document.createElement('div');

    el.className = 'msg-row ' + role;

    if (msgId) el.dataset.msgId = String(msgId);

    const bubble = document.createElement('div');

    bubble.className = 'bubble';

    if (isTool) { bubble.textContent = text; } else { APP.renderRichContent(bubble, text || ''); }

    el.appendChild(bubble);

    APP.$('messages').appendChild(el);

    return el;

  };
  APP.onMessageUpdated = function onMessageUpdated(row) {
    if (row.conversation_id && row.conversation_id !== APP.currentConversationId) return;

    const meta = row.metadata || {};
    const mtype = meta.type || '';

    if (mtype === 'approval') {
      // [2026-09-19] 브라우저 에이전트(sidepanel.js)와 동일한 카드 구조로 갱신.
      //   자동승인(auto_approved)이면 카드를 resolved 로 바꾸고 5초 뒤 제거한다.
      const d = meta.data || {};
      const thisSessionId = d.session_id || APP.activeSessionId;
      APP.renderApprovalCard(row, d, thisSessionId);
      return;
    }

    if (mtype === 'delta' || mtype === 'complete') {
      if (APP.pendingAssistantEl && (APP.pendingAssistantEl.dataset.msgId === String(row.id) || !APP.pendingAssistantEl.dataset.msgId)) {
        APP.pendingAssistantEl.dataset.msgId = String(row.id);
        const bubble = APP.pendingAssistantEl.querySelector('.bubble');
        if (bubble) { bubble._raw = row.content || ''; APP.renderRichContent(bubble, bubble._raw); }
        APP.scrollBottom();
      } else {
        const existing = document.querySelector(`.msg-row[data-msg-id="${row.id}"]`);
        if (existing) {
          const bubble = existing.querySelector('.bubble');
          if (bubble) { bubble._raw = row.content || ''; APP.renderRichContent(bubble, bubble._raw); }
          APP.scrollBottom();
        } else {
          APP.renderMessage(row);
        }
      }
      if (mtype === 'complete') {
        APP.pendingAssistantEl = null;
        APP.activeStreamId = null;
      }
    }
  };
  APP.scrollBottom = function scrollBottom(force = false) {
    const box = APP.$('messages');
    if (!box) return;
    // 사용자가 스크롤을 위로 올린 상태(하단에서 80px 이상 떨어진 위치)면 자동 하단 스크롤 방지
    const isNearBottom = (box.scrollHeight - box.scrollTop - box.clientHeight) < 80;
    if (force || isNearBottom) {
      box.scrollTop = box.scrollHeight;
    }
  };
  APP.loadMessages = async function loadMessages(forceScroll = false) {
    if (!APP.currentConversationId) return;

    const { data: anchors, error: aErr } = await APP.sb
      .from('messages')
      .select('created_at')
      .eq('conversation_id', APP.currentConversationId)
      .eq('role', 'user')
      .order('created_at', { ascending: false })
      .limit(15);

    if (aErr) { console.error('load anchors:', aErr); return; }

    let rows = [];
    if (anchors && anchors.length) {
      const cutoff = anchors[anchors.length - 1].created_at;
      const { data, error } = await APP.sb
        .from('messages')
        .select('id, role, content, metadata, created_at, conversation_id')
        .eq('conversation_id', APP.currentConversationId)
        .gte('created_at', cutoff)
        .order('created_at', { ascending: false })
        .limit(1000);
      if (error) { console.error('load:', error); return; }
      rows = (data || []).reverse();
    } else {
      const { data, error } = await APP.sb
        .from('messages')
        .select('id, role, content, metadata, created_at, conversation_id')
        .eq('conversation_id', APP.currentConversationId)
        .order('created_at', { ascending: false })
        .limit(200);
      if (error) { console.error('load:', error); return; }
      rows = (data || []).reverse();
    }

    const box = APP.$('messages');
    box.innerHTML = '';
    APP.pendingAssistantEl = null;

    // 히스토리 렌더:
    // 1) delta 토큰 조각 병합
    // 2) complete가 존재하는 스트림 파악
    const deltaMap = {};
    const completedStreamIds = new Set();
    rows.forEach(r => {
      const m = r.metadata || {};
      if (m.type === 'delta' && r.role === 'assistant') {
        const sid = m.stream_id || r.id || '_none';
        if (!deltaMap[sid]) deltaMap[sid] = '';
        deltaMap[sid] += (r.content || '');
      }
      if (m.type === 'complete' && m.stream_id) {
        completedStreamIds.add(m.stream_id);
      }
    });

    const uncompletedRendered = new Set();
    rows.forEach(r => {
      const m = r.metadata || {};

      // [핵심] complete가 없는 스트림(승인 대기 중 등)은 delta 내용을 반드시 렌더링!
      if (m.type === 'delta') {
        const sid = m.stream_id || r.id || '_none';
        if (completedStreamIds.has(sid)) return;
        if (!uncompletedRendered.has(sid)) {
          uncompletedRendered.add(sid);
          const full = (deltaMap[sid] || r.content || '').trim();
          if (full && full.indexOf('✅') !== 0) {
            APP.createBubble('assistant', full, false, r.id);
          }
        }
        return;
      }

      if (m.type === 'complete') {
        const sid = m.stream_id;
        const merged = (sid && deltaMap[sid]) ? deltaMap[sid] : (r.content || '');
        const full = merged.trim();
        if (full && full.indexOf('✅') !== 0) APP.createBubble('assistant', full, false, r.id);
        APP.pendingAssistantEl = null;
        return;
      }

      APP.renderMessage(r);
    });

    APP.scrollBottom(forceScroll);
  };
  APP.syncMessagesBackground = async function syncMessagesBackground() {
    if (!APP.currentConversationId || document.visibilityState === 'hidden') return;
    try {
      const { data, error } = await APP.sb
        .from('messages')
        .select('id, role, content, metadata, created_at, conversation_id')
        .eq('conversation_id', APP.currentConversationId)
        .order('created_at', { ascending: false })
        .limit(20);

      if (error || !data) return;
      const recent = data.reverse();

      for (const r of recent) {
        const existing = document.querySelector(`.msg-row[data-msg-id="${r.id}"]`);
        if (existing) {
          APP.onMessageUpdated(r);
        } else {
          // 화면에 아직 없는 신규 메시지(예: 승인 요청, 어시스턴트 발화)만 추가
          APP.renderMessage(r);
        }
      }
    } catch (e) {
      console.warn('background sync error:', e);
    }
  };
  APP.subscribeMessages = function subscribeMessages() {

    if (!APP.currentConversationId) return;

    // 이전 대화 채널 해제 — 안 끊으면 이전 대화 응답이 새 화면에 계속 렌더링됨

    if (APP.messagesChannel) {

      try { APP.sb.removeChannel(APP.messagesChannel); } catch (_) { }

      APP.messagesChannel = null;

    }

    APP.messagesChannel = APP.sb.channel('msgs-' + APP.currentConversationId)

      .on(

        'postgres_changes',

        { event: '*', schema: 'public', table: 'messages', filter: 'conversation_id=eq.' + APP.currentConversationId },

        (payload) => {

          if (payload.eventType === 'INSERT') {

            APP.renderMessage(payload.new);

          } else if (payload.eventType === 'UPDATE') {

            APP.onMessageUpdated(payload.new);

          } else if (payload.eventType === 'DELETE') {

            // [v3] 상태 배지 row 삭제 → 화면에서도 제거

            const delId = payload.old && payload.old.id;

            if (delId) {

              const delEl = document.querySelector('.msg-row[data-msg-id="' + delId + '"]');

              if (delEl) delEl.remove();
            }
            APP.setWorkingState(false);

          }

        }

      )

      .subscribe();

  };
})(window.DAON_APP);

