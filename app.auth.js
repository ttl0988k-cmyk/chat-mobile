// app.auth.js - 9990 게이트 + Supabase 세션 (2026-09-12 라온)
// [FIX 2026-09-12] 채팅 불가 근본 수정
//   ▸ 증상: 익명 로그인 비활성(anonymous_provider_disabled 422) →
//           user_id 'local-user' → uuid 캐스팅 실패(22P02 400) → 모든 DB 요청 실패
//   ▸ 조치: 9990 게이트 통과 후 config.js 의 window.DAON_LOGIN 계정으로
//           signInWithPassword() 를 수행해 '진짜 uuid' 세션을 만든다.
(function (APP) {
'use strict';

  // 9990 게이트 통과 → 실제 Supabase 세션 확보
  APP.login = async function login() {
    const pwEl = APP.$('auth-password');
    const msgEl = APP.$('auth-msg');
    const pw = pwEl ? pwEl.value : '';
    if (msgEl) msgEl.textContent = '';

    if (pw !== window.APP_PASSWORD) {
      if (msgEl) msgEl.textContent = '비밀번호가 틀렸습니다.';
      return;
    }
    if (msgEl) msgEl.textContent = '연결 중…';

    // 1) 기존 세션 재사용
    try {
      const { data: sess } = await APP.sb.auth.getSession();
      if (sess && sess.session && sess.session.user) {
        APP.onSignedIn(sess.session.user);
        return;
      }
    } catch (_) {}

    // 2) 앱 전용 계정으로 로그인 (실제 uuid 확보)
    const cred = window.DAON_LOGIN;
    if (cred && cred.email && cred.password) {
      try {
        const { data, error } = await APP.sb.auth.signInWithPassword({
          email: cred.email, password: cred.password
        });
        if (!error && data && data.user) { APP.onSignedIn(data.user); return; }
        console.warn('[auth] signInWithPassword 실패:', error && error.message);
      } catch (e) { console.warn('[auth] signInWithPassword 예외:', e); }
    }

    // 3) 익명 로그인 시도 (프로젝트에서 켜져 있는 경우)
    try {
      const { data, error } = await APP.sb.auth.signInAnonymously();
      if (!error && data && data.user) { APP.onSignedIn(data.user); return; }
    } catch (_) {}

    // 4) 최후 폴백 — uuid 형식의 고정 ID (uuid 캐스팅 실패 방지)
    if (msgEl) msgEl.textContent = '오프라인 모드로 시작합니다.';
    APP.onSignedIn({ id: '00000000-0000-0000-0000-000000000000', email: 'offline@daon' });
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

    // 로그인 후 모델 목록 로드 (Supabase 실시간 목록 동기화 시작)
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
