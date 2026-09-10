# -*- coding: utf-8 -*-
"""커넥터 패치 2차: P5 필터 / P6-P7 stream_id"""
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

# P5: 수신 필터 (실제 들여쓰기 24칸)
rep("                        if (row.get('role') == 'user' and not _rtype) or (row.get('role') == 'system' and _rtype in ('approval_response', 'interrupt')):",
    "                        if (row.get('role') == 'user' and not _rtype) or (row.get('role') == 'system' and _rtype in ('approval_response', 'interrupt', 'autonomous_toggle')):",
    'P5-수신필터')

# P6: delta에 stream_id
rep("                'metadata': {'type': 'delta'},",
    "                'metadata': {'type': 'delta', 'stream_id': stream_id},",
    'P6-delta-stream-id')

# P7: complete에 stream_id
rep("                'content': '✅ 완료', 'metadata': {'type': 'complete', 'session': session.get('session_id')},",
    "                'content': '✅ 완료', 'metadata': {'type': 'complete', 'session': session.get('session_id'), 'stream_id': stream_id},",
    'P7-complete-stream-id')

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('저장 완료')
