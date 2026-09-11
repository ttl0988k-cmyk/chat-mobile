# -*- coding: utf-8 -*-
"""커넥터 패치: 자율실행 토글 + 승인 400 피드백 + delta stream_id + auto_approved 읽기전용"""
import io, sys

P = r'C:\daon\cafe\LLM\chat\connector\daon_remote_connector.py'
BAK = P + '.bak-2026-08-30-auto'
src = io.open(P, 'r', encoding='utf-8', newline='').read()
io.open(BAK, 'w', encoding='utf-8', newline='').write(src)

def rep(old, new, tag):
    global src
    # 공백라인 패딩 무시 매칭: 논리 라인 시퀀스로 정규화해 위치를 찾고 원본 버전으로 치환
    o_lines = [l for l in old.split('\n')]
    # 원본에서 old의 첫 줄이 나오는 지점부터 순차 매칭 (빈 줄 스킵 허용)
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
                # [i, j) 구간을 new로 교체 (원본 개행 스타일 유지: \r\n)
                new_lf = new.replace('\n', '\r\n') if '\r\n' in src[:2000] else new
                src = '\n'.join(lines[:i]) + '\n' + new_lf + '\n' + '\n'.join(lines[j:])
                print(f'[OK] {tag} (lines {i+1}-{j})')
                return
        i += 1
    print(f'[FAIL] {tag} — 매칭 실패'); sys.exit(1)

EOL = '\r\n' if '\r\n' in src[:2000] else '\n'

# 1) 자율실행 상태 블록 삽입 (def daon_approval 앞)
rep("def daon_approval(session_id: str, approve: bool, reason: str = ''):",
    "# ── 자율 실행 모드 (모바일 토글 → 커넥터가 승인 요청 자동 처리) ──" + EOL +
    "_AUTO_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'connector_state.json')" + EOL +
    EOL +
    "def _load_auto_approve() -> bool:" + EOL +
    "    try:" + EOL +
    "        with open(_AUTO_STATE_PATH, 'r', encoding='utf-8') as f:" + EOL +
    "            return bool(json.load(f).get('auto_approve'))" + EOL +
    "    except Exception:" + EOL +
    "        return False" + EOL +
    EOL +
    "def _save_auto_approve(v: bool) -> None:" + EOL +
    "    try:" + EOL +
    "        st = {}" + EOL +
    "        if os.path.exists(_AUTO_STATE_PATH):" + EOL +
    "            with open(_AUTO_STATE_PATH, 'r', encoding='utf-8') as f:" + EOL +
    "                st = json.load(f)" + EOL +
    "        st['auto_approve'] = bool(v)" + EOL +
    "        with open(_AUTO_STATE_PATH, 'w', encoding='utf-8') as f:" + EOL +
    "            json.dump(st, f)" + EOL +
    "    except Exception as e:" + EOL +
    "        log.warning('자율실행 상태 저장 실패: %s', e)" + EOL +
    EOL +
    "_AUTO_APPROVE = _load_auto_approve()" + EOL +
    EOL +
    "def daon_approval(session_id: str, approve: bool, reason: str = ''):",
    'P1-자율실행상태블록')

# 2) 승인 응답 결과 캡처 + 400 피드백
rep("            daon_approval(session_id, bool(meta.get('approved')), reason=meta.get('reason', ''))",
    "            _ok = daon_approval(session_id, bool(meta.get('approved')), reason=meta.get('reason', ''))" + EOL +
    "            if not _ok:" + EOL +
    "                # 이미 45초 자동승인되었거나 만료됨 — 모바일에 상태 알림" + EOL +
    "                try:" + EOL +
    "                    sb_request('POST', '/rest/v1/messages', {" + EOL +
    "                        'conversation_id': conv_id, 'user_id': user_id, 'role': 'tool'," + EOL +
    "                        'content': '⏳ 이미 자동 승인되었거나 만료된 승인입니다 (45초 무응답 자동승인).'," + EOL +
    "                        'metadata': {'type': 'notice'}," + EOL +
    "                    }, service=True)" + EOL +
    "                except Exception:" + EOL +
    "                    pass",
    'P2-승인400피드백')

# 3) approval 릴레이 3분기 (자율실행 즉시승인 / auto_approved 읽기전용 / 일반 카드)
rep("""            sb_request('POST', '/rest/v1/messages', {
                'conversation_id': conv_id, 'user_id': user_id, 'role': 'tool',
                'content': f"🔐 승인 요청: {data.get('message', data.get('cmd', '?'))}",
                'metadata': {'type': 'approval', 'data': approval_data},
            }, service=True)
            log.info('🔐 승인 요청 전달됨 (session=%s)', _CONV_SESSIONS.get(conv_id))""",
    "            _status = str(data.get('status') or 'pending')" + EOL +
    "            _subj = str(data.get('message', data.get('cmd', '?')))" + EOL +
    EOL +
    "            if _status == 'pending' and _AUTO_APPROVE and approval_data.get('session_id'):" + EOL +
    "                # [자율실행] 모바일 대기 없이 즉시 승인" + EOL +
    "                _sid = approval_data['session_id']" + EOL +
    "                _ok = daon_approval(_sid, True)" + EOL +
    "                _msg = ('🤖 자율 실행: 승인 자동 처리 — ' if _ok else '🤖 자율 실행: 자동 승인 실패(이미 처리됨) — ') + _subj" + EOL +
    "                sb_request('POST', '/rest/v1/messages', {" + EOL +
    "                    'conversation_id': conv_id, 'user_id': user_id, 'role': 'tool'," + EOL +
    "                    'content': _msg," + EOL +
    "                    'metadata': {'type': 'approval', 'data': dict(approval_data, status='auto_approved')}," + EOL +
    "                }, service=True)" + EOL +
    "                log.info('🤖 자율 실행 자동승인 (session=%s, ok=%s)', _sid, _ok)" + EOL +
    "            elif _status == 'auto_approved':" + EOL +
    "                # DAON 45초 무응답 자동승인 → 읽기전용 안내 (버튼 없음)" + EOL +
    "                sb_request('POST', '/rest/v1/messages', {" + EOL +
    "                    'conversation_id': conv_id, 'user_id': user_id, 'role': 'tool'," + EOL +
    "                    'content': '⏳ 45초 무응답으로 자동 승인되었습니다 — ' + _subj," + EOL +
    "                    'metadata': {'type': 'approval', 'data': dict(approval_data, status='auto_approved')}," + EOL +
    "                }, service=True)" + EOL +
    "                log.info('⏳ 자동승인 이벤트 전달 (session=%s)', approval_data.get('session_id'))" + EOL +
    "            else:" + EOL +
    "                sb_request('POST', '/rest/v1/messages', {" + EOL +
    "                    'conversation_id': conv_id, 'user_id': user_id, 'role': 'tool'," + EOL +
    "                    'content': f\"🔐 승인 요청: {_subj}\"," + EOL +
    "                    'metadata': {'type': 'approval', 'data': approval_data}," + EOL +
    "                }, service=True)" + EOL +
    "                log.info('🔐 승인 요청 전달됨 (session=%s)', _CONV_SESSIONS.get(conv_id))",
    'P3-승인릴레이3분기')

# 4) 자율실행 토글 핸들러 (interrupt 핸들러 앞)
rep("    if mtype == 'interrupt':",
    "    if mtype == 'autonomous_toggle':" + EOL +
    "        global _AUTO_APPROVE" + EOL +
    "        _AUTO_APPROVE = bool(meta.get('enabled'))" + EOL +
    "        _save_auto_approve(_AUTO_APPROVE)" + EOL +
    "        try:" + EOL +
    "            sb_request('POST', '/rest/v1/messages', {" + EOL +
    "                'conversation_id': conv_id, 'user_id': user_id, 'role': 'tool'," + EOL +
    "                'content': '🤖 자율 실행 모드 ON — 승인 요청을 자동 승인합니다.' if _AUTO_APPROVE else '🛡️ 일반 실행 모드 — 승인 요청마다 확인합니다.'," + EOL +
    "                'metadata': {'type': 'notice', 'auto': _AUTO_APPROVE}," + EOL +
    "            }, service=True)" + EOL +
    "        except Exception:" + EOL +
    "            pass" + EOL +
    "        log.info('🤖 자율 실행 토글: %s', _AUTO_APPROVE)" + EOL +
    "        return" + EOL +
    EOL +
    "    if mtype == 'interrupt':",
    'P4-자율실행토글핸들러')

# 5) 수신 필터에 autonomous_toggle 추가
rep("if (row.get('role') == 'user' and not _rtype) or (row.get('role') == 'system' and _rtype in ('approval_response', 'interrupt')):",
    "if (row.get('role') == 'user' and not _rtype) or (row.get('role') == 'system' and _rtype in ('approval_response', 'interrupt', 'autonomous_toggle')):",
    'P5-수신필터')

# 6) delta/complete에 stream_id 추가 (작업중단 버튼 평시 활성화)
rep("                'metadata': {'type': 'delta'},",
    "                'metadata': {'type': 'delta', 'stream_id': stream_id},",
    'P6-delta-stream-id')
rep("                'content': '✅ 완료', 'metadata': {'type': 'complete', 'session': session.get('session_id')},",
    "                'content': '✅ 완료', 'metadata': {'type': 'complete', 'session': session.get('session_id'), 'stream_id': stream_id},",
    'P7-complete-stream-id')

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('저장 완료:', P)
