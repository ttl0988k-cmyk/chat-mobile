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
