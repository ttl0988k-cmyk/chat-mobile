# -*- coding: utf-8 -*-
"""커넥터 패치 3차: P2(승인400피드백) / P3(릴레이3분기) / P4(자율실행토글)"""
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
    print(f'[FAIL] {tag}'); sys.exit(1)

# P2: 승인 응답 결과 캡처 + 400 피드백
rep("            daon_approval(session_id, bool(meta.get('approved')), reason=meta.get('reason', ''))",
    "            _ok = daon_approval(session_id, bool(meta.get('approved')), reason=meta.get('reason', ''))\n"
    "            if not _ok:\n"
    "                # 이미 45초 자동승인되었거나 만료됨 — 모바일에 상태 알림\n"
    "                try:\n"
    "                    sb_request('POST', '/rest/v1/messages', {\n"
    "                        'conversation_id': conv_id, 'user_id': user_id, 'role': 'tool',\n"
    "                        'content': '⏳ 이미 자동 승인되었거나 만료된 승인입니다 (45초 무응답 자동승인).',\n"
    "                        'metadata': {'type': 'notice'},\n"
    "                    }, service=True)\n"
    "                except Exception:\n"
    "                    pass",
    'P2-승인400피드백')

# P3: approval 릴레이 3분기
rep("""            sb_request('POST', '/rest/v1/messages', {
                'conversation_id': conv_id, 'user_id': user_id, 'role': 'tool',
                'content': f"🔐 승인 요청: {data.get('message', data.get('cmd', '?'))}",
                'metadata': {'type': 'approval', 'data': approval_data},
            }, service=True)
            log.info('🔐 승인 요청 전달됨 (session=%s)', _CONV_SESSIONS.get(conv_id))""",
    "            _status = str(data.get('status') or 'pending')\n"
    "            _subj = str(data.get('message', data.get('cmd', '?')))\n"
    "\n"
    "            if _status == 'pending' and _AUTO_APPROVE and approval_data.get('session_id'):\n"
    "                # [자율실행] 모바일 대기 없이 즉시 승인\n"
    "                _sid = approval_data['session_id']\n"
    "                _ok2 = daon_approval(_sid, True)\n"
    "                _msg = ('🤖 자율 실행: 승인 자동 처리 — ' if _ok2 else '🤖 자율 실행: 자동 승인 실패(이미 처리됨) — ') + _subj\n"
    "                sb_request('POST', '/rest/v1/messages', {\n"
    "                    'conversation_id': conv_id, 'user_id': user_id, 'role': 'tool',\n"
    "                    'content': _msg,\n"
    "                    'metadata': {'type': 'approval', 'data': dict(approval_data, status='auto_approved')},\n"
    "                }, service=True)\n"
    "                log.info('🤖 자율 실행 자동승인 (session=%s, ok=%s)', _sid, _ok2)\n"
    "            elif _status == 'auto_approved':\n"
    "                # DAON 45초 무응답 자동승인 → 읽기전용 안내 (버튼 없음)\n"
    "                sb_request('POST', '/rest/v1/messages', {\n"
    "                    'conversation_id': conv_id, 'user_id': user_id, 'role': 'tool',\n"
    "                    'content': '⏳ 45초 무응답으로 자동 승인되었습니다 — ' + _subj,\n"
    "                    'metadata': {'type': 'approval', 'data': dict(approval_data, status='auto_approved')},\n"
    "                }, service=True)\n"
    "                log.info('⏳ 자동승인 이벤트 전달 (session=%s)', approval_data.get('session_id'))\n"
    "            else:\n"
    "                sb_request('POST', '/rest/v1/messages', {\n"
    "                    'conversation_id': conv_id, 'user_id': user_id, 'role': 'tool',\n"
    "                    'content': f\"🔐 승인 요청: {_subj}\",\n"
    "                    'metadata': {'type': 'approval', 'data': approval_data},\n"
    "                }, service=True)\n"
    "                log.info('🔐 승인 요청 전달됨 (session=%s)', _CONV_SESSIONS.get(conv_id))",
    'P3-승인릴레이3분기')

# P4: 자율실행 토글 핸들러
rep("    if mtype == 'interrupt':",
    "    if mtype == 'autonomous_toggle':\n"
    "        global _AUTO_APPROVE\n"
    "        _AUTO_APPROVE = bool(meta.get('enabled'))\n"
    "        _save_auto_approve(_AUTO_APPROVE)\n"
    "        try:\n"
    "            sb_request('POST', '/rest/v1/messages', {\n"
    "                'conversation_id': conv_id, 'user_id': user_id, 'role': 'tool',\n"
    "                'content': '🤖 자율 실행 모드 ON — 승인 요청을 자동 승인합니다.' if _AUTO_APPROVE else '🛡️ 일반 실행 모드 — 승인 요청마다 확인합니다.',\n"
    "                'metadata': {'type': 'notice', 'auto': _AUTO_APPROVE},\n"
    "            }, service=True)\n"
    "        except Exception:\n"
    "            pass\n"
    "        log.info('🤖 자율 실행 토글: %s', _AUTO_APPROVE)\n"
    "        return\n"
    "\n"
    "    if mtype == 'interrupt':",
    'P4-자율실행토글핸들러')

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('저장 완료')
