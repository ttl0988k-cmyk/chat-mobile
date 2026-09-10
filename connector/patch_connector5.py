# -*- coding: utf-8 -*-
"""patch_connector5.py — v3 패치 (2026-09-04)
파일의 \r\r\r\n 변형 개행 오염을 정규화하면서 v3 패치 적용.
"""
import io, sys

PATH = r'C:\daon\cafe\LLM\chat\connector\daon_remote_connector.py'

with io.open(PATH, 'r', encoding='utf-8', newline='') as f:
    raw = f.read()

# 정규화: 모든 개행 변형(\r\r\r\n, \r\n, \r) → \n
content = raw.replace('\r\r\n', '\n').replace('\r\n', '\n').replace('\r', '\n')

R = []

R.append((
"import http.client\nimport websockets\n",
"import http.client\nimport websockets\nimport uuid\n"))

R.append((
"    data = None\n    if body is not None:\n        headers['Content-Type'] = 'application/json'\n        data = json.dumps(body).encode('utf-8')\n",
"    data = None\n    if body is not None:\n        headers['Content-Type'] = 'application/json'\n        if method in ('POST', 'PATCH'):\n            headers['Prefer'] = 'return=representation'\n        data = json.dumps(body).encode('utf-8')\n"))

R.append((
"        self.lock = threading.Lock()\n        # [v2] stream_id별 INSERT 1회만 허용 — 같은 stream에 대해 멀티스레드/Realtime 중복\n        # 알림으로 add_token이 두 번 호출돼도 row 2개 INSERT 방지.\n        self.inserted_streams = {}   # stream_id -> True\n        self._insert_inflight = {}   # stream_id -> True (현재 INSERT HTTP 진행 중)\n",
"        self.lock = threading.Lock()\n"))

R.append((
"        with self.lock:\n            first_token = conv_id not in self.buffers\n            # [v2] 이미 INSERT된 stream의 토큰이 또 들어오면 무시 (중복 row 방지).\n            if stream_id and stream_id in self.inserted_streams and not first_token:\n                return\n",
"        with self.lock:\n            first_token = conv_id not in self.buffers\n            if first_token:\n                # [v3] 새 응답 시작 — 이전 응답의 row를 재사용하지 않음\n                self.msg_ids.pop(conv_id, None)\n"))

R.append((
"            self.buffers.pop(conv_id, None)\n            self.last_flush.pop(conv_id, None)\n            self.user_ids.pop(conv_id, None)\n            self.stream_ids.pop(conv_id, None)\n\n    def _flush_locked",
"            self.buffers.pop(conv_id, None)\n            self.last_flush.pop(conv_id, None)\n            self.user_ids.pop(conv_id, None)\n            self.stream_ids.pop(conv_id, None)\n            self.msg_ids.pop(conv_id, None)  # [v3] 다음 응답은 반드시 새 row\n\n    def _flush_locked"))

R.append((
"        if msg_id is None:\n            # [v2] 같은 stream에 대해 동시에 두 번 INSERT 안 되게 inflight 가드.\n            if stream_id and stream_id in self._insert_inflight:\n                log.warning('⚠️ INSERT inflight (stream=%s) — 중복 flush skip', stream_id)\n                return\n            if stream_id:\n                self._insert_inflight[stream_id] = True\n            try:\n                status, res = sb_request('POST', '/rest/v1/messages', {\n                    'conversation_id': conv_id,\n                    'user_id': user_id,\n                    'role': 'assistant',\n                    'content': text or ('✅ 완료' if is_done else ''),\n                    'metadata': meta,\n                }, service=True)\n                if res and isinstance(res, list) and len(res) > 0:\n                    self.msg_ids[conv_id] = res[0].get('id')\n                    if stream_id:\n                        self.inserted_streams[stream_id] = True\n                    log.info('✅ 메시지 INSERT (conv=%s…, stream=%s…, msg_id=%s)',\n                             conv_id[:8], (stream_id or '')[:8], self.msg_ids[conv_id])\n                else:\n                    log.error('❌ INSERT 응답 이상 status=%s: %s', status,\n                              str(res)[:200] if not isinstance(res, str) else res[:200])\n            finally:\n                if stream_id:\n                    self._insert_inflight.pop(stream_id, None)\n        else:\n            # 동일 행 PATCH 업데이트 (새 행 생성 금지)\n            queue_sb_request('PATCH', f'/rest/v1/messages?id=eq.{msg_id}', {\n                'content': text or ('✅ 완료' if is_done else ''),\n                'metadata': meta,\n            }, service=True)",
"        content = text or ('✅ 완료' if is_done else '')\n\n        if msg_id is None:\n            # [v3] row 1개 INSERT — id를 커넥터가 직접 지정 → 응답 body 없이도 PATCH 가능\n            row_id = str(uuid.uuid4())\n            status, res = sb_request('POST', '/rest/v1/messages', {\n                'id': row_id,\n                'conversation_id': conv_id,\n                'user_id': user_id,\n                'role': 'assistant',\n                'content': content,\n                'metadata': meta,\n            }, service=True)\n            self.msg_ids[conv_id] = row_id\n            if status in (200, 201) and isinstance(res, list) and len(res) > 0:\n                log.info('✅ 메시지 INSERT (conv=%s…, stream=%s…, msg_id=%s)',\n                         conv_id[:8], (stream_id or '')[:8], row_id)\n            else:\n                # body 누락돼도 id는 확보했으므로 이후 flush는 PATCH로 진행\n                log.warning('⚠️ INSERT 응답 비정상 status=%s — id 직접 지정으로 진행: %s',\n                            status, str(res)[:120])\n        else:\n            # 동일 행 PATCH 업데이트 (새 행 생성 금지)\n            queue_sb_request('PATCH', f'/rest/v1/messages?id=eq.{msg_id}', {\n                'content': content,\n                'metadata': meta,\n            }, service=True)"))

R.append((
"_delta_mgr = DeltaStreamManager()\n\n# ── DAON 로컬 API ──────────────────────────────────────────",
"""_delta_mgr = DeltaStreamManager()


# ── 작업 상태 배지 관리 (v3 — "생각중/작업중" row 1개) ──────
class StatusRowManager:
    \"\"\"conv당 status row 1개: 도구 이벤트 → INSERT 1회, 이후 PATCH 갱신, done 시 DELETE.\"\"\"
    def __init__(self):
        self.ids = {}   # conv_id -> status row id
        self.lock = threading.Lock()

    def update(self, conv_id: str, user_id: str, text: str):
        with self.lock:
            row_id = self.ids.get(conv_id)
            if row_id is None:
                row_id = str(uuid.uuid4())
                status, res = sb_request('POST', '/rest/v1/messages', {
                    'id': row_id,
                    'conversation_id': conv_id,
                    'user_id': user_id,
                    'role': 'tool',
                    'content': text,
                    'metadata': {'type': 'status'},
                }, service=True)
                if status in (200, 201):
                    self.ids[conv_id] = row_id
                else:
                    log.error('❌ status row INSERT 실패 status=%s', status)
            else:
                sb_request('PATCH', f'/rest/v1/messages?id=eq.{row_id}', {
                    'content': text,
                    'metadata': {'type': 'status'},
                }, service=True)

    def clear(self, conv_id: str):
        with self.lock:
            row_id = self.ids.pop(conv_id, None)
            if row_id:
                sb_request('DELETE', f'/rest/v1/messages?id=eq.{row_id}', service=True)

_status_mgr = StatusRowManager()

# ── DAON 로컬 API ──────────────────────────────────────────"""))

R.append((
"        elif event == 'done':\n            _delta_mgr.finish(conv_id, session_id=session_id)\n            return False  # 스트림 종료",
"        elif event == 'done':\n            _status_mgr.clear(conv_id)  # [v3] 상태 배지 제거\n            _delta_mgr.finish(conv_id, session_id=session_id)\n            return False  # 스트림 종료"))

R.append((
"            log.info('🔧 [tool %s %s] %s', t_name, t_ev, t_raw[:200])\n            _delta_mgr.flush_now(conv_id, session_id=session_id)\n",
"            log.info('🔧 [tool %s %s] %s', t_name, t_ev, t_raw[:200])\n            _delta_mgr.flush_now(conv_id, session_id=session_id)\n            # [v3] 도구 로그 INSERT 금지 → 상태 배지 1개로 간단 표시\n            if t_name == '_thinking':\n                _status_mgr.update(conv_id, user_id, '💭 생각중…')\n            else:\n                _status_mgr.update(conv_id, user_id, '🔧 작업중… (' + t_name + ')')\n"))

R.append((
"            if _status == 'pending' and _AUTO_APPROVE:\n                _ok2 = daon_approval(session_id, True)\n                log.info('🤖 자율실행 자동승인 ok=%s', _ok2)\n            _delta_mgr.flush_now(conv_id, session_id=session_id)\n            return True\n",
"            if _status == 'pending' and _AUTO_APPROVE:\n                _ok2 = daon_approval(session_id, True)\n                log.info('🤖 자율실행 자동승인 ok=%s', _ok2)\n            _delta_mgr.flush_now(conv_id, session_id=session_id)\n            # [v3] 승인 대기/자동승인 상태 배지\n            if _status == 'pending' and not _AUTO_APPROVE:\n                _status_mgr.update(conv_id, user_id, '🔐 승인 대기중…')\n            else:\n                _status_mgr.update(conv_id, user_id, '💭 생각중…')\n            return True\n"))

R.append((
"        elif event in ('error', 'apierror', 'apperror'):\n            msg_text = data.get('message', data.get('error', '오류'))\n",
"        elif event in ('error', 'apierror', 'apperror'):\n            msg_text = data.get('message', data.get('error', '오류'))\n            _status_mgr.clear(conv_id)  # [v3] 상태 배지 제거\n"))

R.append((
"        elif event == 'cancel':\n            queue_sb_request('POST', '/rest/v1/messages', {\n",
"        elif event == 'cancel':\n            _status_mgr.clear(conv_id)  # [v3] 상태 배지 제거\n            queue_sb_request('POST', '/rest/v1/messages', {\n"))

R.append((
"DAON Remote Connector (2026-09-04 v2 — 중복 INSERT 방지)",
"DAON Remote Connector (2026-09-04 v3 — PATCH 스트리밍 + 상태 배지)"))

R.append((
"v2 핵심 변경 (2026-09-04):\n- DeltaStreamManager에 inserted_streams / _insert_inflight 가드 추가\n- 같은 stream_id에 대해 INSERT 1회만 허용 → 모바일 중복 row 렌더 차단\n- finish() 후에도 msg_ids 보존 → 다음 응답은 PATCH로 이어붙임\n",
"v3 핵심 변경 (2026-09-04):\n- INSERT 시 id를 커넥터가 직접 지정(uuid) + Prefer: return=representation\n  → 응답 body 누락과 무관하게 msg_id 확보 → 중복 INSERT 폭주 근본 차단\n- delta 토큰: 첫 flush 1회 INSERT, 이후 전부 같은 row PATCH → 응답당 row 1개\n- 새 응답 시작 시 이전 row 재사용 금지 (msg_ids 초기화)\n- 도구 이벤트: 로그 INSERT ❌ → 'status' 배지 row 1개 (PATCH 갱신 → done 시 DELETE)\n"))

R.append((
"log.info('🚀 DAON Remote Connector (v2 — 중복 INSERT 방지) 시작')",
"log.info('🚀 DAON Remote Connector (v3 — PATCH 스트리밍 + 상태 배지) 시작')"))

ok, fail = 0, 0
for i, (old, new) in enumerate(R, 1):
    n = content.count(old)
    if n == 0 and new in content:
        print(f'[{i:02d}] SKIP (already applied)')
        ok += 1
        continue
    if n != 1:
        print(f'[{i:02d}] FAIL (count={n}) :: {old[:60]!r}')
        fail += 1
        continue
    content = content.replace(old, new)
    ok += 1
    print(f'[{i:02d}] OK')

if fail:
    print(f'\n❌ {fail}개 교체 실패 — 파일 미저장')
    sys.exit(1)

# 표준 CRLF로 저장
content = content.replace('\n', '\r\n')

with io.open(PATH, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print(f'\n✅ 패치 저장 완료 ({ok}/{len(R)}) — 개행 CRLF 정규화 포함')
