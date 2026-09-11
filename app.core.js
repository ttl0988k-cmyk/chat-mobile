// app.core.js - namespace/state/helpers (2026-09-11)

window.DAON_APP = window.DAON_APP || {};

(function (APP) {

'use strict';



  const { url, anonKey } = window.SUPABASE_CONFIG;

  APP.sb = window.supabase.createClient(url, anonKey);

  APP.$ = (id) => document.getElementById(id);

  APP.views = { auth: APP.$('auth-view'), chat: APP.$('chat-view') };



  APP.currentConversationId = null;

  APP.currentUserId = null;

  APP.activeStreamId = null;

  APP.activeSessionId = null;

  APP.selectedModel = '';

  APP.isWorking = false;

  // ── [FIX 2026-09-12] 리팩토링 누락 상태변수 복원 ──────────────
  //   legacy(app.js)에는 있었지만 모듈 분리 시 빠졌던 것들.
  //   특히 pendingFiles 가 undefined 이면 전송 핸들러의
  //   `!APP.pendingFiles.length` 에서 TypeError 가 나서
  //   메시지를 보내도 렌더링/전송이 통째로 실패한다.
  APP.pendingFiles = [];          // 전송 대기 중인 선택 파일 (legacy L618)
  APP.autoMode = false;           // 자율모드 플래그 (legacy L799)
  APP.pendingAssistantEl = null;  // delta 누적 중인 말풍선 (legacy L933)
  APP.messagesChannel = null;     // 현재 구독 채널 (legacy L1294)





  function setWorkingState(working) {
    APP.isWorking = !!working;
    const btn = $('send-btn');
    const input = $('send-input');
    if (!btn) return;
    if (APP.isWorking) {
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
  };

})(window.DAON_APP);
