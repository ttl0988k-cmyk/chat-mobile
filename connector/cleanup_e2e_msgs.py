# -*- coding: utf-8 -*-
"""E2E 테스트 메시지 정리: [E2E-TEST] system 메시지 삭제"""
import json, urllib.request

env = {}
for l in open(r'C:\daon\.env', encoding='utf-8'):
    l = l.strip()
    if '=' in l and not l.startswith('#'):
        k, v = l.split('=', 1)
        env[k.strip()] = v.strip()
URL = env['SUPABASE_URL'].rstrip('/')
K = env['SUPABASE_SERVICE_ROLE_KEY']

req = urllib.request.Request(
    URL + "/rest/v1/messages?content=like.*[E2E-TEST*",
    headers={'apikey': K, 'Authorization': 'Bearer ' + K, 'Prefer': 'return=representation'},
    method='DELETE')
with urllib.request.urlopen(req, timeout=10) as r:
    rows = json.loads(r.read().decode())
print('삭제된 테스트 메시지:', len(rows), '건')
