# -*- coding: utf-8 -*-
"""E2E 테스트: 모바일 채널 스트리밍 row 1개 검증 (2026-09-04)"""
import json, time, urllib.request, urllib.error

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
print('테스트 대화:', conv['id'][:8], '…')

st, row = api('POST', '/rest/v1/messages', {
    'conversation_id': conv['id'], 'user_id': conv['user_id'], 'role': 'user',
    'content': '[시스템 점검] 모바일 채널 테스트입니다. 한 줄만 짧게 답해주세요. 링크: https://example.com',
})
print('테스트 메시지 전송:', st)

seen = {}
for i in range(45):
    time.sleep(2)
    st, rows = api('GET', '/rest/v1/messages?select=id,role,content,metadata,created_at&conversation_id=eq.' + conv['id'] + '&order=created_at.desc&limit=15')
    if st != 200 or not rows:
        continue
    for r in rows:
        m = r.get('metadata') or {}
        seen[r['id']] = (r['role'], m.get('type', ''), (r['content'] or '')[:60].replace('\n', ' '))
    done = any(v[1] == 'complete' and '점검' not in v[2] for v in seen.values())
    if i % 5 == 4:
        print('  ... %d초 경과, rows=%d' % ((i + 1) * 2, len(seen)))
    if done:
        break

print()
print('=== 최종 row 목록 (최근) ===')
for rid, v in list(seen.items())[:12]:
    print(' |', v[0], '|', v[1], '|', v[2])

st, rows = api('GET', '/rest/v1/messages?select=id,role,content,metadata&conversation_id=eq.' + conv['id'] + '&order=created_at.desc&limit=15')
asst = [r for r in rows if r['role'] == 'assistant' and ((r.get('metadata') or {}).get('type') in ('delta', 'complete'))]
stat = [r for r in rows if ((r.get('metadata') or {}).get('type') == 'status')]
print()
print('assistant 응답 row 수:', len(asst), '(기대: 1)')
print('잔여 status 배지 row:', len(stat), '(기대: 0 — done 시 삭제)')
if asst:
    print('응답 미리보기:', (asst[0]['content'] or '')[:120].replace('\n', ' '))
