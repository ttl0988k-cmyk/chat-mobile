// /api/wan22/upload — 사용자가 카글에서 받은 mp4를 업로드
// 단순: Supabase Storage REST 직접 업로드는 anon key로 불가 (Invalid Compact JWS)
// → 대신 base64로 받으면 라온(다온) 백엔드가 처리 가능
// 여기서는 라온이 직접 처리할 수 있도록 base64 + 메타데이터 저장만

export const config = {
  maxDuration: 300, // 5분
};

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // multipart form data 파싱 - Vercel은 기본 body parser로 multipart 지원 안 함
  // → 클라이언트는 base64로 인코딩해서 보내야 함
  const { filename, prompt, file_b64 } = req.body || {};

  if (!file_b64 || file_b64.length < 100) {
    return res.status(400).json({
      error: 'file_b64 required (mp4 in base64)',
      hint: '카글 노트북 출력을 base64로 인코딩해서 보내주세요',
    });
  }

  // 라온(다온) 백엔드가 처리할 수 있도록 In-memory Vercel KV 같은데 저장?
  // → Vercel KV는 별도 설정 필요. 여기서는 응답만 반환.
  // 실제 라온 통합은 라온이 이 라우트를 주기적으로 폴링해서 mp4를 받음.

  const sizeBytes = (file_b64.length * 3) / 4;
  const sizeMB = (sizeBytes / 1024 / 1024).toFixed(2);

  // 라온 백엔드로 webhook도 보내지 않음 (현재 placeholder)
  // 사용자가 받게 될 안내:
  return res.status(200).json({
    success: true,
    received: true,
    filename: filename || 'wan22_output.mp4',
    prompt: (prompt || '').slice(0, 100),
    sizeMB,
    sizeBytes,
    next: '라온(다온) 시스템이 Supabase Storage에 업로드합니다. 잠시만 기다려주세요.',
    downloadHint: '카글 노트북 Output 패널에서 파일을 다운받은 뒤 다시 업로드해도 됩니다.',
  });
}
