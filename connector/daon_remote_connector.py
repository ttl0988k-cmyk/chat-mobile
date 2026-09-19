"""

DAON Remote Connector (2026-09-04 v3 — PATCH 스트리밍 + 상태 배지)

================================================

Windows PC에서 실행되는 브리지 에이전트:

  모바일 웹/앱 (Supabase)  ⇄  이 커넥터  ⇄  DAON (127.0.0.1:9090 SSE)

v3 핵심 변경 (2026-09-04):

- INSERT 시 id를 커넥터가 직접 지정(uuid) + Prefer: return=representation

  → 응답 body 누락과 무관하게 msg_id 확보 → 중복 INSERT 폭주 근본 차단

- delta 토큰: 첫 flush 1회 INSERT, 이후 전부 같은 row PATCH → 응답당 row 1개

- 새 응답 시작 시 이전 row 재사용 금지 (msg_ids 초기화)

- 도구 이벤트: 로그 INSERT ❌ → 'status' 배지 row 1개 (PATCH 갱신 → done 시 DELETE)

"""

import os

import sys

import json

import time

import queue

import asyncio

import threading

import logging

import urllib.request

import urllib.error

import urllib.parse

import http.client

import websockets

import uuid

from pathlib import Path

# ── 로깅 설정 ──────────────────────────────────────────────

logging.basicConfig(

    level=logging.INFO,

    format='[%(asctime)s] %(levelname)s %(message)s',

    datefmt='%Y-%m-%d %H:%M:%S'

)

log = logging.getLogger('daon-remote')

# ── 단일 인스턴스 락 ────────────────────────────────────────

_LOCK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'daon_connector.lock')

import socket

_SINGLE_INSTANCE_SOCKET = None

def _acquire_single_instance_lock() -> bool:
    """로컬 TCP 포트(49199) 바인딩 기반 완전한 OS 레벨 단일 인스턴스 보장."""
    global _SINGLE_INSTANCE_SOCKET
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        s.bind(('127.0.0.1', 49199))
        s.listen(1)
        _SINGLE_INSTANCE_SOCKET = s
        log.info('🔒 단일 인스턴스 락 획득 (port=49199, pid=%s)', os.getpid())
        return True
    except OSError:
        log.warning('⚠️ 이미 다른 DAON Connector 프로세스가 실행 중입니다 — 중복 실행 방지 종료 (pid=%s)', os.getpid())
        return False

def _release_single_instance_lock():
    global _SINGLE_INSTANCE_SOCKET
    try:
        if _SINGLE_INSTANCE_SOCKET:
            _SINGLE_INSTANCE_SOCKET.close()
            _SINGLE_INSTANCE_SOCKET = None
    except Exception:
        pass
    try:
        if os.path.exists(_LOCK_PATH):
            os.remove(_LOCK_PATH)
    except Exception:
        pass

# ── 환경 설정 ──────────────────────────────────────────────

def load_env(path: str):

    env = {}

    p = Path(path)

    if p.exists():

        for line in p.read_text(encoding='utf-8', errors='replace').splitlines():

            line = line.strip()

            if '=' in line and not line.startswith('#'):

                k, v = line.split('=', 1)

                env[k.strip()] = v.strip()

    return env

def _locate_env_file():

    """[지인 배포 이식성] .env 를 커넥터 폴더에서 위로 올라가며 찾는다.

    우선순위:

      1) 이 스크립트가 있는 폴더의 .env          <- 배포판 기본 위치

      2) 상위 폴더들의 .env (최대 5단계)

      3) 이전 개발 레이아웃(C:\\daon\\.env)      <- 기존 사용자 호환

    """

    here = Path(__file__).resolve().parent

    candidates = [here / '.env']

    cur = here

    for _ in range(5):

        try:

            cur = cur.parent

        except Exception:

            break

        candidates.append(cur / '.env')

    candidates.append(Path(r'C:\\daon\\.env'))

    for c in candidates:

        try:

            if c.is_file():

                return str(c)

        except Exception:

            continue

    return str(here / '.env')   # 없으면 폴더 옆 경로(오류 메시지용)

_ENV_PATH = _locate_env_file()

ENV = load_env(_ENV_PATH)

if not ENV.get('SUPABASE_URL'):

    print('=' * 62)

    print('[설정 오류] Supabase 설정을 찾지 못했습니다.')

    print('  찾은 경로: ' + _ENV_PATH)

    print('  커넥터 폴더에 .env 파일을 만들고 아래 3줄을 채워주세요:')

    print('    SUPABASE_URL=https://<프로젝트>.supabase.co')

    print('    SUPABASE_ANON_KEY=<anon 키>')

    print('    SUPABASE_SERVICE_ROLE_KEY=<service_role 키>')

    print('=' * 62)


SUPABASE_URL = ENV.get('SUPABASE_URL', '').rstrip('/')

SUPABASE_ANON = ENV.get('SUPABASE_ANON_KEY', '')

SUPABASE_SERVICE = ENV.get('SUPABASE_SERVICE_ROLE_KEY', '')

DAON_URL = 'http://127.0.0.1:9090'

# ── Supabase REST 요청 & 백그라운드 큐 ───────────────────────

_sb_queue = queue.Queue()

def sb_request(method: str, path: str, body=None, service=False):

    """동기 Supabase REST API 호출."""

    key = SUPABASE_SERVICE if service else SUPABASE_ANON

    headers = {'apikey': key, 'Authorization': 'Bearer ' + key}

    if method in ('POST', 'PATCH'):

        # INSERT/UPDATE 시 수정된 행을 응답으로 반환 (msg_id 수신 필수)

        # 이 헤더가 없으면 201 + 빈 body → msg_id 모름 → flush마다 중복 INSERT 폭주 (중복 버그 근본원인)

        headers['Prefer'] = 'return=representation'

    data = None

    if body is not None:

        headers['Content-Type'] = 'application/json'

        if method in ('POST', 'PATCH'):

            headers['Prefer'] = 'return=representation'

        data = json.dumps(body).encode('utf-8')

    req = urllib.request.Request(SUPABASE_URL + path, data=data, headers=headers, method=method)

    try:

        with urllib.request.urlopen(req, timeout=15) as resp:

            raw = resp.read().decode('utf-8', errors='replace')

            try:

                return resp.status, json.loads(raw) if raw else None

            except Exception:

                return resp.status, raw

    except urllib.error.HTTPError as e:

        body_text = ''

        try:

            body_text = e.read().decode('utf-8', errors='replace')

        except Exception:

            pass

        log.error('Supabase HTTP %s %s: %s — body: %s', method, path, e.code, body_text[:200])

        return e.code, body_text

    except Exception as e:

        log.error('Supabase 요청 예외: %s — %s %s', e, method, path)

        return None, str(e)

def _sb_worker():

    """백그라운드 Supabase 요청 워커 (SSE 블로킹 방지)."""

    while True:

        item = _sb_queue.get()

        if item is None:

            break

        try:

            method, path, body, service = item

            sb_request(method, path, body, service=service)

        except Exception as e:

            log.error('SB 워커 예외: %s', e)

        finally:

            _sb_queue.task_done()

def queue_sb_request(method, path, body=None, service=False):

    """비동기 큐에 Supabase 요청 넣기 (응답 기다리지 않음)."""

    try:

        _sb_queue.put_nowait((method, path, body, service))

    except Exception as e:

        log.error('큐 등록 실패: %s', e)

# 백그라운드 워커 시작

threading.Thread(target=_sb_worker, daemon=True, name='sb-worker').start()
# [fix 09-09] FK 409 방지 — assistant 응답 INSERT 전 대화 row 존재 보장
def _ensure_conversation(conv_id: str, user_id):
    """폰 앱이 conversation 생성 실패/지연했을 때 커넥터가 보완 생성."""
    try:
        st, res = sb_request('GET', '/rest/v1/conversations?id=eq.' + conv_id + '&select=id', service=True)
        if st == 200 and isinstance(res, list) and len(res) > 0:
            return True
        st2, res2 = sb_request('POST', '/rest/v1/conversations', {
            'id': conv_id,
            'user_id': user_id or None,
            'device': 'mobile',
            'title': '대화(복원)',
        }, service=True)
        if st2 in (200, 201):
            log.info('🛟 conversation 보완 생성 conv=%s', conv_id[:8])
            return True
        log.warning('conversation 보완 생성 실패 status=%s: %s', st2, str(res2)[:100])
        return False
    except Exception as e:
        log.warning('conversation 보완 예외: %s', e)
        return False
# [fix 09-09] reasoning 뱃지 스로틀
_REASONING_LAST = {}

# ── 토큰 스트리밍 디바운서 (v2 — 중복 INSERT 방지) ─────────

class DeltaStreamManager:

    def __init__(self):

        self.buffers = {}            # conv_id -> text

        self.msg_ids = {}            # conv_id -> msg_id in supabase (재응답 시 PATCH용)

        self.last_flush = {}         # conv_id -> timestamp

        self.user_ids = {}           # conv_id -> user_id

        self.stream_ids = {}         # conv_id -> stream_id

        self.lock = threading.Lock()

    def add_token(self, conv_id: str, user_id: str, stream_id: str, text: str):
        with self.lock:
            prev_stream = self.stream_ids.get(conv_id)
            if prev_stream is not None and prev_stream != stream_id:
                log.info('🔄 새 스트림 감지 (이전=%s, 현재=%s) — 이전 버퍼 및 msg_id 초기화',
                         prev_stream[:8] if prev_stream else 'None', stream_id[:8] if stream_id else 'None')
                self.buffers.pop(conv_id, None)
                self.msg_ids.pop(conv_id, None)
                self.last_flush.pop(conv_id, None)

            first_token = conv_id not in self.buffers
            if first_token:
                # [v3] 새 응답 시작 — 이전 응답의 row를 재사용하지 않음
                self.msg_ids.pop(conv_id, None)
            self.buffers[conv_id] = self.buffers.get(conv_id, '') + text

            self.user_ids[conv_id] = user_id

            self.stream_ids[conv_id] = stream_id

            now = time.time()

            if first_token or now - self.last_flush.get(conv_id, 0.0) >= 0.2:

                self._flush_locked(conv_id, is_done=False)

                self.last_flush[conv_id] = now

    def flush_now(self, conv_id: str, session_id: str = None):

        """도구 사용/외부 이벤트 시점에 강제 flush. 모바일 heartbeat 유지용."""

        with self.lock:

            self._flush_locked(conv_id, is_done=False, session_id=session_id)

            self.last_flush[conv_id] = time.time()

    def finish(self, conv_id: str, session_id: str = None):

        with self.lock:

            self._flush_locked(conv_id, is_done=True, session_id=session_id)

            # [v2] msg_ids/inserted_streams는 보존 — 다음 응답에서 같은 conv_id 재사용 시

            # 새 row INSERT 후 PATCH로 자연스러운 스트리밍 유지.

            self.buffers.pop(conv_id, None)

            self.last_flush.pop(conv_id, None)

            self.user_ids.pop(conv_id, None)

            self.stream_ids.pop(conv_id, None)

            self.msg_ids.pop(conv_id, None)  # [v3] 다음 응답은 반드시 새 row

    def cancel(self, conv_id: str):
        """스트림 취소 시 버퍼와 msg_id를 즉시 완전 삭제하여 다음 응답이 이전 row에 덮어써지지 않도록 보장."""
        with self.lock:
            log.info('🧹 DeltaStreamManager.cancel 호출 — conv=%s', (conv_id or '')[:8])
            self.buffers.pop(conv_id, None)
            self.last_flush.pop(conv_id, None)
            self.user_ids.pop(conv_id, None)
            self.stream_ids.pop(conv_id, None)
            self.msg_ids.pop(conv_id, None)

    def _flush_locked(self, conv_id: str, is_done=False, session_id=None):

        text = self.buffers.get(conv_id, '')

        if not text and not is_done:

            return

        msg_id = self.msg_ids.get(conv_id)

        user_id = self.user_ids.get(conv_id)

        stream_id = self.stream_ids.get(conv_id)

        meta = {

            'type': 'complete' if is_done else 'delta',

            'stream_id': stream_id,

        }

        if session_id:

            meta['session'] = session_id

        content = text or ('✅ 완료' if is_done else '')

        if msg_id is None:

            _ensure_conversation(conv_id, user_id)
            # [v3] row 1개 INSERT — id를 커넥터가 직접 지정 → 응답 body 없이도 PATCH 가능

            row_id = str(uuid.uuid4())

            status, res = sb_request('POST', '/rest/v1/messages', {

                'id': row_id,

                'conversation_id': conv_id,

                'user_id': user_id,

                'role': 'assistant',

                'content': content,

                'metadata': meta,

            }, service=True)

            if status not in (200, 201):
                time.sleep(0.5)
                status, res = sb_request('POST', '/rest/v1/messages', {
                    'id': row_id,
                    'conversation_id': conv_id,
                    'user_id': user_id,
                    'role': 'assistant',
                    'content': content,
                    'metadata': meta,
                }, service=True)
            if status in (200, 201):
                self.msg_ids[conv_id] = row_id
                log.info('✅ 메시지 INSERT (conv=%s…, stream=%s…, msg_id=%s)',
                         conv_id[:8], (stream_id or '')[:8], row_id)
            else:
                log.error('❌ assistant INSERT 실패 status=%s — 유령 msg_id 등록 방지: %s',
                          status, str(res)[:120])

        else:

            # 동일 행 PATCH 업데이트 (새 행 생성 금지)

            queue_sb_request('PATCH', f'/rest/v1/messages?id=eq.{msg_id}', {

                'content': content,

                'metadata': meta,

            }, service=True)

_delta_mgr = DeltaStreamManager()

# ── 작업 상태 배지 관리 (v3 — "생각중/작업중" row 1개) ──────

class StatusRowManager:

    """conv당 status row 1개: 도구 이벤트 → INSERT 1회, 이후 PATCH 갱신, done 시 DELETE."""

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


# ── DAON 모델 동기화 (모바일 연동) ─────────────────────────
import hashlib

_LAST_MODELS_HASH = None

def fetch_daon_models():
    """DAON 백엔드(9090 /api/models) 또는 로컬 custom_providers.json에서 모델 목록을 조회합니다."""
    # 1) 127.0.0.1:9090 /api/models 시도
    try:
        req = urllib.request.Request('http://127.0.0.1:9090/api/models')
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                groups = data.get('groups', [])
                def_model = data.get('default_model') or 'MiniMax-M3'
                if groups:
                    return _process_model_groups(groups, def_model)
    except Exception as e:
        log.debug('DAON 9090 /api/models 조회 실패: %s', e)

    # 2) 로컬 custom_providers.json 시도
    candidates = [
        Path(os.environ.get('LOCALAPPDATA', '')) / 'DAON Agent System' / 'data' / 'custom_providers.json',
        Path(os.environ.get('LOCALAPPDATA', '')) / 'daon-agent-system' / 'data' / 'custom_providers.json',
        Path(r'C:\daon\Daon agent System\data\custom_providers.json'),
    ]
    for cp in candidates:
        if cp.exists():
            try:
                raw = json.loads(cp.read_text(encoding='utf-8-sig'))
                providers = raw.get('providers', {})
                if providers:
                    groups = []
                    for pname, pcfg in providers.items():
                        models = pcfg.get('models', [])
                        c_models = []
                        for m in models:
                            mid = m.get('id') if isinstance(m, dict) else str(m)
                            mlabel = m.get('label') if isinstance(m, dict) else mid
                            mtype = m.get('type', 'chat') if isinstance(m, dict) else 'chat'
                            c_models.append({'id': mid, 'label': mlabel, 'type': mtype})
                        groups.append({
                            'provider': pcfg.get('label') or pname,
                            'provider_key': pname,
                            'models': c_models
                        })
                    return _process_model_groups(groups, 'MiniMax-M3')
            except Exception as e:
                log.warning('custom_providers.json 읽기 실패(%s): %s', cp, e)

    return None, None, None

def _process_model_groups(raw_groups, default_model):
    clean_groups = []
    flat_models = []
    for g in raw_groups:
        pname = g.get('provider') or 'Custom'
        c_models = []
        for m in g.get('models', []):
            mid = m.get('id') if isinstance(m, dict) else str(m)
            mlabel = (m.get('label') if isinstance(m, dict) else mid) or mid
            mtype = (m.get('type') if isinstance(m, dict) else 'chat') or 'chat'
            c_models.append({'id': mid, 'label': mlabel, 'type': mtype})
            flat_models.append({'provider': pname, 'id': mid, 'label': mlabel, 'type': mtype})
        clean_groups.append({
            'provider': pname,
            'provider_key': g.get('provider_key') or pname.lower(),
            'models': c_models
        })
    return clean_groups, flat_models, default_model

def sync_models_to_supabase_and_config():
    """등록된 프로바이더 모델 목록을 Supabase agent_memory 및 mobile config.js 에 동기화합니다."""
    global _LAST_MODELS_HASH
    clean_groups, flat_models, default_model = fetch_daon_models()
    if not clean_groups:
        return False

    model_data_for_hash = json.dumps({'g': clean_groups, 'd': default_model}, sort_keys=True)
    mhash = hashlib.md5(model_data_for_hash.encode('utf-8')).hexdigest()
    if mhash == _LAST_MODELS_HASH:
        return True
    content_dict = {
        'groups': clean_groups,
        'models': flat_models,
        'default_model': default_model or 'MiniMax-M3',
        'updated_at': time.time(),
    }
    content_json = json.dumps(content_dict, ensure_ascii=False)

    # 1) config.js 자동 갱신 — [FIX 2026-09-12] 폐기
    #   ⚠️ 기존 구현은 config.js 전체를 DAON /api/models 결과로 '덮어쓰기' 했다.
    #      그 결과 DAON 에 없는 프로바이더(예: DeepSeek)와 window.APP_PASSWORD 가
    #      통째로 사라져 모바일 앱에서 모델 목록이 0개로 보이는 장애가 발생했다.
    #      (2026-09-12 실제 발생: 50개 -> 46개, APP_PASSWORD 소실, 로그인 불가)
    #   ▸ 이후 config.js 는 git/Vercel 로 관리한다.
    #   ▸ 실시간 모델 동기화는 Supabase agent_memory(key=available_models) 경로를 그대로 사용한다.
    #   ▸ 아래는 참고용 스냅샷만 남기며, config.js 는 절대 자동으로 덮어쓰지 않는다.
    try:
        ref_path = Path(__file__).resolve().parent / 'live_models.json'
        ref_path.write_text(
            json.dumps({
                'groups': clean_groups,
                'models': flat_models,
                'default_model': default_model or 'MiniMax-M3',
                'updated_at': time.time(),
            }, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        log.info('[SAFE] live_models.json 기록 완료 (%d개 모델) — config.js 는 보존됨', len(flat_models))
    except Exception as e:
        log.warning('live_models.json 기록 예외: %s', e)

    # 2) Supabase Auth 사용자 조회 및 agent_memory upsert
    try:
        status, u_data = sb_request('GET', '/auth/v1/admin/users', service=True)
        user_ids = []
        if isinstance(u_data, dict) and 'users' in u_data:
            for u in u_data['users']:
                if u.get('id'):
                    user_ids.append(u['id'])
        if not user_ids:
            user_ids = ['2e8e15e5-73bf-483f-bc96-5094cf2d9a01']

        for uid in user_ids:
            st, rows = sb_request('GET', f'/rest/v1/agent_memory?key=eq.available_models&user_id=eq.{uid}', service=True)
            if isinstance(rows, list) and len(rows) > 0:
                rid = rows[0]['id']
                sb_request('PATCH', f'/rest/v1/agent_memory?id=eq.{rid}', {
                    'content': content_json,
                    'metadata': {'type': 'system_models', 'count': len(flat_models), 'updated_at': time.time()}
                }, service=True)
            else:
                sb_request('POST', '/rest/v1/agent_memory', {
                    'user_id': uid,
                    'target': 'user',
                    'key': 'available_models',
                    'content': content_json,
                    'confidence': 1.0,
                    'metadata': {'type': 'system_models', 'count': len(flat_models), 'updated_at': time.time()}
                }, service=True)

        _LAST_MODELS_HASH = mhash
        log.info('🔄 DAON 프로바이더 모델 Supabase 동기화 성공: %d개 그룹, %d개 모델 (사용자 %d명)',
                 len(clean_groups), len(flat_models), len(user_ids))
        return True
    except Exception as e:
        log.error('Supabase 모델 동기화 예외: %s', e)
        return False

def _model_sync_worker():
    """백그라운드에서 주기적으로 DAON 프로바이더 모델 동기화 및 미답변 메시지 점검."""
    while True:
        try:
            sync_models_to_supabase_and_config()
            check_pending_user_messages()
        except Exception as e:
            log.debug('백그라운드 워커 오류: %s', e)
        time.sleep(15)


# ── DAON 로컬 API ──────────────────────────────────────────

def daon_new_session(model: str = None):

    body = {}

    if model:

        body['model'] = model

    data = json.dumps(body).encode('utf-8')

    conn = http.client.HTTPConnection('127.0.0.1', 9090, timeout=60)

    try:

        conn.request('POST', '/api/session/new', body=data, headers={'Content-Type': 'application/json'})

        resp = conn.getresponse()

        raw = resp.read().decode('utf-8')

        if resp.status != 200:

            log.error('DAON 세션 생성 실패 %s: %s', resp.status, raw[:200])

            return None

        return json.loads(raw).get('session', {}).get('session_id')

    except Exception as e:

        log.error('DAON 세션 생성 예외: %s', e)

        return None

    finally:

        conn.close()

def _storage_public_url(bucket: str, path: str) -> str:

    """Supabase Storage public URL 생성."""

    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"

def daon_start_chat(session_id: str, message: str, model: str = None, image_urls: list = None):

    body = {'session_id': session_id, 'message': message}

    if model:

        body['model'] = model

    if image_urls:

        body['image_urls'] = image_urls

    data = json.dumps(body).encode('utf-8')

    conn = http.client.HTTPConnection('127.0.0.1', 9090, timeout=10)

    try:

        conn.request('POST', '/api/chat/start', body=data, headers={'Content-Type': 'application/json'})

        resp = conn.getresponse()

        raw = resp.read().decode('utf-8')

        if resp.status != 200:

            log.error('DAON start 실패 %s: %s', resp.status, raw[:200])

            return None

        return json.loads(raw)

    except Exception as e:

        log.error('DAON start 예외: %s', e)

        return None

    finally:

        conn.close()

def daon_sse_stream(stream_id: str, on_event):

    """DAON SSE 스트림을 수신하며 on_event를 호출 (타임아웃 방어)."""

    conn = http.client.HTTPConnection('127.0.0.1', 9090, timeout=180)

    path = '/api/chat/stream?stream_id=' + urllib.parse.quote(stream_id)

    try:

        conn.request('GET', path)

        resp = conn.getresponse()

        if resp.status != 200:

            log.error('DAON SSE 실패 status=%s', resp.status)

            return

        event = None

        data_lines = []

        while True:

            line = resp.readline()

            if not line:

                break

            line = line.decode('utf-8', errors='replace').rstrip('\r\n')

            if line.startswith('event:'):

                event = line[len('event:'):].strip()

            elif line.startswith('data:'):

                data_lines.append(line[len('data:'):].strip())

            elif line == '':

                if event and data_lines:

                    try:

                        payload = json.loads('\n'.join(data_lines))

                    except Exception:

                        payload = {'raw': '\n'.join(data_lines)}

                    if event not in ('token', 'done', 'reasoning'):

                        log.info('📨 SSE event=%s keys=%s', event,

                                 list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__)

                    if on_event(event, payload) is False:

                        log.info('SSE 종료 이벤트(%s) 수신', event)

                        return

                event = None

                data_lines = []

    except Exception as e:

        log.error('DAON SSE 예외: %s', e)

    finally:

        conn.close()

# ── 자율 실행 모드 및 승인 제어 ────────────────────────────

_AUTO_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'connector_state.json')

def _load_auto_approve() -> bool:

    try:

        with open(_AUTO_STATE_PATH, 'r', encoding='utf-8') as f:

            return bool(json.load(f).get('auto_approve'))

    except Exception:

        return False

def _save_auto_approve(v: bool) -> None:

    try:

        st = {}

        if os.path.exists(_AUTO_STATE_PATH):

            with open(_AUTO_STATE_PATH, 'r', encoding='utf-8') as f:

                st = json.load(f)

        st['auto_approve'] = bool(v)

        with open(_AUTO_STATE_PATH, 'w', encoding='utf-8') as f:

            json.dump(st, f)

    except Exception as e:

        log.warning('자율실행 상태 저장 실패: %s', e)

_AUTO_APPROVE = _load_auto_approve()

def daon_approval(session_id: str, approve: bool, reason: str = ''):

    choice = 'once' if approve else 'deny'

    body = {'session_id': session_id, 'choice': choice}

    if not approve and reason:

        body['reason'] = reason

    data = json.dumps(body).encode('utf-8')

    ok = False

    conn = http.client.HTTPConnection('127.0.0.1', 9090, timeout=15)

    try:

        conn.request('POST', '/api/approval/respond', body=data, headers={'Content-Type': 'application/json'})

        resp = conn.getresponse()

        resp.read()

        ok = (resp.status == 200)

    except Exception as e:

        log.error('DAON 승인 응답 예외: %s', e)

    finally:

        conn.close()

    return ok

def daon_cancel(stream_id: str, session_id: str):

    body = {'stream_id': stream_id, 'session_id': session_id}

    data = json.dumps(body).encode('utf-8')

    conn = http.client.HTTPConnection('127.0.0.1', 9090, timeout=15)

    try:

        conn.request('POST', '/api/chat/cancel', body=data, headers={'Content-Type': 'application/json'})

        resp = conn.getresponse()

        resp.read()

        return resp.status == 200

    except Exception as e:

        log.error('DAON 취소 예외: %s', e)

        return False

    finally:

        conn.close()

# ── 메시지 디스패치 및 이벤트 처리 ──────────────────────────

_CONV_SESSIONS = {}   # conversation_id -> session_id

_CONV_STREAMS = {}    # conversation_id -> stream_id

# 대화-세션 매핑 영속화 (ChatGPT 스타일 대화 이어짐)

# 커넥터 재시작/PC 재부팅 후에도 같은 대화는 같은 DAON 세션으로 이어짐.

# DAON 세션 자체는 sessions/*.json으로 영속되므로, 매핑만 잃지 않으면

# 에이전트가 이전 맥락(작업 내역)을 그대로 기억함.

_CONV_MAP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'conv_sessions.json')

def _load_conv_sessions():

    try:

        if os.path.exists(_CONV_MAP_PATH):

            with open(_CONV_MAP_PATH, 'r', encoding='utf-8') as f:

                data = json.load(f)

            if isinstance(data, dict):

                _CONV_SESSIONS.update(data)

                log.info('매핑 복원: 대화-세션 %d건', len(data))

    except Exception as e:

        log.warning('매핑 로드 실패(무시): %s', e)

def _save_conv_sessions():

    try:

        with open(_CONV_MAP_PATH, 'w', encoding='utf-8') as f:

            json.dump(dict(_CONV_SESSIONS), f, ensure_ascii=False, indent=1)

    except Exception as e:

        log.warning('매핑 저장 실패(무시): %s', e)

_load_conv_sessions()

# 중복 수신 방지 (Realtime 재전송/재접속 리플레이 대비)

_PROC_MSGS = set()

_PROC_ORDER = []

_PROC_LOCK = threading.Lock()

def _mark_processed(msg_id):

    '''처리 이력 있으면 False(스킵), 처음이면 True.'''

    if not msg_id:

        return True

    with _PROC_LOCK:

        if msg_id in _PROC_MSGS:

            return False

        _PROC_MSGS.add(msg_id)

        _PROC_ORDER.append(msg_id)

        if len(_PROC_ORDER) > 1000:

            for old in _PROC_ORDER[:500]:

                _PROC_MSGS.discard(old)

            del _PROC_ORDER[:500]

        return True

def _unmark_processed(msg_id):

    '''[FIX 2026-09-14] 처리 실패 시 이력을 해제하여 자동 재시도를 허용한다.

    기존에는 handle_user_message 진입 직후 이력이 등록되고 실패해도 그대로 남아
    로그온 직후(DAON 서버 부팅 전) 들어온 메시지가 영구히 재시도되지 않았다.'''

    if not msg_id:

        return

    with _PROC_LOCK:

        _PROC_MSGS.discard(msg_id)

        try:

            _PROC_ORDER.remove(msg_id)

        except ValueError:

            pass


def _post_error_message(conv_id, user_id, content, msg_id=None):

    '''[FIX 2026-09-14] 오류 안내를 1개만 유지하고, 실패한 유저 메시지는 재시도 가능하게 해제한다.

    - 재시도 이력 해제(_unmark_processed) → 다음 점검 주기에서 다시 시도된다
    - 기존 오류 메시지가 있으면 PATCH 로 내용만 갱신 → 채팅창에 경고가 쌓이지 않는다'''

    _unmark_processed(msg_id)

    try:

        _, existing = sb_request('GET', '/rest/v1/messages?conversation_id=eq.' + conv_id + '&role=eq.assistant&metadata->>type=eq.error&order=created_at.desc&limit=1', service=True)

        if isinstance(existing, list) and existing:

            eid = existing[0].get('id')

            if eid:

                queue_sb_request('PATCH', '/rest/v1/messages?id=eq.' + str(eid), {'content': content}, service=True)

                return

    except Exception as e:

        log.debug('기존 오류 메시지 조회 실패(신규 생성으로 진행): %s', e)

    queue_sb_request('POST', '/rest/v1/messages', {

        'conversation_id': conv_id,

        'user_id': user_id,

        'role': 'assistant',

        'content': content,

        'metadata': {'type': 'error'},

    }, service=True)

# 대화별 직렬화 락 (동시 수신 시 세션 이중 생성 방지)

_SESS_LOCKS = {}

_SESS_LOCKS_LOCK = threading.Lock()

def _conv_lock(conv_id):

    with _SESS_LOCKS_LOCK:

        if conv_id not in _SESS_LOCKS:

            _SESS_LOCKS[conv_id] = threading.Lock()

        return _SESS_LOCKS[conv_id]

def handle_user_message(msg):

    global _AUTO_APPROVE

    conv_id = msg.get('conversation_id')

    user_id = msg.get('user_id')

    content = (msg.get('content') or '').strip()

    meta = msg.get('metadata') or {}

    mtype = meta.get('type', '') if isinstance(meta, dict) else ''

    req_model = meta.get('model', '') if isinstance(meta, dict) else ''

    if not conv_id:

        return

    _known_sid = _CONV_SESSIONS.get(conv_id)

    log.info('📩 모바일 메시지 type=%s conv=%s session=%s: %s',

             mtype or 'chat', conv_id[:8], (_known_sid or 'NEW')[:8], content[:80])

    if not _mark_processed(msg.get('id')):

        log.info('중복 수신 스킵 msg=%s', str(msg.get('id'))[:8])

        return

    if mtype == 'approval_response':

        session_id = meta.get('session_id') or _CONV_SESSIONS.get(conv_id)

        if session_id:

            # [2026-09-19] 브라우저 에이전트 계약과 동일하게 is_dangerous 를 인지한다.
            #   위험 명령(dangerous_command)이든 일반 도구 승인이든 DAON 서버의
            #   /api/approval/respond 가 resolve_gateway_approval 로 일괄 처리하므로
            #   라우팅은 동일하되, 로그/추적을 위해 is_dangerous 를 함께 남긴다.
            _is_dangerous = bool(meta.get('is_dangerous'))

            log.info('✅ 승인 응답 수신: session=%s approved=%s dangerous=%s',

                     session_id[:8], bool(meta.get('approved')), _is_dangerous)

            daon_approval(session_id, bool(meta.get('approved')), reason=meta.get('reason', ''))

        return

    if mtype == 'autonomous_toggle':

        _AUTO_APPROVE = bool(meta.get('enabled'))

        _save_auto_approve(_AUTO_APPROVE)

        queue_sb_request('POST', '/rest/v1/messages', {

            'conversation_id': conv_id,

            'user_id': user_id,

            'role': 'tool',

            'content': '🤖 자율 실행 모드 ON — 승인 요청을 자동 승인합니다.' if _AUTO_APPROVE else '🛡️ 일반 실행 모드 — 승인 요청마다 확인합니다.',

            'metadata': {'type': 'notice', 'auto': _AUTO_APPROVE},

        }, service=True)

        return

    if mtype == 'interrupt':

        stream_id = meta.get('stream_id') or _CONV_STREAMS.get(conv_id)

        session_id = meta.get('session_id') or _CONV_SESSIONS.get(conv_id)

        if stream_id and session_id:

            daon_cancel(stream_id, session_id)

        # [수정] 상태 배지 제거 + 세션 정리 → 다음 작업 재개 가능

        _status_mgr.clear(conv_id)
        _delta_mgr.cancel(conv_id)
        _CONV_STREAMS.pop(conv_id, None)

        # 세션은 유지 (대화 컨텍스트 보존)

        # 새 메시지 시 세션 재사용 시도 → 실패 시 새 세션 자동 생성 (1015~1024 로직)

        queue_sb_request('POST', '/rest/v1/messages', {
            'conversation_id': conv_id,
            'user_id': user_id,
            'role': 'assistant',
            'content': '⏹️ 작업이 취소되었습니다.',
            'metadata': {'type': 'notice'},
        }, service=True)

        log.info('✅ interrupt 처리 완료 — conv=%s, stream=%s', conv_id, stream_id)
        return

    if not content:

        return

    # 세션 획득

    with _conv_lock(conv_id):

        # [FIX 2026-09-11] null 매핑은 전확한 falsy 처리 (이면 다시 생성)
        existing = _CONV_SESSIONS.get(conv_id)
        if not existing:
            # 더 깎대: conv_sessions.json 에서 null 조합을 제거하고 실제 세션이 있는지 확인
            if existing is None:
                _CONV_SESSIONS.pop(conv_id, None)
                _save_conv_sessions()
            _CONV_SESSIONS[conv_id] = daon_new_session(model=req_model or None)
            _save_conv_sessions()

            

            if not _CONV_SESSIONS.get(conv_id):

                _post_error_message(conv_id, user_id, '⚠️ DAON 서버 연결 불가 (127.0.0.1:9090 확인 필요)', msg.get('id'))

                return

    session_id = _CONV_SESSIONS[conv_id]

    start = daon_start_chat(session_id, content, model=req_model or None)

    if not start:
        log.info('기존 세션(%s) 만료 또는 실패 감지 — 새 세션 자동 생성 후 재시도: conv=%s', session_id, conv_id)
        _CONV_SESSIONS.pop(conv_id, None)
        session_id = daon_new_session(model=req_model or None)
        if session_id:
            _CONV_SESSIONS[conv_id] = session_id
            _save_conv_sessions()
            start = daon_start_chat(session_id, content, model=req_model or None)

    if not start:

        _post_error_message(conv_id, user_id, '⚠️ DAON 작업 시작 실패 (서버 실행 상태 확인 필요)', msg.get('id'))

        return

    stream_id = start.get('stream_id')

    if not stream_id:

        log.error('stream_id 누락: %s', start)

        return

    _CONV_STREAMS[conv_id] = stream_id

    def on_event(event, data):
        # 만약 이 스트림이 이미 취소되었거나 다른 새 스트림으로 교체되었다면 오래된 이벤트는 즉시 무시
        if _CONV_STREAMS.get(conv_id) != stream_id:
            return False

        if event == 'token':

            text = data.get('text', '')

            _delta_mgr.add_token(conv_id, user_id, stream_id, text)

        elif event == 'done':

            _status_mgr.clear(conv_id)  # [v3] 상태 배지 제거

            _delta_mgr.finish(conv_id, session_id=session_id)

            return False  # 스트림 종료

        elif event == 'tool':

            t_name = data.get('name', '도구')

            t_ev = data.get('event', '')

            t_raw = str(data.get('output') or data.get('args') or '')

            log.info('🔧 [tool %s %s] %s', t_name, t_ev, t_raw[:200])

            _delta_mgr.flush_now(conv_id, session_id=session_id)

            # [v3] 도구 로그 INSERT 금지 → 상태 배지 1개로 간단 표시

            if t_name == '_thinking':

                _status_mgr.update(conv_id, user_id, '💭 생각중…')

            else:

                _status_mgr.update(conv_id, user_id, '🔧 작업중… (' + t_name + ')')

        elif event == 'approval':

            _status = str(data.get('status') or 'pending')

            _subj = str(data.get('command') or data.get('cmd') or data.get('message') or '?')

            log.info('🔐 [approval %s] %s', _status, _subj)

            if _status == 'pending' and _AUTO_APPROVE:

                _ok2 = daon_approval(session_id, True)

                log.info('🤖 자율실행 자동승인 ok=%s', _ok2)

            _delta_mgr.flush_now(conv_id, session_id=session_id)

            # [v3] 승인 대기/자동승인 상태 배지

            if _status == 'pending' and not _AUTO_APPROVE:

                _status_mgr.update(conv_id, user_id, '🔐 승인 대기중…')

                # [v3] 모바일 승인가드 렌더링: messages 테이블에 INSERT

                _approval_msg = _subj

                _approval_desc = str(data.get('description') or '')

                _approval_type = str(data.get('type') or '')

                _approval_sid = str(data.get('session_id') or session_id or '')

                if _approval_desc and _approval_msg and _approval_msg != '?':
                    _card_text = f'⚠️ 승인 필요\n\n명령 실행을 허용할까요?\n\n📋 사유: {_approval_desc}\n\n💻 실행 명령:\n{_approval_msg}'
                elif _approval_msg and _approval_msg != '?':
                    _card_text = f'⚠️ 승인 필요\n\n명령 실행을 허용할까요?\n\n💻 실행 명령:\n{_approval_msg}'
                elif _approval_desc:
                    _card_text = f'⚠️ 승인 필요\n\n명령 실행을 허용할까요?\n\n📋 {_approval_desc}'
                else:
                    _card_text = '⚠️ 승인 필요\n\n명령 실행을 허용할까요?'

                queue_sb_request('POST', '/rest/v1/messages', {

                    'conversation_id': conv_id,

                    'user_id': user_id,

                    'role': 'tool',

                    'content': _card_text,

                    'metadata': {

                        'type': 'approval',

                        'data': {

                            'status': 'pending',

                            'session_id': _approval_sid,

                            'type': _approval_type,

                            'description': _approval_desc,

                            'message': _subj,

                        }

                    }

                }, service=True)

            else:

                _status_mgr.update(conv_id, user_id, '💭 생각중…')

            return True

        elif event == 'reasoning':
            # [fix 09-09] 사고 중 뱃지 갱신(긴 구간 폰 화면 정지 방지) — 5초 스로틀
            if time.time() - _REASONING_LAST.get(conv_id, 0.0) >= 5.0:
                _REASONING_LAST[conv_id] = time.time()
                _status_mgr.update(conv_id, user_id, '💭 생각중…')
        elif event in ('error', 'apierror', 'apperror'):

            msg_text = data.get('message', data.get('error', '오류'))

            _status_mgr.clear(conv_id)  # [v3] 상태 배지 제거

            queue_sb_request('POST', '/rest/v1/messages', {

                'conversation_id': conv_id,

                'user_id': user_id,

                'role': 'assistant',

                'content': f'❌ {msg_text}',

                'metadata': {'type': 'error'},

            }, service=True)

            return False

        elif event == 'cancel':
            _status_mgr.clear(conv_id)  # [v3] 상태 배지 제거
            _delta_mgr.cancel(conv_id)   # [중요] 이전 스트림 버퍼와 msg_id 완전 초기화
            if _CONV_STREAMS.get(conv_id) == stream_id:
                _CONV_STREAMS.pop(conv_id, None)

            queue_sb_request('POST', '/rest/v1/messages', {

                'conversation_id': conv_id,

                'user_id': user_id,

                'role': 'assistant',

                'content': '⏹️ 작업이 취소되었습니다.',

                'metadata': {'type': 'notice'},

            }, service=True)

            return False

        return True

    _stream_ended = {'ok': False}
    def _wrapped_event(_ev, _data):
        _r = on_event(_ev, _data)
        if _r is False:
            _stream_ended['ok'] = True
        return _r
    daon_sse_stream(stream_id, _wrapped_event)
    # [fix 09-09] done/error/cancel 없이 연결 끊김 — 잔여 응답 마무리 + 폰 통지
    if not _stream_ended['ok']:
        if _CONV_STREAMS.get(conv_id) == stream_id:
            log.warning('⚠️ SSE 비정상 종료 감지 — 잔여 버퍼 마무리 + 폰 통지 (conv=%s)', conv_id[:8])
            _status_mgr.clear(conv_id)
            _CONV_STREAMS.pop(conv_id, None)
            if _delta_mgr.buffers.get(conv_id):
                _delta_mgr.finish(conv_id, session_id=session_id)
            queue_sb_request('POST', '/rest/v1/messages', {
                'conversation_id': conv_id,
                'user_id': user_id,
                'role': 'assistant',
                'content': '⚠️ 연결이 끊겨 응답이 중단되었습니다. 다시 시도해 주세요.',
                'metadata': {'type': 'notice'},
            }, service=True)
        else:
            log.info('SSE 종료(stale 스트림) — 보완 처리 생략')

# ── Supabase Realtime 웹소켓 루프 (무중단 하트비트) ─────────

_ERR_RETRY_MAX = 6

_ERR_RETRY_COOLDOWN = 20.0

_ERR_RETRY_STATE = {}

_ERR_RETRY_LOCK = threading.Lock()


def check_pending_user_messages():

    '''커넥터 시작 시 또는 재연결 시 최근 미처리된 유저 메시지를 자동 감지하여 실행합니다.

    [FIX 2026-09-14] 로그온 순서 가드 — 오류 안내(type=error)를 실제 답변으로 오인해 자동 재시도가
    영구 차단되던 버그를 고친다. 재시도 폭주 방지용 쿨다운/최대 횟수 가드 포함.'''

    try:

        status, msgs = sb_request('GET', '/rest/v1/messages?role=eq.user&order=created_at.desc&limit=5', service=True)

        if not isinstance(msgs, list) or not msgs:

            return

        for m in reversed(msgs):

            mid = m.get('id')

            cid = m.get('conversation_id')

            cts = m.get('created_at')

            if not mid or not cid:

                continue

            with _PROC_LOCK:

                if mid in _PROC_MSGS:

                    continue

            q_cts = urllib.parse.quote(cts) if cts else ''

            _, replies = sb_request('GET', '/rest/v1/messages?conversation_id=eq.' + cid + '&role=eq.assistant&created_at=gt.' + q_cts + '&order=created_at.asc&limit=10', service=True)

            if not isinstance(replies, list):

                continue

            real = [r for r in replies if (r.get('metadata') or {}).get('type') != 'error']

            if real:

                continue

            if replies:

                with _ERR_RETRY_LOCK:

                    st = _ERR_RETRY_STATE.setdefault(mid, {'count': 0, 'last': 0.0})

                    now = time.time()

                    if st['count'] >= _ERR_RETRY_MAX:

                        continue

                    if now - st['last'] < _ERR_RETRY_COOLDOWN:

                        continue

                    st['count'] += 1

                    st['last'] = now

                    nth = st['count']

                    if len(_ERR_RETRY_STATE) > 500:

                        for _k in list(_ERR_RETRY_STATE.keys())[:250]:

                            _ERR_RETRY_STATE.pop(_k, None)

                log.info('🚀 [오류 자동 재시도 %d/%d] conv=%s: %s', nth, _ERR_RETRY_MAX, cid[:8], (m.get('content') or '')[:50])

            else:

                log.info('🚀 [미처리 유저 메시지 감지] conv=%s: %s (자동 처리 시작)', cid[:8], (m.get('content') or '')[:50])

            threading.Thread(target=handle_user_message, args=(m,), daemon=True).start()

    except Exception as e:

        log.warning('미처리 메시지 확인 예외: %s', e)

def realtime_ws_url():

    host = SUPABASE_URL.replace('https://', 'wss://').replace('http://', 'ws://')

    return f"{host}/realtime/v1/websocket?apikey={SUPABASE_SERVICE}&vsn=1.0.0"

async def realtime_loop():

    url = realtime_ws_url()

    log.info('Realtime WS 연결 시도: %s...', url[:80])

    backoff = 3.0

    while True:

        try:

            async with websockets.connect(

                url,

                ping_interval=15,

                ping_timeout=10,

                close_timeout=5,

                max_size=10 * 1024 * 1024

            ) as ws:

                log.info('✅ Supabase Realtime WS 연결 성공')

                backoff = 3.0

                join_msg = {

                    "topic": "realtime:daon-remote",

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

                async def _phoenix_heartbeat():

                    ref = 100

                    while True:

                        await asyncio.sleep(25)

                        try:

                            hb = {"topic": "phoenix", "event": "heartbeat", "payload": {}, "ref": str(ref)}

                            ref += 1

                            await ws.send(json.dumps(hb))

                        except Exception:

                            break

                hb_task = asyncio.create_task(_phoenix_heartbeat())

                try:

                    async for raw in ws:

                        try:

                            msg = json.loads(raw)

                        except Exception:

                            continue

                        event = msg.get('event', '')

                        if event == 'postgres_changes':

                            payload = msg.get('payload', {})

                            row = payload.get('data', {}).get('record', {})

                            _rtype = (row.get('metadata') or {}).get('type', '')

                            if (row.get('role') == 'user' and not _rtype) or (

                                row.get('role') == 'system' and _rtype in ('approval_response', 'interrupt', 'autonomous_toggle')

                            ):

                                threading.Thread(target=handle_user_message, args=(row,), daemon=True).start()

                finally:

                    hb_task.cancel()

        except Exception as e:

            log.warning('Realtime 연결 끊김 (%s) — %.1f초 후 자동 재연결...', e, backoff)

            await asyncio.sleep(backoff)

            backoff = min(backoff * 1.5, 30.0)

if __name__ == '__main__':

    if not _acquire_single_instance_lock():

        sys.exit(42)

    log.info('🚀 DAON Remote Connector (v3 — PATCH 스트리밍 + 상태 배지) 시작')

    log.info('Supabase URL: %s', SUPABASE_URL)

    log.info('DAON URL: %s', DAON_URL)
    # 백그라운드 모델 동기화 스레드 시작 (DAON /api/models -> Supabase & config.js)
    threading.Thread(target=_model_sync_worker, daemon=True).start()


    try:

        asyncio.run(realtime_loop())

    finally:

        _release_single_instance_lock()

