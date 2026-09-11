# -*- coding: utf-8 -*-
"""남은 _ACTIVE_SESSION 참조 정리 (2차) — 줄 단위 처리"""
import io

PATH = r'C:\daon\cafe\LLM\chat\connector\daon_remote_connector.py'

with io.open(PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

out = []
changed = 0
for line in lines:
    stripped = line.rstrip('\r\n')
    # 6457: if not _ACTIVE_SESSION: (일반채팅 세션 생성부)
    if stripped.strip() == 'if not _ACTIVE_SESSION:':
        out.append(line.replace('if not _ACTIVE_SESSION:', 'if not _CONV_SESSIONS.get(conv_id):'))
        changed += 1
    elif stripped.strip() == '_ACTIVE_SESSION = daon_new_session(model=req_model or None)':
        out.append(line.replace('_ACTIVE_SESSION = daon_new_session(model=req_model or None)',
                                '_CONV_SESSIONS[conv_id] = daon_new_session(model=req_model or None)'))
        changed += 1
    elif stripped.strip() == 'if not _ACTIVE_SESSION:' and 'if not _CONV' not in line:
        # 두 번째 if not (실패 시 에러 분기)
        out.append(line.replace('if not _ACTIVE_SESSION:', 'if not _CONV_SESSIONS.get(conv_id):'))
        changed += 1
    elif 'daon_start_chat(_ACTIVE_SESSION' in line:
        out.append(line.replace('daon_start_chat(_ACTIVE_SESSION', 'daon_start_chat(_CONV_SESSIONS.get(conv_id)'))
        changed += 1
    elif 'log.info(\'DAON 세션: %s\', _ACTIVE_SESSION)' in line:
        out.append(line.replace("log.info('DAON 세션: %s', _ACTIVE_SESSION)",
                                "log.info('DAON 세션(%s): %s', conv_id[:8], _CONV_SESSIONS.get(conv_id))"))
        changed += 1
    else:
        out.append(line)

with io.open(PATH, 'w', encoding='utf-8', newline='') as f:
    f.writelines(out)

print('2차 수정 완료, 변경 줄 수:', changed)

# 검증
with io.open(PATH, 'r', encoding='utf-8') as f:
    src = f.read()
left = []
for i, line in enumerate(src.split('\n'), 1):
    if '_ACTIVE_SESSION' in line or '_ACTIVE_STREAM_ID' in line:
        if 'global ' in line or '= None' in line or line.strip().startswith('#'):
            continue
        left.append(f'{i}: {line.strip()}')
if left:
    print('⚠️ 남은 참조:')
    for l in left:
        print(' ', l)
else:
    print('✅ _ACTIVE_SESSION/_ACTIVE_STREAM_ID 사용처 모두 정리됨')
