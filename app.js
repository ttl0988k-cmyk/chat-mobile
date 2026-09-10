// app.js — 다온 모바일 작업실 v3 (DAON Remote)





// 양방향 프로토콜: prompt.submit / message.delta / message.complete





//                  approval.request → approval_response / session.interrupt





// v3: 대화 목록 전환 + 모델 선택





(function () {





  'use strict';











  const { url, anonKey } = window.SUPABASE_CONFIG;





  const sb = window.supabase.createClient(url, anonKey);











  const $ = (id) => document.getElementById(id);





  const views = {





    auth: $('auth-view'),





    chat: $('chat-view'),





  };











  let currentConversationId = null;





  let currentUserId = null;





  let activeStreamId = null;   // 중단(interrupt)에 사용





  let activeSessionId = null;  // 승인 응답에 사용





  let selectedModel = '';      // 모바일에서 선택한 모델
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
  }











  // ─────────────────────────────────────────





  // 로그인/회원가입





  // ─────────────────────────────────────────





  async function login() {





    const email = $('auth-email').value.trim();





    const password = $('auth-password').value;





    $('auth-msg').textContent = '';





    if (!email || !password) { $('auth-msg').textContent = '이메일/비번 입력'; return; }





    const { data, error } = await sb.auth.signInWithPassword({ email, password });





    if (error) { $('auth-msg').textContent = '로그인 실패: ' + error.message; return; }





    onSignedIn(data.user);





  }











  async function signup() {





    const email = $('auth-email').value.trim();





    const password = $('auth-password').value;





    $('auth-msg').textContent = '';





    if (!email || !password) { $('auth-msg').textContent = '이메일/비번 입력'; return; }





    const { data, error } = await sb.auth.signUp({ email, password });





    if (error) { $('auth-msg').textContent = '가입 실패: ' + error.message; return; }





    if (data.session) onSignedIn(data.user);





    else $('auth-msg').textContent = '가입 완료 — 이메일을 확인하세요.';





  }











  async function logout() {





    await sb.auth.signOut();





    currentConversationId = null;





    showView('auth');





  }











  // ─────────────────────────────────────────





  // 화면 전환





  // ─────────────────────────────────────────





  function showView(name) {





    Object.entries(views).forEach(([k, el]) => el.classList.toggle('active', k === name));





  }











  function onSignedIn(user) {





    currentUserId = user.id;





    $('user-email').textContent = user.email;





    showView('chat');





    loadModelList();





    ensureConversation().then(() => {



      loadMessages();



      subscribeMessages();



    });



    // [v3] 폴링 루프: 3초마다 새 메시지 확인 (승인 요청 실시간 수신)

    // [v4] 부드러운 백그라운드 동기화 (DOM innerHTML 초기화 없이 새 메시지만 갱신)
    setInterval(() => {
      if (currentConversationId && document.visibilityState !== 'hidden') {
        syncMessagesBackground();
      }
    }, 3000);




  }











  // ─────────────────────────────────────────





  // 모델 목록 (DAON 백엔드 /api/models)





  // ─────────────────────────────────────────





  async function loadModelList() {





    try {





      const sel = $('model-select');





      sel.innerHTML = '<option value="">기본 모델</option>';





      // config.js에 정의된 모델 목록 사용 (폰에서 DAON 서버 접근 불가)





      const models = (window.SUPABASE_CONFIG && window.SUPABASE_CONFIG.models) || [];





      let lastProvider = '';





      for (const m of models) {





        if (m.provider !== lastProvider) {





          const optgroup = document.createElement('optgroup');





          optgroup.label = m.provider;





          sel.appendChild(optgroup);





          lastProvider = m.provider;





        }





        const opt = document.createElement('option');





        opt.value = m.id;





        opt.textContent = m.id;





        sel.lastChild.appendChild(opt);





      }





      // localStorage에 저장된 선택 복원





      const saved = localStorage.getItem('daon_selected_model');





      if (saved && Array.from(sel.options).some(o => o.value === saved)) {





        sel.value = saved;





        selectedModel = saved;





      }





    } catch (e) {





      console.error('모델 목록 로드 실패:', e);





    }





  }











  function onModelChange() {





    selectedModel = $('model-select').value;





    try { localStorage.setItem('daon_selected_model', selectedModel); } catch (_) {}





  }











  // ─────────────────────────────────────────





  // 대화 목록





  // ─────────────────────────────────────────





  async function loadConversationList() {





    if (!currentUserId) return;





    const { data, error } = await sb





      .from('conversations')





      .select('id, title, updated_at, created_at')





      .eq('user_id', currentUserId)





      .order('updated_at', { ascending: false })





      .limit(50);





    if (error) { console.error('conv list:', error); return; }





    const box = $('conv-list');





    box.innerHTML = '';





    if (!data || data.length === 0) {





      box.innerHTML = '<div class="conv-empty">대화가 없습니다</div>';





      return;





    }





    for (const c of data) {





      const el = document.createElement('div');





      el.className = 'conv-item' + (c.id === currentConversationId ? ' active' : '');





      // 첫 메시지로 제목 대체 시도 (가벼운 조회)





      let title = c.title || '대화';





      if (title === '새 작업') title = '대화 ' + (c.created_at || '').slice(0, 10);





      const time = (c.updated_at || '').slice(0, 16).replace('T', ' ');





      el.innerHTML = '<div class="conv-title">' + escHtml(title) + '</div><div class="conv-time">' + escHtml(time) + '</div>';





      el.onclick = () => switchConversation(c.id);





      box.appendChild(el);





    }





  }











  function escHtml(s) {





    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');





  }





  // [v3] 안전 리치 렌더 — 링크 클릭 지원 (escHtml 선행으로 XSS 안전)


  function renderRichContent(el, text) {


    let s = escHtml(text || '');


    // 마크다운 링크 [text](url) 또는 URL 자동 감지 → <a>


    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s<)]+)\)|((?:https?:\/\/)[^\s<)]+)/g, function (m, mt, mu, bu) {


      if (mt !== undefined && mu !== undefined) return '<a href="' + mu + '" target="_blank" rel="noopener">' + mt + '</a>';


      if (bu) return '<a href="' + bu + '" target="_blank" rel="noopener">' + bu + '</a>';


      return m;


    });


    el.innerHTML = s.replace(/\n/g, '<br>');


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














  function toggleConvPanel(show) {





    const panel = $('conv-list-panel');





    const force = show !== undefined ? show : panel.style.display === 'none';





    panel.style.display = force ? 'flex' : 'none';





    if (force) loadConversationList();





  }











  async function switchConversation(convId) {





    currentConversationId = convId;





    activeStreamId = null;





    activeSessionId = null;





    pendingAssistantEl = null;





    toggleConvPanel(false);





    await loadMessages();





    subscribeMessages();





  }











  async function newConversation() {





    if (!currentUserId) return;





    const { data, error } = await sb





      .from('conversations')





      .insert({ user_id: currentUserId, device: 'mobile', title: '새 작업' })





      .select()





      .single();





    if (error) { console.error('conv create:', error); return; }





    currentConversationId = data.id;





    pendingAssistantEl = null;





    $('messages').innerHTML = '';





    toggleConvPanel(false);





    await loadMessages();





    subscribeMessages();





  }











  // ─────────────────────────────────────────





  // 대화 세션 (1개)





  // ─────────────────────────────────────────





  async function ensureConversation() {
    // [FIX 2026-09-11] idempotent guard: 미리 설정된 conv_id 있으면 반병
    if (currentConversationId) return;

    // 동시 멀티치 창단 (더볌탭/StrictMode 랴스)
    if (ensureConversation._inFlight) {
      await ensureConversation._inFlight;
      return;
    }
    ensureConversation._inFlight = (async () => {
      const { data: existing } = await sb
        .from('conversations')
        .select('id')
        .eq('user_id', currentUserId)
        .order('updated_at', { ascending: false })
        .limit(1);

      if (existing && existing.length > 0) {
        currentConversationId = existing[0].id;
      } else {
        const { data: created, error } = await sb
          .from('conversations')
          .insert({ user_id: currentUserId, device: 'mobile', title: '새 작업' })
          .select()
          .single();
        if (error) { console.error('conv create:', error); return; }
        currentConversationId = created.id;
      }
    })().finally(() => {
      ensureConversation._inFlight = null;
    });
    await ensureConversation._inFlight;
  }











  // ─────────────────────────────────────────





  // 메시지 송수신





  // ─────────────────────────────────────────





  async function sendMessage(text, attachments) {
    // [FIX 2026-09-11] 더브탭/StrictMode/Enter+버튼 race 창단
    if (!currentConversationId) return;

    // 동원 한 conv에 대한 in-flight Promise 가드
    if (sendMessage._inFlight) {
      console.warn('[sendMessage] 중복 호출 밀동 ❌');
      return;
    }
    sendMessage._inFlight = true;

    // 더브탭/Enter+버튼 대응: 동일 내용이 2초 이내 다시 대일 제대
    const dedupKey = (text||'') + '|' + JSON.stringify(attachments||[]);
    const now = Date.now();
    if (sendMessage._lastDedup && sendMessage._lastDedup.key === dedupKey && (now - sendMessage._lastDedup.ts) < 2000) {
      console.warn('[sendMessage] 동일 메세지 중복 (ׅ) ❌');
      sendMessage._inFlight = false;
      return;
    }
    sendMessage._lastDedup = { key: dedupKey, ts: now };

    setWorkingState(true);

    try {





      const meta = {};





      if (selectedModel) meta.model = selectedModel;  // 모델 선택 시 metadata에 전달





      if (attachments && attachments.length) {





      meta.attachments = attachments;





      meta.type = 'file';





      }





      const content = text || (attachments && attachments.length ? '📎 ' + attachments.map(a => a.name).join(', ') : '');





      if (!content) return;





      const { error } = await sb.from('messages').insert({





      conversation_id: currentConversationId,





      user_id: currentUserId,





      role: 'user',





      content: content,





      metadata: meta,





      });





      if (error) console.error('send:', error);





      else {





      $('send-input').value = '';





      sb.from('conversations')





        .update({ updated_at: new Date().toISOString(), title: content.slice(0, 40) })





        .eq('id', currentConversationId)





        .then(() => {});





      }





    } finally {
      sendMessage._inFlight = false;
    }
  }











  // ─────────────────────────────────────────





  // 파일 첨부/업로드 (chat-files 버킷, RLS: metadata.user_id 필수)





  // ─────────────────────────────────────────





  let pendingFiles = [];  // 전송 대기 중인 선택 파일











  function onAttachClick() { $('file-input').click(); }











  function onFileSelect(e) {





    const files = Array.from(e.target.files || []);





    if (!files.length) return;





    pendingFiles = pendingFiles.concat(files);





    updateAttachPreview();





    e.target.value = '';





  }











  function updateAttachPreview() {





    let bar = $('attach-preview');





    if (!bar) {





      bar = document.createElement('div');





      bar.id = 'attach-preview';





      $('send-form').insertBefore(bar, $('file-input'));





    }





    if (!pendingFiles.length) { bar.style.display = 'none'; bar.innerHTML = ''; return; }





    bar.style.display = 'flex';





    bar.innerHTML = pendingFiles.map((f, i) =>





      '<span class="attach-chip">' + escHtml(f.name).slice(0, 24) +





      ' <button type="button" data-i="' + i + '" class="attach-rm">✕</button></span>'





    ).join('');





    bar.querySelectorAll('.attach-rm').forEach(btn => {





      btn.onclick = () => { pendingFiles.splice(+btn.dataset.i, 1); updateAttachPreview(); };





    });





  }











  async function uploadFiles(files) {





    const uploaded = [];





    for (const f of files) {





      const safeName = f.name.replace(/[^\w가-힣.\-() ]/g, '_').slice(-80);





      const path = currentUserId + '/' + Date.now() + '_' + Math.random().toString(36).slice(2, 8) + '_' + safeName;





      const { error } = await sb.storage.from('chat-files').upload(path, f, {





        contentType: f.type || 'application/octet-stream',





        metadata: { user_id: currentUserId },  // RLS: metadata->>'user_id' = auth.uid()





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





  }











  function renderAttachments(wrap, attachments) {





    for (const a of attachments) {





      const isImg = /^image\//.test(a.mime || '');





      if (isImg) {





        const img = document.createElement('img');





        img.className = 'attach-img';





        img.alt = a.name;





        img.onclick = () => { if (img.src) window.open(img.src, '_blank'); };





        wrap.appendChild(img);





        sb.storage.from(a.bucket || 'chat-files').createSignedUrl(a.path, 86400)





          .then(({ data }) => { if (data) img.src = data.signedUrl; })





          .catch(() => {});





      } else {





        const link = document.createElement('a');





        link.className = 'attach-file';





        link.textContent = '📄 ' + a.name;





        link.target = '_blank';





        wrap.appendChild(link);





        sb.storage.from(a.bucket || 'chat-files').createSignedUrl(a.path, 86400)





          .then(({ data }) => { if (data) link.href = data.signedUrl; })





          .catch(() => {});





      }





    }





  }











  // 승인 응답 보내기 (approval.respond)





  async function sendApproval(approved, sessionId, reason) {





    if (!currentConversationId) return;





    await sb.from('messages').insert({





      conversation_id: currentConversationId,





      user_id: currentUserId,





      role: 'system',





      content: approved ? '✅ 승인함' : '❌ 거절함',





      metadata: { type: 'approval_response', approved: approved, session_id: sessionId, reason: reason || '' },





    });





  }











  // 작업 중단 보내기 (session.interrupt)





  async function sendInterrupt() {
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
  }











  // 자율 실행 토글 (커넥터가 승인 요청 자동 처리)


  let autoMode = false;


  function updateAutoBtn() {


    const b = document.getElementById('auto-btn');


    if (!b) return;


    b.textContent = autoMode ? '🤖' : '🛡️';


    b.classList.toggle('auto-on', autoMode);


    b.title = autoMode ? '자율 실행 ON (승인 자동 처리) — 클릭 시 일반 실행' : '일반 실행 — 클릭 시 자율 실행(승인 자동 처리)';


  }


  async function sendAutonomousToggle() {


    if (!currentConversationId) return;


    autoMode = !autoMode;


    updateAutoBtn();


    await sb.from('messages').insert({


      conversation_id: currentConversationId,


      user_id: currentUserId,


      role: 'system',


      content: autoMode ? '🤖 자율 실행 켬' : '🛡️ 자율 실행 끔',


      metadata: { type: 'autonomous_toggle', enabled: autoMode },


    });


  }





  // ─────────────────────────────────────────


  // 채팅 삭제 (확인 팝업 → messages + conversation 삭제)


  // ─────────────────────────────────────────





  function confirmClearChat() {





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





      await clearChat();





    };





  }











  async function clearChat() {





    if (!currentConversationId) return;





    const convId = currentConversationId;





    const { error: msgErr } = await sb





      .from('messages')





      .delete()





      .eq('conversation_id', convId)





      .eq('user_id', currentUserId);





    if (msgErr) { console.error('clear messages:', msgErr); alert('삭제 실패: ' + msgErr.message); return; }





    await sb.from('conversations').delete().eq('id', convId).eq('user_id', currentUserId);





    currentConversationId = null;





    activeStreamId = null;





    activeSessionId = null;





    pendingAssistantEl = null;





    $('messages').innerHTML = '';





    $('send-input').value = '';





    await ensureConversation();





    await loadMessages();





    $('messages').innerHTML = '<div class="meta" style="text-align:center;padding:24px;">새 대화를 시작하세요 ✨</div>';





    subscribeMessages();





  }











  // ─────────────────────────────────────────





  // 메시지 렌더링 (delta 누적 + 승인 버튼)





  // ─────────────────────────────────────────





  let pendingAssistantEl = null;  // delta 누적 중인 말풍선





  function createToolBadge(row) {


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


    summary.innerHTML = `<span class="tool-icon">⚙️</span> <span class="tool-name">${escHtml(name)}</span> <span class="tool-event">${escHtml(event)}</span>`;





    const body = document.createElement('pre');


    body.className = 'tool-content';


    body.textContent = content;





    details.appendChild(summary);


    details.appendChild(body);


    el.appendChild(details);


    $('messages').appendChild(el);


    return el;


  }














  function renderMessage(row) {
    // 현재 대화 소속 메시지만 렌더링 (다른 대화의 realtime INSERT 유입 차단)
    if (row.conversation_id && row.conversation_id !== currentConversationId) return;

    const meta = row.metadata || {};
    const mtype = meta.type || '';

    // [v3] 승인 요청 (mtype === 'approval') → 최우선 처리 (role=tool이어도 차단 금지)
    if (mtype === 'approval') {
      setWorkingState(true);
      pendingAssistantEl = null;
      const d = meta.data || {};
      activeStreamId = d.stream_id || activeStreamId;
      const thisSessionId = d.session_id || activeSessionId;
      activeSessionId = thisSessionId;

      if (d.status && d.status !== 'pending') {
        // 자동 승인/만료 등 이미 처리된 요청 → 읽기 전용 안내 (버튼 없음)
        createBubble('tool', row.content, true, row.id);
        scrollBottom();
        return;
      }

      let el = row.id ? document.querySelector(`.msg-row[data-msg-id="${row.id}"]`) : null;
      if (!el) {
        el = createBubble('tool', row.content, true, row.id);
        const btnWrap = document.createElement('div');
        btnWrap.className = 'approval-btns';

        const ok = document.createElement('button');
        ok.className = 'approve';
        ok.textContent = '✅ 승인';
        ok.onclick = () => {
          sendApproval(true, thisSessionId);
          ok.disabled = true;
          no.disabled = true;
        };

        const no = document.createElement('button');
        no.className = 'reject';
        no.textContent = '❌ 거절';
        no.onclick = () => {
          sendApproval(false, thisSessionId);
          ok.disabled = true;
          no.disabled = true;
        };

        btnWrap.appendChild(ok);
        btnWrap.appendChild(no);
        el.appendChild(btnWrap);
      }
      scrollBottom();
      return;
    }

    // [v3] 상태 배지 (💭 생각중… / 🔧 작업중…)
    if (mtype === 'status') { renderStatusBadge(row); setWorkingState(true); return; }

    // [v3] 일반 도구 로그(role=tool / mtype=tool) 메시지는 항상 숨김 (상태 배지로 대체)
    if (row.role === 'tool' || mtype === 'tool') return;

    // delta (스트리밍 토큰) → 누적
    if (mtype === 'delta' && row.role === 'assistant') {
      setWorkingState(true);
      if (row.metadata && row.metadata.stream_id) activeStreamId = row.metadata.stream_id;
      if (!pendingAssistantEl) {
        pendingAssistantEl = createBubble('assistant', '', false, row.id);
        pendingAssistantEl.dataset.role = 'assistant';
      }
      const dBubble = pendingAssistantEl.querySelector('.bubble');
      dBubble._raw = (dBubble._raw || '') + row.content;
      renderRichContent(dBubble, dBubble._raw);
      scrollBottom();
      return;
    }

    // complete → 완성본 표시 (커넥터가 이제 delta 조각 대신 완성본 1건만 저장)
    if (mtype === 'complete') {
      const full = (row.content || '').trim();
      if (full && full.indexOf('✅') !== 0) {
        createBubble('assistant', full, false, row.id);
        scrollBottom();
      }
      pendingAssistantEl = null;
      activeStreamId = null;
      setWorkingState(false);
      return;
    }

    // [v3] 취소/에러/완료 notice 시 작업 상태 해제
    if (mtype === 'notice') {
      const c = row.content || '';
      if (c.includes('취소') || c.includes('중단') || c.includes('완료')) {
        setWorkingState(false);
      }
    }
    if (mtype === 'error') {
      setWorkingState(false);
    }

    // 자율 실행 상태 동기화 (커넥터 notice)
    if (mtype === 'notice' && typeof meta.auto === 'boolean') {
      autoMode = meta.auto;
      updateAutoBtn();
    }

    // 첨부 파일이 있는 메시지 (이미지 인라인 / 기타 파일 링크)
    if (meta.attachments && meta.attachments.length) {
      const showText = row.content && row.content.indexOf('📎') !== 0 ? row.content : '';
      const el = createBubble(row.role, showText, row.role === 'tool', row.id);
      const wrap = document.createElement('div');
      wrap.className = 'attachments';
      el.appendChild(wrap);
      renderAttachments(wrap, meta.attachments);
      scrollBottom();
      return;
    }

    // 그 외 (user / assistant 완성 / tool / error)
    pendingAssistantEl = null;
    createBubble(row.role, row.content, row.role === 'tool', row.id);
    scrollBottom();
  }

  function createBubble(role, text, isTool, msgId) {


    const el = document.createElement('div');


    el.className = 'msg-row ' + role;


    if (msgId) el.dataset.msgId = String(msgId);


    const bubble = document.createElement('div');


    bubble.className = 'bubble';


    if (isTool) { bubble.textContent = text; } else { renderRichContent(bubble, text || ''); }


    el.appendChild(bubble);


    $('messages').appendChild(el);


    return el;


  }





  function onMessageUpdated(row) {
    if (row.conversation_id && row.conversation_id !== currentConversationId) return;

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
      if (pendingAssistantEl && (pendingAssistantEl.dataset.msgId === String(row.id) || !pendingAssistantEl.dataset.msgId)) {
        pendingAssistantEl.dataset.msgId = String(row.id);
        const bubble = pendingAssistantEl.querySelector('.bubble');
        if (bubble) { bubble._raw = row.content || ''; renderRichContent(bubble, bubble._raw); }
        scrollBottom();
      } else {
        const existing = document.querySelector(`.msg-row[data-msg-id="${row.id}"]`);
        if (existing) {
          const bubble = existing.querySelector('.bubble');
          if (bubble) { bubble._raw = row.content || ''; renderRichContent(bubble, bubble._raw); }
          scrollBottom();
        } else {
          renderMessage(row);
        }
      }
      if (mtype === 'complete') {
        pendingAssistantEl = null;
        activeStreamId = null;
      }
    }
  }

  function scrollBottom(force = false) {
    const box = $('messages');
    if (!box) return;
    // 사용자가 스크롤을 위로 올린 상태(하단에서 80px 이상 떨어진 위치)면 자동 하단 스크롤 방지
    const isNearBottom = (box.scrollHeight - box.scrollTop - box.clientHeight) < 80;
    if (force || isNearBottom) {
      box.scrollTop = box.scrollHeight;
    }
  }











  async function loadMessages(forceScroll = false) {
    if (!currentConversationId) return;

    const { data: anchors, error: aErr } = await sb
      .from('messages')
      .select('created_at')
      .eq('conversation_id', currentConversationId)
      .eq('role', 'user')
      .order('created_at', { ascending: false })
      .limit(15);

    if (aErr) { console.error('load anchors:', aErr); return; }

    let rows = [];
    if (anchors && anchors.length) {
      const cutoff = anchors[anchors.length - 1].created_at;
      const { data, error } = await sb
        .from('messages')
        .select('id, role, content, metadata, created_at, conversation_id')
        .eq('conversation_id', currentConversationId)
        .gte('created_at', cutoff)
        .order('created_at', { ascending: false })
        .limit(1000);
      if (error) { console.error('load:', error); return; }
      rows = (data || []).reverse();
    } else {
      const { data, error } = await sb
        .from('messages')
        .select('id, role, content, metadata, created_at, conversation_id')
        .eq('conversation_id', currentConversationId)
        .order('created_at', { ascending: false })
        .limit(200);
      if (error) { console.error('load:', error); return; }
      rows = (data || []).reverse();
    }

    const box = $('messages');
    box.innerHTML = '';
    pendingAssistantEl = null;

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
            createBubble('assistant', full, false, r.id);
          }
        }
        return;
      }

      if (m.type === 'complete') {
        const sid = m.stream_id;
        const merged = (sid && deltaMap[sid]) ? deltaMap[sid] : (r.content || '');
        const full = merged.trim();
        if (full && full.indexOf('✅') !== 0) createBubble('assistant', full, false, r.id);
        pendingAssistantEl = null;
        return;
      }

      renderMessage(r);
    });

    scrollBottom(forceScroll);
  }

  // [v4] 부드러운 백그라운드 동기화 (화면 깜빡임 없이 새 메시지 및 승인상태만 갱신)
  async function syncMessagesBackground() {
    if (!currentConversationId || document.visibilityState === 'hidden') return;
    try {
      const { data, error } = await sb
        .from('messages')
        .select('id, role, content, metadata, created_at, conversation_id')
        .eq('conversation_id', currentConversationId)
        .order('created_at', { ascending: false })
        .limit(20);

      if (error || !data) return;
      const recent = data.reverse();

      for (const r of recent) {
        const existing = document.querySelector(`.msg-row[data-msg-id="${r.id}"]`);
        if (existing) {
          onMessageUpdated(r);
        } else {
          // 화면에 아직 없는 신규 메시지(예: 승인 요청, 어시스턴트 발화)만 추가
          renderMessage(r);
        }
      }
    } catch (e) {
      console.warn('background sync error:', e);
    }
  }

  let messagesChannel = null;  // 현재 구독 채널 (전환 시 이전 채널 해제용)











  function subscribeMessages() {





    if (!currentConversationId) return;





    // 이전 대화 채널 해제 — 안 끊으면 이전 대화 응답이 새 화면에 계속 렌더링됨





    if (messagesChannel) {





      try { sb.removeChannel(messagesChannel); } catch (_) {}





      messagesChannel = null;





    }





    messagesChannel = sb.channel('msgs-' + currentConversationId)


      .on(


        'postgres_changes',


        { event: '*', schema: 'public', table: 'messages', filter: 'conversation_id=eq.' + currentConversationId },


        (payload) => {


          if (payload.eventType === 'INSERT') {


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
            setWorkingState(false);


          }


        }


      )


      .subscribe();





  }











  // ─────────────────────────────────────────





  // 이벤트





  // ─────────────────────────────────────────





  $('auth-login').addEventListener('click', login);





  $('auth-signup').addEventListener('click', signup);





  $('logout-btn').addEventListener('click', logout);





  $('interrupt-btn').addEventListener('click', sendInterrupt);





  const _autoBtn = document.getElementById('auto-btn');





  if (_autoBtn) _autoBtn.addEventListener('click', sendAutonomousToggle);





  $('clear-btn').addEventListener('click', confirmClearChat);





  $('model-select').addEventListener('change', onModelChange);





  $('conv-list-btn').addEventListener('click', () => toggleConvPanel());





  $('conv-close-btn').addEventListener('click', () => toggleConvPanel(false));





  $('conv-new-btn').addEventListener('click', newConversation);





  $('send-form').addEventListener('submit', async (e) => {





    e.preventDefault();
    if (isWorking) {
      await sendInterrupt();
      return;
    }
    const txt = $('send-input').value.trim();





    if (!txt && !pendingFiles.length) return;





    let attachments = [];





    if (pendingFiles.length) {





      try {





        attachments = await uploadFiles(pendingFiles);





      } catch (err) {





        console.error('upload:', err);





        alert('파일 업로드 실패: ' + (err.message || err));





        return;





      }





      pendingFiles = [];





      updateAttachPreview();





    }





    if (txt || attachments.length) { sendMessage(txt, attachments); scrollBottom(true); }





  });











  // 파일 첨부





  $('attach-btn').addEventListener('click', onAttachClick);





  $('file-input').addEventListener('change', onFileSelect);











  // 자동 로그인 확인





  sb.auth.getSession().then(({ data }) => {





    if (data.session) onSignedIn(data.session.user);





  });





  sb.auth.onAuthStateChange((_event, session) => {





    if (session && !currentUserId) onSignedIn(session.user);





  });





})();





