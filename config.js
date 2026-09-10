// config.js — 채팅 UI가 사용하는 공개 설정 (브라우저에 노출됨)
// ⚠️ service_role/secret 키는 절대 여기에 넣지 마세요. publishable(anon) key만 사용.
window.SUPABASE_CONFIG = {
  url: 'https://gfpsahhfllozfqczyoza.supabase.co',
  anonKey: 'sb_publishable_DcKkfosSQHBO65vHT9tfow_flGTKYXT',
  // 모델 목록 (DAON /api/models 기준 — 폰에서 직접 접근 불가하므로 하드코딩)
  models: [
    { provider: 'MiniMax', id: 'MiniMax-M3' },
    { provider: 'MiniMax', id: 'MiniMax-M2.7' },
    { provider: 'DeepSeek', id: 'deepseek-v4-flash' },
    { provider: 'DeepSeek', id: 'deepseek-v4-pro' },
    { provider: 'OpenRouter', id: 'z-ai/glm-5.3-flash' },
    { provider: 'Qwen (Alibaba)', id: 'qwen3.8-max' },
    { provider: 'Qwen (Alibaba)', id: 'qwen3.8-flash' },
    { provider: 'Qwen (Alibaba)', id: 'deepseek-v4-flash-0731' }
  ]
};
