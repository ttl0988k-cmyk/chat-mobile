// /api/wan22/submit — 실구현 v4 (2026-08-30)
// 1) 노트북 템플릿에 프롬프트/시드/길이 주입
// 2) 카글 kernels/push (Bearer 토큰) → 신규 커널 생성 = 즉시 실행 큐
// 3) jobId(=커널 슬러그) 반환 → 프론트는 /api/wan22/status?slug=... 폴링
import tpl from './notebook-template.js';

export const config = { maxDuration: 300 };

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { prompt, seed } = req.body || {};
  if (!prompt || prompt.length < 5) {
    return res.status(400).json({ error: 'prompt required (5+ chars)' });
  }
  if (prompt.length > 800) {
    return res.status(400).json({ error: 'prompt too long (max 800 chars)' });
  }

  const TOKEN = process.env.KAGGLE_TOKEN;
  const USER = process.env.KAGGLE_USERNAME;
  if (!TOKEN || !USER) {
    return res.status(503).json({
      error: 'KAGGLE_TOKEN/KAGGLE_USERNAME env가 설정되지 않았습니다.',
    });
  }

  // 길이 모드: short=단일 세그먼트 5초(15스텝, ~8분) / long=2세그먼트 8초(20스텝, ~14분)
  const duration = req.body && req.body.duration === 'long' ? 'long' : 'short';
  const frames = 81;
  const seg2frames = duration === 'long' ? 49 : 0;
  const steps = duration === 'long' ? 20 : 15;
  const useSeed = Number.isInteger(seed) && seed >= 0
    ? seed
    : Math.floor(Math.random() * 2147483647);

  // 고정 커널 방식 (08-30 확정): 매번 새 커널을 만들면 카글이 GPU를 P100으로
  // 배정해 CUDA 에러. push API는 GPU 모델 지정이 불가하므로, 웹UI에서 T4로
  // 설정된 고정 커널에 "새 버전 push"만 하고 설정을 상속받는다.
  const token = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const kernelSlug = 'wan22-daon-main-t4';   // 실제 생성된 슬러그 (title의 T4가 붙음)

  // placeholder 치환 — 객체 수준에서 먼저 하고 나중에 stringify
  // (JSON 문자열에 직접 replace하면 프롬프트의 따옴표가 노트북 JSON을 깨뜨림)
  const nb = JSON.parse(JSON.stringify(tpl));
  const fills = {
    __WAN22_PROMPT__: JSON.stringify(prompt),
    __WAN22_SEED__: String(useSeed),
    __WAN22_FRAMES__: String(frames),
    __WAN22_SEG2FRAMES__: String(seg2frames),
    __WAN22_STEPS__: String(steps),
  };
  for (const cell of nb.cells) {
    if (Array.isArray(cell.source)) {
      cell.source = cell.source.map(s => {
        let x = String(s);
        for (const [k, v] of Object.entries(fills)) x = x.replaceAll(k, v);
        return x;
      });
    } else if (typeof cell.source === 'string') {
      let x = cell.source;
      for (const [k, v] of Object.entries(fills)) x = x.replaceAll(k, v);
      cell.source = x;
    }
  }
  const text = JSON.stringify(nb);
  if (/__WAN22_[A-Z0-9_]+__/.test(text)) {
    return res.status(500).json({ error: 'placeholder 치환 실패 (템플릿 불일치)' });
  }

  const pushBody = {
    slug: `${USER}/${kernelSlug}`,
    newTitle: `Wan22 Daon ${token}`,
    text, // ipynb JSON 문자열
    language: 'python',
    kernelType: 'notebook',
    isPrivate: true,
    enableGpu: true,
    enableInternet: true,
    datasetDataSources: [],
    competitionDataSources: [],
    kernelDataSources: [],
    modelDataSources: [],
    categoryIds: [],
  };

  try {
    const r = await fetch('https://www.kaggle.com/api/v1/kernels/push', {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + TOKEN, 'Content-Type': 'application/json' },
      body: JSON.stringify(pushBody),
    });
    const out = await r.json().catch(() => ({}));
    if (!r.ok || out.error) {
      return res.status(502).json({
        error: '카글 push 실패',
        detail: out.error || `HTTP ${r.status}`,
      });
    }
    // ref: "/code/<user>/<slug>"
    const ref = out.ref || `/code/${USER}/${kernelSlug}`;
    const actualSlug = ref.split('/').pop();
    return res.status(200).json({
      jobId: actualSlug,
      seed: useSeed,
      duration,
      status: 'queued',
      pollUrl: `/api/wan22/status?slug=${actualSlug}`,
      url: out.url || `https://www.kaggle.com/code/${USER}/${actualSlug}`,
      next: duration === 'long'
        ? '카글 GPU 큐 등록 완료. 2세그먼트 모드, 12~16분 예정.'
        : '카글 GPU 큐 등록 완료. 빠른 모드(5초), 약 8분 예정.',
    });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
