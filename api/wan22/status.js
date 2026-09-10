// /api/wan22/status — 실구현 (2026-08-30)
// 폴링 순서:
//   1) Supabase에 이미 결과 mp4 있으면 → signedUrl 반환 (complete)
//   2) 카글 커널 상태 조회 (queued/running/error)
//   3) 커널 complete → output zip 다운로드 → mp4 추출 → Supabase 업로드 → signedUrl

export const config = { maxDuration: 300 };

const SB_URL = () => (process.env.SUPABASE_URL || '').replace(/\/$/, '');
const SB_KEY = () => process.env.SUPABASE_SERVICE_ROLE_KEY || '';
const KAG = () => ({
  token: process.env.KAGGLE_TOKEN || '',
  user: process.env.KAGGLE_USERNAME || '',
});

const objPath = (slug) => `chat-files/raon-agent/wan22/${slug}.mp4`;

async function supabaseObjectExists(slug) {
  const r = await fetch(`${SB_URL()}/storage/v1/object/${objPath(slug)}`, {
    method: 'HEAD',
    headers: { apikey: SB_KEY(), Authorization: 'Bearer ' + SB_KEY() },
  });
  return r.ok;
}

async function createSignedUrl(slug, expiresIn = 86400) {
  const r = await fetch(`${SB_URL()}/storage/v1/object/sign/${objPath(slug)}`, {
    method: 'POST',
    headers: {
      apikey: SB_KEY(),
      Authorization: 'Bearer ' + SB_KEY(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ expiresIn }),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || !j.signedURL) throw new Error('signedURL 생성 실패: ' + JSON.stringify(j).slice(0, 150));
  return SB_URL() + j.signedURL;
}

async function kaggleStatus(slug) {
  const { token, user } = KAG();
  const r = await fetch(
    `https://www.kaggle.com/api/v1/kernels/status?userName=${user}&kernelSlug=${encodeURIComponent(slug)}`,
    { headers: { Authorization: 'Bearer ' + token } }
  );
  if (r.status === 403 || r.status === 404) return { status: 'notfound' };
  const j = await r.json().catch(() => ({}));
  return { status: j.status || 'unknown', message: j.failureMessage || '' };
}

async function finalize(slug) {
  const { token, user } = KAG();
  const r = await fetch(
    `https://www.kaggle.com/api/v1/kernels/output?userName=${user}&kernelSlug=${encodeURIComponent(slug)}`,
    { headers: { Authorization: 'Bearer ' + token } }
  );
  if (!r.ok) throw new Error('카글 output 조회 실패: HTTP ' + r.status);
  const buf = Buffer.from(await r.arrayBuffer());

  // 응답은 zip(PK 헤더) 또는 JSON(로그만 있고 output 파일 없음)
  if (buf.length < 4 || buf[0] !== 0x50 || buf[1] !== 0x4b) {
    throw new Error('output zip 없음(아직 생성 중일 수 있음): ' + buf.toString('utf8', 0, 120));
  }

  const { unzipSync } = await import('fflate');
  const files = unzipSync(buf);
  let name = null;
  let size = 0;
  for (const [n, data] of Object.entries(files)) {
    if (n.endsWith('.mp4') && data.length > size) {
      name = n;
      size = data.length;
    }
  }
  if (!name) throw new Error('zip 안에 mp4 없음: ' + Object.keys(files).join(', ').slice(0, 200));

  const up = await fetch(`${SB_URL()}/storage/v1/object/${objPath(slug)}`, {
    method: 'POST',
    headers: {
      apikey: SB_KEY(),
      Authorization: 'Bearer ' + SB_KEY(),
      'Content-Type': 'video/mp4',
      'x-upsert': 'true',
    },
    body: files[name],
  });
  if (!up.ok) throw new Error('Storage 업로드 실패: ' + (await up.text()).slice(0, 200));

  const videoUrl = await createSignedUrl(slug);
  return { videoUrl, sizeMB: +(size / 1048576).toFixed(1) };
}

export default async function handler(req, res) {
  const slug = String(req.query.slug || req.query.jobId || '').trim();
  if (!slug) return res.status(400).json({ error: 'slug required' });
  if (!process.env.KAGGLE_TOKEN || !SB_URL() || !SB_KEY()) {
    return res.status(503).json({ error: 'KAGGLE_TOKEN / SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY env 필요' });
  }

  try {
    // 1) 이미 업로드된 결과?
    if (await supabaseObjectExists(slug)) {
      const videoUrl = await createSignedUrl(slug);
      return res.status(200).json({ slug, status: 'complete', videoUrl });
    }

    // 2) 카글 상태
    const ks = await kaggleStatus(slug);

    if (ks.status === 'complete') {
      // 3) 최종화 (zip → mp4 → Supabase)
      try {
        const { videoUrl, sizeMB } = await finalize(slug);
        return res.status(200).json({ slug, status: 'complete', videoUrl, sizeMB });
      } catch (e) {
        return res.status(200).json({ slug, status: 'finalizing', message: e.message });
      }
    }
    if (ks.status === 'error') {
      return res.status(200).json({ slug, status: 'error', message: ks.message || '커널 실행 에러' });
    }
    if (ks.status === 'notfound') {
      return res.status(200).json({ slug, status: 'error', message: '커널을 찾을 수 없습니다' });
    }
    return res.status(200).json({ slug, status: ks.status }); // queued | running
  } catch (e) {
    return res.status(500).json({ slug, error: e.message });
  }
}
