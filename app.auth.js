// app.auth.js - 9990 비밀번호 게이트 + view switching (2026-09-11 라온)
(function (APP) {
'use strict';

  APP.login = async function login() {
    const pw = APP.$('auth-password').value;
    APP.$('auth-msg').textContent = '';
    if (pw !== window.APP_PASSWORD) {
      APP.$('auth-msg').textContent = '비밀번호가 틀렸습니다.';
      return;
    }
    // 기존 supabase 세션 있으면 재사용, 없으면 익명 로그인 시도
    const { data: sess } = await APP.sb.auth.getSession();
    if (sess && sess.session) { APP.onSignedIn(sess.session.user); return; }

    // 익명 세션 (supabase anon sign-in) — 프로젝트에서 익명 로그인 비활성이어도 local-only 게이트로 통과
    try {
      const { data, error } = await APP.sb.auth.signInAnonymously();
      if (!error && data && data.user) { APP.onSignedIn(data.user); return; }
    } catch (e) { /* fallthrough */ }

    // local-only 유저 폴백 (DB user_id 없이도 대화 동작 가능하게 하기 위해 고정 ID 사용)
    APP.onSignedIn({ id: 'local-user', email: 'daon@local' });
  };

  APP.logout = async function logout() {
    try { await APP.sb.auth.signOut(); } catch (e) {}
    APP.currentConversationId = null;
    APP.showView('auth');
  };

  APP.showView = function showView(name) {
    Object.entries(APP.views).forEach(([k, el]) => el.classList.toggle('active', k === name));
  };

  APP.onSignedIn = function onSignedIn(user) {
    APP.currentUserId = user.id;
    APP.$('user-email').textContent = user.email || '';
    APP.showView('chat');
  };

})(window.DAON_APP);
