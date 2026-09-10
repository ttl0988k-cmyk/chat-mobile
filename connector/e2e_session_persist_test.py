# -*- coding: utf-8 -*-
"""세션 영속화 검증: 테스트 메시지 1건 전송 → 매핑 파일 확인"""
import json, time, os, urllib.request, urllib.error

env = {}
for line in open(r'C:\daon\.env', encoding='utf-8', errors='replace'):
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1); env[k.strip()] = v.strip()
url = env.get('SUPABASE_URL', '').rstrip('/')
key = env.get('SUPABASE_SERVICE_ROLE_KEY', '')


def api(method, path, body=None):
    h = {'apikey': key, 'Authorization': 'Bearer ' + key, 'Prefer': 'return=representation'}
    data = None
    if body is not None:
        h['Content-Type'] = 'application/json'
        data = json.dumps(body).encode()
    r = urllib.request.Request(url + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')[:200]


st, convs = api('GET', '/rest/v1/conversations?select=id,user_id&order=updated_at.desc&limit=1')
conv = convs[0]
print('대화:', conv['id'])

st, _ = api('POST', '/rest/v1/messages', {
    'conversation_id': conv['id'], 'user_id': conv['user_id'], 'role': 'user',
    'content': '[세션 매핑 점검] 응답은 짧게 한 줄만.',
})
print('메시지 전송:', st)

for i in range(10):
    time.sleep(3)
    p = r'C:\daon\cafe\LLM\chat\connector\conv_sessions.json'
    if os.path.exists(p):
        m = json.load(open(p, encoding='utf-8'))
        sid = m.get(conv['id'])
        print('✅ 매핑 파일 생성됨 (%d건). 이 대화 → 세션: %s' % (len(m), (sid or 'N/A')))
        break
else:
    print('⏳ 매핑 파일 아직 미생성 — 로그 확인 필요')
