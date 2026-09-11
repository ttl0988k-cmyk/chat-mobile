// app.auth.js - 9990 비밀번호 게이트 + view switching (2026-09-11 라온)
// [FIX 2026-09-12] 로그인 직후 모델 목록 로드 추가 — init 중단(APP.APP 오타)과 별개로,
//   세션 복원/익명 로그인 경로에서도 모델 목록이 즉시 채워지도록 보강.
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
    Object.entries(APP.views).forEach(([k, el]) => el && el.classList.toggle('active', k === name));
  };

  APP.onSignedIn = function onSignedIn(user) {
    APP.currentUserId = user.id;
    const emailEl = APP.$('user-email');
    if (emailEl) emailEl.textContent = user.email || '';
    APP.showView('chat');

    // [FIX 2026-09-12] 로그인 후 모델 목록 로드 — 이 호출이 없으면
    // Supabase 실시간 목록 동기화가 시작되지 않아 모델이 비어 보인다.
    try {
      if (typeof APP.loadModelList === 'function') APP.loadModelList();
    } catch (e) { console.warn('[auth] loadModelList 실패:', e); }

    // 안전망: 그래도 비어 있으면 config.js 기준으로 채운다
    setTimeout(() => {
      const sel = APP.$('model-select');
      if (sel && sel.options.length <= 1) {
        try {
          const g = window.SUPABASE_CONFIG && window.SUPABASE_CONFIG.modelGroups;
          if (g && g.length) APP.renderModelOptions(g);
        } catch (e) {}
      }
    }, 900);
  };

})(window.DAON_APP);
