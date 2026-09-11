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
  APP.renderMessage = function renderMessage(row) {
    // 현재 대화 소속 메시지만 렌더링 (다른 대화의 realtime INSERT 유입 차단)
    if (row.conversation_id && row.conversation_id !== APP.currentConversationId) return;

    const meta = row.metadata || {};
    const mtype = meta.type || '';

    // [v3] 승인 요청 (mtype === 'approval') → 최우선 처리 (role=tool이어도 차단 금지)
    if (mtype === 'approval') {
      APP.setWorkingState(true);
      APP.pendingAssistantEl = null;
      const d = meta.data || {};
      APP.activeStreamId = d.stream_id || APP.activeStreamId;
      const thisSessionId = d.session_id || APP.activeSessionId;
      APP.activeSessionId = thisSessionId;

      if (d.status && d.status !== 'pending') {
        // 자동 승인/만료 등 이미 처리된 요청 → 읽기 전용 안내 (버튼 없음)
        APP.createBubble('tool', row.content, true, row.id);
        APP.scrollBottom();
        return;
      }

      let el = row.id ? document.querySelector(`.msg-row[data-msg-id="${row.id}"]`) : null;
      if (!el) {
        el = APP.createBubble('tool', row.content, true, row.id);
        const btnWrap = document.createElement('div');
        btnWrap.className = 'approval-btns';

        const ok = document.createElement('button');
        ok.className = 'approve';
        ok.textContent = '✅ 승인';
        ok.onclick = () => {
          APP.sendApproval(true, thisSessionId);
          ok.disabled = true;
          no.disabled = true;
        };

        const no = document.createElement('button');
        no.className = 'reject';
        no.textContent = '❌ 거절';
        no.onclick = () => {
          APP.sendApproval(false, thisSessionId);
          ok.disabled = true;
          no.disabled = true;
        };

        btnWrap.appendChild(ok);
        btnWrap.appendChild(no);
        el.appendChild(btnWrap);
      }
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
      const existing = document.querySelector(`.msg-row[data-msg-id="${row.id}"]`);
      if (existing) {
        const d = meta.data || {};
        if (d.status && d.status !== 'pending') {
          const btns = existing.querySelector('.approval-btns');
          if (btns) btns.remove();
        }
      }
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

      try { APP.sb.removeChannel(APP.messagesChannel); } catch (_) {}

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

