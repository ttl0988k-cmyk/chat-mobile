// /api/wan22/notebook — 라온이 만든 파라미터화 노트북을 서빙
// 1순위: 라온 워크스페이스의 노트북을 base64로 env에 박은 경우 (env 보존)
// 2순위: 라온이 GitHub에 배포한 노트북을 raw.githubusercontent.com에서 프록시
// 3순위: 503

const NOTEBOOK_B64 = process.env.WAN22_NOTEBOOK_B64 || '';
const GITHUB_RAW_URL = process.env.WAN22_NOTEBOOK_URL ||
  'https://raw.githubusercontent.com/szchengmi/kaggle-wan22-t2v/main/kaggle_wan22_t2v.ipynb';

export default async function handler(req, res) {
  // 1순위: env에 base64로 들어있으면 즉시 서빙
  if (NOTEBOOK_B64) {
    const buf = Buffer.from(NOTEBOOK_B64, 'base64');
    res.setHeader('Content-Type', 'application/x-ipynb+json');
    res.setHeader('Content-Disposition', 'attachment; filename="kaggle_wan22_t2v_param.ipynb"');
    return res.status(200).send(buf);
  }

  // 2순위: GitHub 프록시
  try {
    const upstream = await fetch(GITHUB_RAW_URL);
    if (!upstream.ok) throw new Error(`upstream ${upstream.status}`);
    const buf = Buffer.from(await upstream.arrayBuffer());
    res.setHeader('Content-Type', 'application/x-ipynb+json');
    res.setHeader('Content-Disposition', 'attachment; filename="kaggle_wan22_t2v_original.ipynb"');
    return res.status(200).send(buf);
  } catch (e) {
    return res.status(503).json({
      error: '노트북 다운로드 실패',
      upstream: GITHUB_RAW_URL,
      detail: e.message,
      hint: '직접 받기: ' + GITHUB_RAW_URL,
    });
  }
}
