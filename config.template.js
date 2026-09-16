// ============================================================
//  config.js — 채팅 UI가 사용하는 공개 설정 (브라우저에 노출됨)
//
//  ⚠️ 이 파일(config.template.js)을 같은 폴더에 config.js 로 복사한 뒤
//     아래 [채울 값 3가지]를 채워서 사용하세요.
//     config.js 는 .gitignore 로 제외되어 있어 저장소에 올라가지 않습니다.
// ============================================================
//
//  [채울 값 3가지]
//   1) APP_PASSWORD      : 앱 접속 비밀번호 (내가 정하는 값)
//   2) DAON_LOGIN        : Supabase에서 만든 내 계정 (이메일/비번)
//   3) SUPABASE_CONFIG   : 내 Supabase 프로젝트 URL + anon 키
//
//  ※ service_role / secret 키는 절대 여기에 넣지 마세요.
//     (이 파일은 브라우저에 그대로 노출됩니다)
// ============================================================

// ── 1) 앱 접속 비밀번호 (내가 정함, 예: 'mypass1234')
window.APP_PASSWORD='여기에_내_비밀번호';

// ── 2) 앱 로그인 계정
//   ▸ 이 값이 없으면 익명 로그인(비활성)으로 떨어져 user_id 가 'local-user' 가 되고,
//     uuid 캐스팅 실패(22P02)로 채팅이 전혀 동작하지 않습니다.
//   ▸ Supabase Dashboard → Authentication → Users → Add user 로
//     이메일/비밀번호를 먼저 만들어야 합니다.
window.DAON_LOGIN = {
  email: '내이메일@example.com',
  password: '내비밀번호'
};

// ── 3) Supabase 연결 설정
window.SUPABASE_CONFIG = {
  // Supabase Dashboard → Settings → API → Project URL
  url: 'https://여기에-내-프로젝트.supabase.co',

  // Supabase Dashboard → Settings → API → Project API keys → anon / public
  anonKey: '여기에_anon_키',

  defaultModel: 'MiniMax-M3',

  // 모델 목록 — 비워두면 PC 커넥터가 다온 앱에서 모델 목록을 가져와 채워줍니다.
  modelGroups: [],

  // 커넥터가 못 채웠을 때 쓸 최소 목록 (필요하면 수정)
  models: [
    { provider: 'Omniroute', id: 'auto', label: 'auto (무료 라우팅)', type: 'chat' }
  ]
};
