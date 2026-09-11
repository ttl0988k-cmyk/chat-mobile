// app.init.js - event bindings + auto-login
// [FIX 2026-09-12] APP.APP._autoBtn 오타로 init 전체가 중단되던 버그 수정.
//   ▸ 기존: APP.APP._autoBtn = ...  → APP.APP 이 undefined → TypeError →
//     이후 model-select / loadModelList / send-form / conv-* 바인딩이 전부 실행 안 됨
//     (증상: 모델 목록 0개, 전송·대화목록 버튼 무반응)
//   ▸ 조치: 안전 바인딩 헬퍼(bind)로 교체 — 요소/함수 하나가 없어도 나머지는 정상 바인딩
(function (APP) {
'use strict';

  // ── 안전 바인딩 헬퍼 ──────────────────────────
  function bind(id, ev, fn) {
    const el = APP.$(id);
    if (!el) { console.warn('[init] 요소 없음:', id); return false; }
    if (typeof fn !== 'function') { console.warn('[init] 핸들러 없음:', id, ev); return false; }
    el.addEventListener(ev, fn);
    return true;
  }

  // ── 이벤트 바인딩 ─────────────────────────────
  bind('auth-login',    'click', APP.login);
  bind('logout-btn',    'click', APP.logout);
  bind('interrupt-btn', 'click', APP.sendInterrupt);

  // 자율모드 버튼 (과거 APP.APP._autoBtn 오타로 여기서 init이 죽었음)
  APP._autoBtn = document.getElementById('auto-btn');
  if (APP._autoBtn && typeof APP.sendAutonomousToggle === 'function') {
    APP._autoBtn.addEventListener('click', APP.sendAutonomousToggle);
  }

  bind('clear-btn', 'click', APP.confirmClearChat);

  bind('model-select', 'change', APP.onModelChange);

  // 초기 모델 목록 즉시 로드 (config.js / 캐시 기준)
  try {
    if (typeof APP.loadModelList === 'function') APP.loadModelList();
  } catch (e) { console.error('[init] loadModelList 실패:', e); }

  // ── 대화 목록 패널 ────────────────────────────
  bind('conv-list-btn',  'click', () => APP.toggleConvPanel());
  bind('conv-close-btn', 'click', () => APP.toggleConvPanel(false));
  bind('conv-new-btn',   'click', APP.newConversation);

  // ── 메시지 전송 ───────────────────────────────
  bind('send-form', 'submit', async (e) => {
    e.preventDefault();
    if (APP.isWorking) {
      await APP.sendInterrupt();
      return;
    }
    const txt = (APP.$('send-input').value || '').trim();
    if (!txt && !APP.pendingFiles.length) return;

    let attachments = [];
    if (APP.pendingFiles.length) {
      try {
        attachments = await APP.uploadFiles(APP.pendingFiles);
      } catch (err) {
        console.error('upload:', err);
        alert('파일 업로드 실패: ' + (err.message || err));
        return;
      }
      APP.pendingFiles = [];
      APP.updateAttachPreview();
    }
    if (txt || attachments.length) { APP.sendMessage(txt, attachments); APP.scrollBottom(true); }
  });

  // [FIX 2026-09-11] 모바일: Enter = 줄바꿈 (전송은 버튼) / 데스크톱: Enter = 전송, Shift+Enter = 줄바꿈
  const isTouch = window.matchMedia('(pointer: coarse)').matches;
  bind('send-input', 'keydown', (e) => {
    if (e.key !== 'Enter') return;
    if (isTouch) return;  // 모바일: 개행 자유, 전송은 [전송] 버튼
    if (!e.shiftKey) {
      e.preventDefault();
      const form = APP.$('send-form');
      if (form && typeof form.requestSubmit === 'function') form.requestSubmit();
      else { const b = APP.$('send-btn'); if (b) b.click(); }
    }
  });

  // ── 파일 첨부 ─────────────────────────────────
  bind('attach-btn', 'click', APP.onAttachClick);
  bind('file-input', 'change', APP.onFileSelect);

  // ── 자동 로그인 확인 ──────────────────────────
  try {
    APP.sb.auth.getSession().then(({ data }) => {
      if (data && data.session) APP.onSignedIn(data.session.user);
    });
    APP.sb.auth.onAuthStateChange((_event, session) => {
      if (session && !APP.currentUserId) APP.onSignedIn(session.user);
    });
  } catch (e) { console.error('[init] auth 초기화 실패:', e); }

  // ── 안전망: 모델 목록이 비어 있으면 config 기준으로 재시도 ──
  function ensureModels(tries) {
    const sel = APP.$('model-select');
    if (sel && sel.options.length > 1) return;            // 정상
    if (tries <= 0) return;
    try {
      const g = window.SUPABASE_CONFIG && window.SUPABASE_CONFIG.modelGroups;
      if (g && g.length) {
        APP.renderModelOptions(g);
        if (APP.$('model-select').options.length > 1) return;
      }
    } catch (e) { console.warn('[init] ensureModels 실패:', e); }
    setTimeout(() => ensureModels(tries - 1), 700);
  }
  setTimeout(() => ensureModels(6), 300);

})(window.DAON_APP);
