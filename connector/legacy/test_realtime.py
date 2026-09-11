"""Supabase Realtime WS 직접 연결 테스트"""
import asyncio, json, sys
sys.path.insert(0, r'C:\daon')
import urllib.request

# .env 로드
env = {}
with open(r'C:\daon\.env', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()

URL = env['SUPABASE_URL'].rstrip('/')
KEY = env['SUPABASE_SERVICE_ROLE_KEY']
print('URL:', URL)

# websockets 15.x: connect 후 send/recv
import websockets

async def main():
    ws_url = URL.replace('https://', 'wss://') + '/realtime/v1/websocket?apikey=' + KEY + '&vsn=1.0.0'
    print('WS URL:', ws_url[:100] + '...')
    try:
        async with websockets.connect(ws_url, ping_interval=20) as ws:
            print('✅ 연결됨')
            await ws.send(json.dumps({
                "topic": "realtime:test",
                "event": "phx_join",
                "payload": {},
                "ref": "1",
            }))
            print('phx_join 전송됨')
            # 응답 대기 (3초)
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=5)
                print('응답:', resp[:300])
            except asyncio.TimeoutError:
                print('응답 타임아웃 (연결은 되었지만 응답 없음)')
    except Exception as e:
        print('❌ 연결 실패:', type(e).__name__, e)

asyncio.run(main())
