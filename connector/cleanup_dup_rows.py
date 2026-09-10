# -*- coding: utf-8 -*-
"""cleanup_dup_rows.py — 중복 delta row + 옛날 tool row + stale status row 삭제 (1회 실행)"""
import json, urllib.request

env = {}
for line in open(r'C:\daon\.env', encoding='utf-8', errors='replace'):
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

url = env.get('SUPABASE_URL', '').rstrip('/')
key = env.get('SUPABASE_SERVICE_ROLE_KEY', '')

def req(method, path):
    r = urllib.request.Request(url + path, headers={'apikey': key, 'Authorization': 'Bearer ' + key}, method=method)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return resp.status, resp.read().decode()

# 1. complete rows → (conv, stream) 페어 수집
s, data = req('GET', '/rest/v1/messages?select=conversation_id,metadata&metadata->>type=eq.complete&limit=2000')
completes = json.loads(data)
pairs = set()
for r in completes:
    m = r.get('metadata') or {}
    sid = m.get('stream_id')
    if sid:
        pairs.add((r['conversation_id'], sid))
print('complete 스트림 페어:', len(pairs))

# 2. complete가 존재하는 stream의 delta row 전부 삭제 (중복 표시의 원흉)
total_del = 0
for conv, sid in pairs:
    q = ('/rest/v1/messages?conversation_id=eq.' + conv +
         '&metadata->>type=eq.delta&metadata->>stream_id=eq.' + sid)
    st, _ = req('DELETE', q)
    if st in (200, 204):
        total_del += 1
print('delta 삭제 처리 페어:', total_del)

# 3. 옛날 도구 로그 rows 전부 삭제
st, _ = req('DELETE', '/rest/v1/messages?metadata->>type=eq.tool')
print('tool rows 삭제:', st)

# 4. stale status 배지 rows 삭제
st, _ = req('DELETE', '/rest/v1/messages?metadata->>type=eq.status')
print('status rows 삭제:', st)

print('✅ DB 청소 완료')
