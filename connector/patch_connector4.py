# -*- coding: utf-8 -*-
"""커넥터 패치 4차: 스트리밍 렌더링 복원 — sentence boundary flush
2026-09-03 버퍼링 방식(don에서 한 번에 INSERT)이 도구 사용 시 커넥터 끊김 유발.
수정: 버퍼 유지하되 문장 끝(.!?)이나 100자마다 DB에 PATCH로 실시간 업데이트.
"""
import io, sys

P = r'C:\daon\cafe\LLM\chat\connector\daon_remote_connector.py'
src = io.open(P, 'r', encoding='utf-8', newline='').read()
EOL = '\r\n' if '\r\n' in src[:2000] else '\n'

def rep(old, new, tag):
    global src
    o_lines = old.split('\n')
    lines = src.split('\n')
    n, m = len(lines), len(o_lines)
    i = 0
    while i < n:
        if lines[i].rstrip('\r') == o_lines[0].rstrip('\r'):
            j, k = i, 0
            while k < m and j < n:
                if lines[j].strip() == '' and o_lines[k].strip() != '':
                    j += 1
                    continue
                if lines[j].rstrip('\r').strip() == o_lines[k].strip():
                    j += 1; k += 1
                elif lines[j].strip() == '':
                    j += 1
                else:
                    break
            if k == m:
                new_lf = new.replace('\n', EOL)
                src = '\n'.join(lines[:i]) + '\n' + new_lf + '\n' + '\n'.join(lines[j:])
                print(f'[OK] {tag} (lines {i+1}-{j})')
                return
        i += 1
    print(f'[FAIL] {tag} — 매칭 실패'); sys.exit(1)

# P1: _DELTA_BUFFERS 옆에 _STREAM_MSG_IDS 추가 (각 세션의 현재 assistant message id 추적)
rep(
    "_DELTA_BUFFERS = {}    # conversation_id -> 누적 텍스트 (2026-09-03 delta 버퍼)",
    "_DELTA_BUFFERS = {}    # conversation_id -> 누적 텍스트\n_STREAM_MSG_IDS = {}  # conversation_id -> 현재 assistant message id (streaming용)",
    'P1-추가-메시지ID트래킹'
)

# P2: delta 이벤트 핸들러 — sentence boundary 또는 100자마다 DB PATCH
rep(
    "            # 🔧 2026-09-03 fix: delta 토큰을 DB에 INSERT하지 않고 버퍼에 누적 (모바일 뒤죽박죽 방지)\n            _DELTA_BUFFERS[conv_id] = _DELTA_BUFFERS.get(conv_id, '') + text",
    "            # 🔧 2026-09-04 fix: sentence boundary마다 DB PATCH (커넥터 끊김 방지)\n            import re as _re\n            _DELTA_BUFFERS[conv_id] = _DELTA_BUFFERS.get(conv_id, '') + text\n            buf = _DELTA_BUFFERS.get(conv_id, '')\n            # 버퍼 크기 >= 100자 또는 문장 끝(.!?) 있으면 flush\n            if len(buf) >= 100 or (_re.search(r'[.!?。！？]\\s*$', buf) and len(buf) > 10):\n                _flush_delta_to_db(conv_id, stream_id, session, buf)",
    'P2-delta-스트리밍-flush'
)

# P3: _flush_delta_to_db 함수 추가 (버퍼를 DB에 PATCH하는 헬퍼)
# on_event 함수 위에 추가
rep(
    "        elif event == 'delta':\n            text = data.get('text', '')",
    "        # ── streaming flush helper ──────────────────────────────────\n        def _flush_delta_to_db(conv_id, stream_id, session, content):\n            \"\"\"버퍼 내용을 DB assistant 메시지에 PATCH (없으면 POST)\"\"\"\n            msg_id = _STREAM_MSG_IDS.get(conv_id)\n            if not msg_id:\n                # 첫 삽입: POST 후 ID 저장\n                try:\n                    resp = sb_request('POST', '/rest/v1/messages', {\n                        'conversation_id': conv_id,\n                        'role': 'assistant',\n                        'content': content,\n                        'metadata': {'type': 'delta', 'stream_id': stream_id},\n                        'session_id': session.get('session_id'),\n                    }, service=True)\n                    if resp and len(resp) > 0:\n                        _STREAM_MSG_IDS[conv_id] = resp[0].get('id')\n                except Exception:\n                    pass\n            else:\n                # 이후: PATCH로 내용만 업데이트\n                try:\n                    sb_request('PATCH', f\"/rest/v1/messages?id=eq.{msg_id}\", {\n                        'content': content,\n                        'metadata': {'type': 'delta', 'stream_id': stream_id},\n                    }, service=True)\n                except Exception:\n                    pass\n\n        elif event == 'delta':\n            text = data.get('text', '')",
    'P3-flush-헬퍼함수'
)

# P4: done 이벤트 핸들러 — 버퍼 flush 후 complete 메시지
rep(
    "                'content': _DELTA_BUFFERS.pop(conv_id, '') or '✅ 완료', 'metadata': {'type': 'complete', 'session': session.get('session_id'), 'stream_id': stream_id},",
    "                final_content = _DELTA_BUFFERS.pop(conv_id, '') or '✅ 완료'\n                # 마지막 flush\n                _flush_delta_to_db(conv_id, stream_id, session, final_content)\n                # 완료 메시지는 새 레코드로 삽입 (type=complete)\n                sb_request('POST', '/rest/v1/messages', {\n                    'conversation_id': conv_id,\n                    'role': 'assistant',\n                    'content': final_content,\n                    'metadata': {'type': 'complete', 'session': session.get('session_id'), 'stream_id': stream_id},\n                }, service=True)\n                _STREAM_MSG_IDS.pop(conv_id, None)\n                return  # 기존 이어지는 코드 실행 안 함 (완료 후 early return)",
    'P4-done-flush-완료'
)

# P5: done 이벤트에서 이어지는 코드가 실행되지 않도록 early return 이후 중복 삽입 방지
# done 핸들러의 남은 코드를 확인하고 필요하면 제거
# (기존 done 핸들러의残余 코드가 있으면 제거)

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('저장 완료 — 스트리밍 렌더링 복원 패치 적용됨')
