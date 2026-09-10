# Realtime 수신부 필터 수정: system 제어 메시지(approval_response/interrupt) 통과
# CR CRLF 함정 회피: 바이트 단위 읽기 + 줄끝 \r 개수 보존
p = r'C:\daon\cafe\LLM\chat\connector\daon_remote_connector.py'
raw = open(p, 'rb').read().decode('utf-8')
lines = raw.split('\n')

target = "if row.get('role') == 'user' and not row.get('metadata', {}).get('type'):"
cnt = 0
for i, line in enumerate(lines):
    if target in line:
        ncr = len(line) - len(line.rstrip('\r'))
        suffix = '\r' * ncr
        s = line.rstrip('\r')
        indent = s[:len(s) - len(s.lstrip())]
        new1 = indent + "_rtype = (row.get('metadata') or {}).get('type', '')"
        new2 = (indent + "if (row.get('role') == 'user' and not _rtype) or "
                "(row.get('role') == 'system' and _rtype in ('approval_response', 'interrupt')):")
        lines[i] = new1 + suffix + '\n' + new2 + suffix
        cnt += 1

open(p, 'wb').write('\n'.join(lines).encode('utf-8'))
print('replaced:', cnt)
