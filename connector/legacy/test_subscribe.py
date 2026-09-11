"""Supabase Realtime 구독 + INSERT 테스트 — 실제 이벤트 수신 확인"""
import asyncio, json, urllib.request

env = {}
with open(r'C:\daon\.env', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()

URL = env['SUPABASE_URL'].rstrip('/')
SERVICE = env['SUPABASE_SERVICE_ROLE_KEY']
ANON = env['SUPABASE_ANON_KEY']

import websockets

async def main():
    ws_url = URL.replace('https://', 'wss://') + '/realtime/v1/websocket?apikey=' + SERVICE + '&vsn=1.0.0'
    async with websockets.connect(ws_url, ping_interval=20) as ws:
        print('✅ 연결됨')
        # phx_join
        await ws.send(json.dumps({
            "topic": "realtime:sub-test",
            "event": "phx_join",
            "payload": {},
            "ref": "1",
        }))
        # postgres_changes 구독 — messages 테이블 INSERT (id 필수!)
        await ws.send(json.dumps({
            "topic": "realtime:sub-test",
            "event": "postgres_changes",
            "payload": {
                "event": "INSERT",
                "schema": "public",
                "table": "messages",
                "filter": "",
                "id": 99128230,
            },
            "ref": "2",
        }))
        print('구독 전송됨. 3초 대기...')
        # 3초 대기 후 INSERT 발생시켜 확인
        await asyncio.sleep(3)
        # 서비스 키로 messages INSERT (테스트)
        body = json.dumps({
            'conversation_id': 'd4fb8096-1191-4f41-809e-7574a0cf5a4a',
            'role': 'user',
            'content': 'realtime 테스트',
            'metadata': {},
        }).encode()
        req = urllib.request.Request(URL + '/rest/v1/messages', data=body, headers={
            'apikey': SERVICE, 'Authorization': 'Bearer ' + SERVICE, 'Content-Type': 'application/json',
        }, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                print('INSERT 응답:', resp.status)
        except Exception as e:
            print('INSERT 실패:', e)
        # 이벤트 수신 대기
        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=8)
                msg = json.loads(raw)
                ev = msg.get('event')
                if ev == 'postgres_changes':
                    print('🎯 postgres_changes 수신!')
                    print(json.dumps(msg, ensure_ascii=False, indent=1)[:600])
                    break
                elif ev == 'phx_reply':
                    print('phx_reply:', json.dumps(msg.get('payload', {}))[:150])
        except asyncio.TimeoutError:
            print('❌ 이벤트 수신 타임아웃')

asyncio.run(main())
