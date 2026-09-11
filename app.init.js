// app.init.js - event bindings + auto-login
(function (APP) {
'use strict';


  // ─────────────────────────────────────────

  // 이벤트

  // ─────────────────────────────────────────

  APP.$('auth-APP.login').addEventListener('click', APP.login);

  APP.$('auth-APP.signup').addEventListener('click', APP.signup);

  APP.$('APP.logout-btn').addEventListener('click', APP.logout);

  APP.$('interrupt-btn').addEventListener('click', APP.sendInterrupt);

  APP.APP._autoBtn = document.getElementById('auto-btn');

  if (APP._autoBtn) APP._autoBtn.addEventListener('click', APP.sendAutonomousToggle);

  APP.$('clear-btn').addEventListener('click', APP.confirmClearChat);

  APP.$('model-select').addEventListener('change', APP.onModelChange);
  // 초기 모델 목록 즉시 로드 (config.js / 캐시 기준)
  APP.loadModelList();


  APP.$('conv-list-btn').addEventListener('click', () => APP.toggleConvPanel());

  APP.$('conv-close-btn').addEventListener('click', () => APP.toggleConvPanel(false));

  APP.$('conv-new-btn').addEventListener('click', APP.newConversation);

  APP.$('send-form').addEventListener('submit', async (e) => {

    e.preventDefault();
    if (APP.isWorking) {
      await APP.sendInterrupt();
      return;
    }
    const txt = APP.$('send-input').value.trim();

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
  APP.$('send-input').addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    if (isTouch) return;  // 모바일: 개행 자유, 전송은 [전송] 버튼
    if (!e.shiftKey) {
      e.preventDefault();
      if (typeof APP.$('send-form').requestSubmit === 'function') {
        APP.$('send-form').requestSubmit();
      } else {
        APP.$('send-btn').click();
      }
    }
  });


  // 파일 첨부

  APP.$('attach-btn').addEventListener('click', APP.onAttachClick);

  APP.$('file-input').addEventListener('change', APP.onFileSelect);

  // 자동 로그인 확인

  APP.sb.auth.getSession().then(({ data }) => {

    if (data.session) APP.onSignedIn(data.session.user);

  });

  APP.sb.auth.onAuthStateChange((_event, session) => {

    if (session && !APP.currentUserId) APP.onSignedIn(session.user);

  });


})(window.DAON_APP);

