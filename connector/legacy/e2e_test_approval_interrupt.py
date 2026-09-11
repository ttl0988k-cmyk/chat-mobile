# -*- coding: utf-8 -*-
"""E2E 검증 v2: 실존 conversation 자동 조회 → system role 제어 메시지 INSERT
   커넥터 필터 통과 → daon_approval/daon_cancel → 9090 POST 도달 여부는 커넥터 로그로 판정"""
import json, urllib.request, urllib.error, uuid

env = {}
for l in open(r'C:\daon\.env', encoding='utf-8'):
    l = l.strip()
    if '=' in l and not l.startswith('#'):
        k, v = l.split('=', 1)
        env[k.strip()] = v.strip()
URL = env['SUPABASE_URL'].rstrip('/')
K = env['SUPABASE_SERVICE_ROLE_KEY']
H = {'apikey': K, 'Authorization': 'Bearer ' + K, 'Content-Type': 'application/json'}

TAG = uuid.uuid4().hex[:6]
print('tag =', TAG)

# 1) 실존 conversation 조회 (최신 1건)
req = urllib.request.Request(URL + '/rest/v1/conversations?select=id,created_at&order=created_at.desc&limit=1',
                             headers=H)
with urllib.request.urlopen(req, timeout=10) as r:
    rows = json.loads(r.read().decode())
CID = rows[0]['id']
UID = rows[0].get('user_id') or '2e8e15e5-73bf-483f-bc96-5094cf2d9a01'
print('conversation =', CID)

def insert(role, content, meta):
    body = json.dumps({'conversation_id': CID, 'role': role, 'content': content,
                       'metadata': meta}).encode()
    req = urllib.request.Request(URL + '/rest/v1/messages', data=body, headers=H, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return f'FAIL {e.code} {e.read().decode("utf-8")[:200]}'

s1 = insert('system', f'[E2E-TEST {TAG}] 승인응답', {
    'type': 'approval_response', 'approved': True,
    'session_id': f'e2e-raon-{TAG}', 'reason': '라온 E2E 자동검증'})
print('approval_response INSERT →', s1)

s2 = insert('system', f'[E2E-TEST {TAG}] 인터럽트', {
    'type': 'interrupt', 'stream_id': f'e2e-stream-{TAG}',
    'session_id': f'e2e-raon-{TAG}'})
print('interrupt INSERT →', s2)
