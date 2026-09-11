# -*- coding: utf-8 -*-
"""daon_remote_connector.py 세션 매핑 버그 수정 스크립트 (2026-08-29)

전역 단일 _ACTIVE_SESSION/_ACTIVE_STREAM_ID → conversation_id별 매핑으로 교체.
"""
import io
import sys

PATH = r'C:\daon\cafe\LLM\chat\connector\daon_remote_connector.py'

with io.open(PATH, 'r', encoding='utf-8') as f:
    src = f.read()

orig = src

# ── 1. _ACTIVE_STREAM_ID = None (옛 전역) 제거 — 이미 _CONV_STREAMS로 대체됨
src = src.replace('_ACTIVE_STREAM_ID = None', '# (stream은 _CONV_STREAMS로 관리)')

# ── 2. approval_response / interrupt / 일반채팅 session_id 조회
src = src.replace("session_id = meta.get('session_id') or _ACTIVE_SESSION",
                  "session_id = meta.get('session_id') or _CONV_SESSIONS.get(conv_id)")

# ── 3. interrupt stream_id 조회
src = src.replace("stream_id = meta.get('stream_id') or _ACTIVE_STREAM_ID",
                  "stream_id = meta.get('stream_id') or _CONV_STREAMS.get(conv_id)")

# ── 4. 일반 채팅: 세션 없으면 생성 → conversation별로 저장
src = src.replace('''    if not _ACTIVE_SESSION:
        _ACTIVE_SESSION = daon_new_session(model=req_model or None)

        if not _ACTIVE_SESSION:''',
                  '''    if not _CONV_SESSIONS.get(conv_id):
        _CONV_SESSIONS[conv_id] = daon_new_session(model=req_model or None)

        if not _CONV_SESSIONS.get(conv_id):''')

# ── 5. 세션 로그
src = src.replace("log.info('DAON 세션: %s', _ACTIVE_SESSION)",
                  "log.info('DAON 세션(%s): %s', conv_id[:8], _CONV_SESSIONS.get(conv_id))")

# ── 6. 채팅 시작
src = src.replace("start = daon_start_chat(_ACTIVE_SESSION, content, model=req_model or None)",
                  "start = daon_start_chat(_CONV_SESSIONS.get(conv_id), content, model=req_model or None)")

# ── 7. stream_id 저장
src = src.replace("    _ACTIVE_STREAM_ID = stream_id  # session.interrupt 대비",
                  "    _CONV_STREAMS[conv_id] = stream_id  # session.interrupt 대비")

# ── 8. approval data에 session_id
src = src.replace("approval_data['session_id'] = _ACTIVE_SESSION",
                  "approval_data['session_id'] = _CONV_SESSIONS.get(conv_id)")

# ── 9. approval 로그
src = src.replace("log.info('🔐 승인 요청 전달됨 (session=%s)', _ACTIVE_SESSION)",
                  "log.info('🔐 승인 요청 전달됨 (session=%s)', _CONV_SESSIONS.get(conv_id))")

# ── 10. global 선언에 _CONV_SESSIONS/_CONV_STREAMS 추가 (이미 되어있을 수 있음)
if '_CONV_SESSIONS' not in src.split('def handle_user_message')[0]:
    src = src.replace('global _ACTIVE_SESSION, _ACTIVE_STREAM_ID',
                      'global _ACTIVE_SESSION, _ACTIVE_STREAM_ID, _CONV_SESSIONS, _CONV_STREAMS')

with io.open(PATH, 'w', encoding='utf-8', newline='') as f:
    f.write(src)

# ── 검증: 남은 _ACTIVE_SESSION/_ACTIVE_STREAM_ID 사용처
leftover = []
for i, line in enumerate(src.split('\n'), 1):
    if '_ACTIVE_SESSION' in line or '_ACTIVE_STREAM_ID' in line:
        if 'global ' in line:
            continue
        if '= None' in line:
            continue
        leftover.append(f'{i}: {line.strip()}')

print('수정 완료')
print('변경 전 길이:', len(orig), '→ 변경 후:', len(src))
if leftover:
    print('⚠️ 남은 _ACTIVE_ 참조:')
    for l in leftover:
        print('  ', l)
else:
    print('✅ _ACTIVE_SESSION/_ACTIVE_STREAM_ID 참조 모두 정리됨')
