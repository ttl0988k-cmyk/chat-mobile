"""Supabase Realtime 정확한 프로토콜 테스트 — phx_join에 config 포함"""
import asyncio, json, urllib.request, uuid

env = {}
with open(r'C:\daon\.env', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()

URL = env['SUPABASE_URL'].rstrip('/')
SERVICE = env['SUPABASE_SERVICE_ROLE_KEY']

import websockets

async def main():
    ws_url = URL.replace('https://', 'wss://') + '/realtime/v1/websocket?apikey=' + SERVICE + '&vsn=1.0.0'
    topic = 'realtime:test2'
    async with websockets.connect(ws_url, ping_interval=20) as ws:
        print('✅ 연결됨')
        # phx_join + config에 postgres_changes 포함 (공식 supabase-py 방식)
        join_msg = {
            "topic": topic,
            "event": "phx_join",
            "payload": {
                "config": {
                    "broadcast": {"key": "", "enabled": False},
                    "presence": {"key": "", "enabled": False},
                    "private": False,
                    "postgres_changes": [
                        {"event": "INSERT", "schema": "public", "table": "messages"}
                    ],
                }
            },
            "ref": "1",
        }
        await ws.send(json.dumps(join_msg))
        print('phx_join(config 포함) 전송됨')
        # 응답 수신
        try:
            resp = await asyncio.wait_for(ws.recv(), timeout=5)
            print('응답:', json.dumps(json.loads(resp), ensure_ascii=False)[:300])
        except asyncio.TimeoutError:
            print('응답 타임아웃')

        # 잠시 후 INSERT
        await asyncio.sleep(2)
        body = json.dumps({
            'conversation_id': 'd4fb8096-1191-4f41-809e-7574a0cf5a4a',
            'role': 'user',
            'content': 'realtime 테스트2 ' + uuid.uuid4().hex[:6],
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
                    print(json.dumps(msg, ensure_ascii=False)[:500])
                    break
                elif ev == 'phx_reply':
                    print('phx_reply:', json.dumps(msg.get('payload', {}), ensure_ascii=False)[:200])
        except asyncio.TimeoutError:
            print('❌ 이벤트 수신 타임아웃')

asyncio.run(main())
