// /api/wan22/callback — 카글 노트북이 완료되면 multipart로 mp4를 받음
// 1) mp4를 받으면 즉시 Supabase Storage 'chat-files' 버킷에 업로드
// 2) 본인 uid 폴더에 /{uid}/wan22-{jobId}.mp4 로 저장
// 3) Supabase Storage는 본인의 RLS 정책상 service_role 키가 필요
//    → Supabase Storage API는 anon key로는 upload 제한
//    → 우회: signedUrl 직접 생성 (service_role이 발급해준 long-lived URL에 PUT)
//
// 전략: 라온이 이 라우트에 mp4를 보내면, 라온(다온 시스템) 쪽에서
// 이미 다온 server.exe가 service_role 키로 signed upload url을 만들어
// mp4를 Supabase Storage에 업로드하도록 함.
//
// 즉 이 라우트는 단순히 mp4를 받아서 "성공" 신호만 보내고
// 실제 업로드는 라온이 처리.
//
// 또는: Vercel 환경변수에 SUPABASE_SERVICE_ROLE_KEY를 넣으면
//       직접 업로드 가능 (지금 사용).

export const config = {
  maxDuration: 300, // 5분
};

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const jobId = req.query.jobId || 'unknown';

  // ⚠️ 현재 구조: 라온(다온) 백엔드가 직접 카글 kernel을 실행하고
  // mp4를 Supabase Storage에 업로드 후 채팅창에 signedUrl을 게시함.
  // 이 라우트는 호환성 유지용 placeholder.
  return res.status(200).json({
    success: true,
    jobId,
    note: 'Receive mp4 (현재는 라온 백엔드가 직접 처리 중). 직접 업로드가 필요하면 SUPABASE_SERVICE_ROLE_KEY 추가 요망.',
  });
}
