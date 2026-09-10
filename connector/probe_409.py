# -*- coding: utf-8 -*-
"""409 원인 파악: PostgREST 에러 본문 출력"""
import json, urllib.request, urllib.error

env = {}
for l in open(r'C:\daon\.env', encoding='utf-8'):
    l = l.strip()
    if '=' in l and not l.startswith('#'):
        k, v = l.split('=', 1)
        env[k.strip()] = v.strip()
URL = env['SUPABASE_URL'].rstrip('/')
K = env['SUPABASE_SERVICE_ROLE_KEY']

body = json.dumps({
    'conversation_id': 'aa0feff2-3ecd-442b-b66f-95bca59a446c',
    'user_id': '2e8e15e5-73bf-483f-bc96-5094cf2d9a01',
    'role': 'system',
    'content': 'E2E probe',
    'metadata': {'type': 'approval_response', 'approved': True, 'session_id': 'e2e-x1'},
}).encode()
req = urllib.request.Request(URL + '/rest/v1/messages', data=body, headers={
    'apikey': K, 'Authorization': 'Bearer ' + K, 'Content-Type': 'application/json',
}, method='POST')
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print('OK', r.status)
except urllib.error.HTTPError as e:
    print('status', e.code)
    print(e.read().decode('utf-8')[:600])
