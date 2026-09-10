# 모바일 챗 3대 문제 수정 계획 (2026-09-04)

## 진단 결과 (DB/로그 실측 확정)

### 문제 1: 메시지 중복 — 근본원인 확정
- `sb_request()`에 `Prefer: return=representation` 헤더 누락
- → Supabase INSERT가 201 성공 + **빈 body** 반환 → 커넥터 `res=None`
- → `msg_id`를 못 받음 → 0.2초 flush마다 **누적 전문을 새 row로 중복 INSERT 폭주**
- 실측: stream `f4ba0194…` 하나에 delta row 29개 + complete 1개 (내용 전부 동일)
- v2 가드(`inserted_streams`)는 msg_id 수신에 의존해서 무용지물이었음
- 추가 결함: finish 후 `msg_ids` 보존 → 다음 응답이 **이전 row를 PATCH로 덮어씀**

### 문제 2: 도구 사용 메시지
- DB에 남아있는 옛날 `type='tool'` row가 loadMessages에서 그대로 렌더링됨
- 커넥터 v2는 tool INSERT를 안 하지만, 앱 렌더러가 옛 row를 표시

### 문제 3: 링크 클릭 불가
- `createBubble()`이 `textContent`로만 표시 → URL/마크다운 링크 전부 클릭 불가

---

## 수정 내용

### A. 커넥터 (daon_remote_connector.py)
1. **[치명] sb_request에 `Prefer: return=representation` 헤더 추가** (POST/PATCH 시)
   → msg_id 정상 수신 → 첫 flush 1회 INSERT + 이후 전부 PATCH (row 1개)
2. **응답 파싱 방어 보강**: INSERT 후 res가 list 아니면 ERROR 로그 + 재INSERT 방지 가드 유지
3. **새 응답 시작 시 `msg_ids.pop(conv_id)`** → 새 row INSERT 보장 (이전 row 덮어쓰기 방지)
4. **`inserted_streams` 토큰 차단 가드 제거** — PATCH 스트리밍이 정상 동작하므로
   실시간 토큰 흐름을 막던 부작용 제거 (진짜 실시간 렌더링 복원)
5. **도구 이벤트 → 상태 row 방식 전환**:
   - tool/approval 이벤트 시 `type='status'` row 1개 유지 (INSERT 1회 → 이후 PATCH)
   - content: `💭 생각중…` → `🔧 작업중… (도구명)`
   - done 시 status row **DELETE** (화면에서 자동 소멸)
   - 도구 로그/에러 row는 모바일에 INSERT하지 않음 (기존 유지)

### B. 모바일 앱 (app.js)
1. **renderRichContent() 신설**: escHtml → 마크다운 `[text](url)` 링크화 → URL 자동링크
   → `<a href target="_blank" rel="noopener">` — complete(완성본) 시점 적용
2. **createBubble이 textContent 대신 리치 렌더 사용** (링크 클릭 이동 가능)
3. **type='tool' / type='error' row 렌더 스킵** (도구 로그 모바일 미표시 — 모바일 UX 원칙)
4. **type='status' row**: 회색 미니 배지("생각중…/작업중…") 렌더링, UPDATE 시 텍스트 교체
5. delta/complete UPDATE 처리 시에도 리치 렌더 적용 (0.2초 디바운스라 성능 부담 없음)

### C. 스타일 (style.css)
- `.bubble a` 링크 색/밑줄 + `.status-badge` 미니 배지 스타일

### D. DB 청소 (승인 후 1회 실행)
- 과거 중복 delta row 삭제: (conversation_id, stream_id)별로 complete row가 있으면 해당 delta row 전부 제거
- 옛날 `type='tool'` row 제거 (모바일 화면 정화)

### E. 적용 절차
1. 커넥터 백업 1개 생성 → 패치
2. 실행 중 커넥터(pid 14020) 종료 → 재시작
3. app.js/style.css 패치 → vercel 배포 (chat-tau-dun.vercel.app)
4. 모바일 테스트: 응답 1개 = row 1개, 링크 클릭, "작업중…" 표시 확인

## 검증 기준
- [ ] 응답 1개당 DB row 1개 (delta→PATCH→complete)
- [ ] 모바일에 메시지 중복 없음
- [ ] 도구 로그 대신 "💭 생각중…/🔧 작업중…" 배지만 표시, 완료 시 소멸
- [ ] 링크 클릭으로 브라우저 이동 가능
