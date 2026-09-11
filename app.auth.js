// app.auth.js - auth/signin + view switching
(function (APP) {
'use strict';

  APP.login = async function login() {

    const email = APP.$('auth-email').value.trim();

    const password = APP.$('auth-password').value;

    APP.$('auth-msg').textContent = '';

    if (!email || !password) { APP.$('auth-msg').textContent = '이메일/비번 입력'; return; }

    const { data, error } = await APP.sb.auth.signInWithPassword({ email, password });

    if (error) { APP.$('auth-msg').textContent = '로그인 실패: ' + error.message; return; }

    APP.onSignedIn(data.user);

  };
  APP.signup = async function signup() {

    const email = APP.$('auth-email').value.trim();

    const password = APP.$('auth-password').value;

    APP.$('auth-msg').textContent = '';

    if (!email || !password) { APP.$('auth-msg').textContent = '이메일/비번 입력'; return; }

    const { data, error } = await APP.sb.auth.signUp({ email, password });

    if (error) { APP.$('auth-msg').textContent = '가입 실패: ' + error.message; return; }

    if (data.session) APP.onSignedIn(data.user);

    else APP.$('auth-msg').textContent = '가입 완료 — 이메일을 확인하세요.';

  };
  APP.logout = async function logout() {

    await APP.sb.auth.signOut();

    APP.currentConversationId = null;

    APP.showView('auth');

  };
  APP.showView = function showView(name) {

    Object.entries(APP.views).forEach(([k, el]) => el.classList.toggle('active', k === name));

  };
  APP.onSignedIn = function onSignedIn(user) {

    APP.currentUserId = user.id;

    APP.$('user-email').textContent = user.email;

    APP.showView('chat');

    APP.loadModelList();

    APP.ensureConversation().then(() => {

      APP.loadMessages();

      APP.subscribeMessages();

    });

    // [v3] 폴링 루프: 3초마다 새 메시지 확인 (승인 요청 실시간 수신)

    // [v4] 부드러운 백그라운드 동기화 (DOM innerHTML 초기화 없이 새 메시지만 갱신)
    setInterval(() => {
      if (APP.currentConversationId && document.visibilityState !== 'hidden') {
        APP.syncMessagesBackground();
      }
    }, 3000);

  };
})(window.DAON_APP);

