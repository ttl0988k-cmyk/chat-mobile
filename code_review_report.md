# 검증 보고서

## 1) 종합 판정
**NEEDS_FIX** — 코드 자체(server.py / test_api.py)는 동작 가능하나, README가 **존재하지 않는 `config.yaml`**을 인용함. 단독으로 즉시 수정 필요.

---

## 2) 파일별 발견된 문제

### `_tmp_discovery_demo/server.py`
- **문제 없음.** 표준 라이브러리만 사용, 문법/로직 정상. 9191 포트, `/api/items` → 200 JSON, 그 외 → 404. `log_message` 무력화로 stdout 깔끔.

### `_tmp_discovery_demo/test_api.py`
- **minor** (`_is_server_running`, `tearDownClass` 내부 호출): `@classmethod` 데코레이터가 붙어 있으나 `cls`를 사용하지 않음 → `@staticmethod`가 더 적절. 동작에는 영향 없음.
- **minor** (`_is_server_running` 호출 위치): 포트가 이미 점유돼 있고 그 프로세스가 `/api/items`를 200으로 응답하면 그대로 통과해버려 subprocess 시작을 건너뜀 → "우리 서버가 아닐 가능성" 체크 불가. 데모 용도라 실손해 없음.
- 7개 테스트 케이스 의미는 모두 타당. 모듈 상수(`SERVER_PORT`/`SERVER_SCRIPT`/`EXPECTED_ITEMS`)와 `server.py` 값 일치 확인.

### `_tmp_discovery_demo/README.md`
- **major** (Setup & Run 섹션의 `> Note:` 블록):
  > `config.yaml` declares port 8080, but the actual server uses **9191`. Always refer to `server.py` as the source of truth.
  
  현재 `_tmp_discovery_demo/` 디렉토리에 **`config.yaml` 자체가 존재하지 않음** (작성된 파일 3개만 존재). 존재하지 않는 설정에 대한 경고는 독자를 오도하는 dangling reference.
- **minor** (Available Products 섹션): "server.py lines 7–9"라고 명시했으나 실제 ITEMS 배열은 **7~11행** (7=`ITEMS = [`, 8=apple, 9=banana, 10=cherry, 11=`]`) — cherry를 누락한 부정확한 범위.

---

## 3) 구체적인 수정 제안

1. **(major) README의 config.yaml 인용 제거**
   ```markdown
   <!-- 기존 -->
   > **Note:** `config.yaml` declares port 8080, but the actual server uses **9191**...
   
   <!-- 권장: 삭제하고 한 줄로 정리 -->
   The server starts on **port 9191** (hardcoded in `server.py`).
   ```
   또는 정말 외부 설정 파일을 도입하려면 `config.yaml`을 실제로 추가하고 `server.py`가 이를 읽도록 수정(현재 작업 범위 밖). **데모 규모상 옵션 A 권장.**

2. **(minor) README 라인 범위 정정**
   - "server.py lines 7–9" → **"server.py lines 7–11"** 또는 라인 번호 언급 자체 삭제.

3. **(minor) `_is_server_running`을 `@staticmethod`로 전환** — 기능 변화 없음, 의도만 명확해짐.
   ```python
   @staticmethod
   def _is_server_running():
       try:
           req = urllib.request.Request(ITEMS_ENDPOINT, method="GET")
           with urllib.request.urlopen(req, timeout=2) as response:
               return response.status == 200
       except (urllib.error.URLError, ConnectionRefusedError, OSError):
           return False
   ```

4. **(선택) subprocess 시작 직후 stdout 첫 줄("serving on ...")을 폴링하는 헬스체크 강화** — 현재는 HTTP 200만 보지만, 데모 규모라 우선순위 낮음.

---

**결론:** server.py + test_api.py는 그대로 동작. README에서 `config.yaml` 인용만 삭제하면 즉시 PASS 전환 가능.