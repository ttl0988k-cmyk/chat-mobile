# 실행 계획 (Execution Plan)

## 프로젝트: _tmp_discovery_demo — 'cherry' 상품 추가 및 문서화/테스트 구축

| 항목 | 내용 |
|------|------|
| 작성일 | 2026-08-21 |
| 작성자 | 라온 (총괄기획자) |
| 기준 문서 | `PRD.md` |
| 상태 | Ready for Execution |

---

## 📍 Phase 1: 디스커버리 (Discovery)

### 1.1 폴더 탐색 결과

| 점검 항목 | 결과 |
|-----------|------|
| **폴더 위치** | `C:\daon\cafe\LLM\chat\_tmp_discovery_demo` |
| **존재 파일** | `PRD.md` (1개) |
| **서버 소스 코드** | ❌ **존재하지 않음** (app.py, server.py, items.js 등 없음) |
| **기존 README** | ❌ 존재하지 않음 |
| **기존 테스트** | ❌ 존재하지 않음 |

### 1.2 결론: 서버 신규 생성 필요

현재 폴더에 데모 서버 코드가 없으므로, **Python Flask 기반의 경량 데모 서버를 신규 생성**한다.

### 1.3 기술 스택 결정

| 항목 | 선택 | 이유 |
|------|------|------|
| **언어** | Python 3.x | Windows 네이티브 지원, 빠른 프로토타이핑 |
| **프레임워크** | Flask | 경량, 내장 테스트 클라이언트 제공, pytest와 호환성 우수 |
| **포트** | **5000** (기본값) | 9090 금지, 8080보다 Flask 기본값이 자연스러움. 환경변수 `PORT`로 override 가능 |
| **데이터 구조** | Python list of dicts | 단순한 인메모리 상품 목록 |

### 1.4 Items 정의 위치 (예정)

```python
# app.py 내 예상 구조
ITEMS = [
    {"id": 1, "name": "apple", "description": "Fresh red apple"},
    {"id": 2, "name": "banana", "description": "Sweet yellow banana"},
    # ✅ cherry 신규 추가 예정
    {"id": 3, "name": "cherry", "description": "Sweet red cherry"},
]
```

### 1.5 포트 바인딩 로직 (예정)

```python
# app.py 내 포트 설정
import os
PORT = int(os.environ.get("PORT", 5000))  # 기본 5000, 환경변수로 override 가능
app.run(host="0.0.0.0", port=PORT)
```

**포트 결정 근거:**
- 코드 상수: `5000` (Flask 기본값)
- 환경변수 폴백: `os.environ.get("PORT", 5000)` → `PORT` 환경변수 없으면 5000 사용
- 실제 listen 포트: **5000** (환경변수 미설정 시)

---

## 🔀 Phase 2: 병렬 3-Way 작업 실행

3개 작업은 **서로 독립적**이므로 `delegate_task`의 병렬 모드(tasks 배열)로 동시에 실행한다.

### 작업 A: 서버 소스 코드 생성 (cherry 포함)

| 항목 | 내용 |
|------|------|
| **담당 에이전트** | 빌 (Bill, 개발자) |
| **목표** | Flask 기반 데모 서버 `app.py` 생성, cherry 상품 포함 |
| **입력** | 없음 (신규 생성) |
| **출력 파일** | `C:\daon\cafe\LLM\chat\_tmp_discovery_demo\app.py` |
| **포트** | 5000 (환경변수 `PORT`로 override 가능) |
| **필수 구현 사항** | 1. `ITEMS` 리스트에 apple, banana, **cherry** 3개 상품 포함<br>2. `GET /api/items` 엔드포인트 구현 (JSON 반환)<br>3. 포트 5000 바인딩 (환경변수 폴백 포함)<br>4. `if __name__ == "__main__":` 블록으로 직접 실행 가능 |
| **완료 조건** | - `app.py` 파일 생성 완료<br>- `ITEMS` 리스트에 `{"id": 3, "name": "cherry", ...}` 명시적 포함<br>- `python app.py` 실행 시 서버 기동 가능<br>- **AC-1, AC-3 충족** |
| **검증 방법** | 파일 생성 후 `python app.py` 백그라운드 실행 → `curl http://localhost:5000/api/items` → 응답에 "cherry" 포함 확인 |

### 작업 B: README.md 작성

| 항목 | 내용 |
|------|------|
| **담당 에이전트** | 라온 (직접 작성) 또는 빌 (위임) |
| **목표** | 서버 사용법 + cherry 상품 + 정확한 포트 문서화 |
| **입력** | 작업 A의 포트 정보 (5000) |
| **출력 파일** | `C:\daon\cafe\LLM\chat\_tmp_discovery_demo\README.md` |
| **필수 포함 내용** | 1. 프로젝트 설명 (데모 서버, 상품 목록 API)<br>2. **cherry 상품 설명** (신규 추가 항목, 1줄 이상)<br>3. **포트 번호: 5000** (명시적 기재)<br>4. 서버 기동 방법 (`python app.py`)<br>5. API 사용 예시 (`curl http://localhost:5000/api/items`) |
| **완료 조건** | - `README.md` 파일 생성 완료<br>- "cherry" 관련 문구 1줄 이상 포함<br>- 포트 "5000" 명시적 기재<br>- **AC-2, AC-3 충족** |
| **검증 방법** | 파일 내용 grep으로 "cherry" 및 "5000" 포함 확인 |

### 작업 C: 테스트 파일 작성

| 항목 | 내용 |
|------|------|
| **담당 에이전트** | 셜록 (Sherlock, QA) 또는 빌 (위임) |
| **목표** | `GET /api/items` 응답에 cherry 포함 검증하는 pytest 테스트 |
| **입력** | 작업 A의 `app.py` (Flask app 객체), 포트 5000 |
| **출력 파일** | `C:\daon\cafe\LLM\chat\_tmp_discovery_demo\test_api.py` |
| **테스트 전략** | Flask 내장 테스트 클라이언트 사용 (외부 HTTP 요청 없이 in-process 테스트) |
| **필수 테스트 케이스** | 1. `GET /api/items` 호출 시 HTTP 200 응답<br>2. 응답 본문에 "cherry" 문자열 포함<br>3. 응답이 JSON 형식 (list 타입) |
| **완료 조건** | - `test_api.py` 파일 생성 완료<br>- `pytest test_api.py` 실행 시 exit code 0<br>- 모든 assertion 통과<br>- **AC-4, AC-5 충족** |
| **검증 방법** | `pytest test_api.py -v` 실행 → 모든 테스트 PASSED 확인 |

### 병렬 실행 명령 (delegate_task)

```python
delegate_task(
    tasks=[
        {
            "goal": "Flask 기반 데모 서버 app.py 생성. ITEMS 리스트에 apple, banana, cherry 3개 상품 포함. GET /api/items 엔드포인트 구현. 포트 5000 바인딩 (환경변수 PORT 폴백).",
            "context": "작업 위치: C:\\daon\\cafe\\LLM\\chat\\_tmp_discovery_demo. Python Flask 사용. 포트 9090 절대 금지.",
            "toolsets": ["terminal", "file"]
        },
        {
            "goal": "README.md 작성. 프로젝트 설명 + cherry 상품 설명 1줄 이상 + 포트 5000 명시 + 서버 기동 방법(python app.py) + API 사용 예시 포함.",
            "context": "작업 위치: C:\\daon\\cafe\\LLM\\chat\\_tmp_discovery_demo. 서버 포트는 5000.",
            "toolsets": ["file"]
        },
        {
            "goal": "test_api.py 작성. Flask 테스트 클라이언트로 GET /api/items 호출. 응답에 cherry 포함 assertion. pytest 실행 시 통과.",
            "context": "작업 위치: C:\\daon\\cafe\\LLM\\chat\\_tmp_discovery_demo. app.py의 Flask app 객체 import. pytest 사용.",
            "toolsets": ["terminal", "file"]
        }
    ]
)
```

---

## ✅ Phase 3: QA 및 통합 검증

### 3.1 검증 시퀀스

모든 병렬 작업 완료 후, 다음 순서로 통합 검증 수행:

#### Step 1: 파일 존재 확인
```bash
dir C:\daon\cafe\LLM\chat\_tmp_discovery_demo
# 예상: app.py, README.md, test_api.py, PRD.md, plan.md
```

#### Step 2: 서버 기동 및 포트 검증 (AC-3)
```bash
# 백그라운드 서버 실행
cd C:\daon\cafe\LLM\chat\_tmp_discovery_demo
python app.py
```

**검증:**
- 서버 로그에서 `Running on http://0.0.0.0:5000` 확인
- `netstat -ano | findstr :5000` → LISTENING 상태 확인

#### Step 3: API 응답 검증 (AC-1, AC-4)
```bash
curl http://localhost:5000/api/items
```

**예상 응답:**
```json
[
  {"id": 1, "name": "apple", "description": "Fresh red apple"},
  {"id": 2, "name": "banana", "description": "Sweet yellow banana"},
  {"id": 3, "name": "cherry", "description": "Sweet red cherry"}
]
```

**검증:** 응답 본문에 `"cherry"` 문자열 포함 확인

#### Step 4: README 내용 검증 (AC-2, AC-3)
```bash
type README.md | findstr "cherry"
type README.md | findstr "5000"
```

**검증:**
- "cherry" 관련 문구 1줄 이상 포함
- "5000" 포트 번호 명시적 기재

#### Step 5: 테스트 실행 (AC-5)
```bash
cd C:\daon\cafe\LLM\chat\_tmp_discovery_demo
pytest test_api.py -v
```

**예상 결과:**
```
test_api.py::test_get_items_status_code PASSED
test_api.py::test_items_contains_cherry PASSED
test_api.py::test_items_is_json_list PASSED
============================== 3 passed in 0.xx seconds ==============================
```

**검증:** exit code 0, 모든 테스트 PASSED

### 3.2 수용 기준 체크리스트

| AC # | 기준 | 검증 방법 | 결과 |
|------|------|-----------|------|
| **AC-1** | 서버 소스에 cherry 등록 | `app.py`의 `ITEMS` 리스트 확인 | ⏳ Pending |
| **AC-2** | README에 cherry 설명 1줄 이상 | `README.md` grep | ⏳ Pending |
| **AC-3** | README 포트 = 실제 listen 포트 | README "5000" + 서버 로그 확인 | ⏳ Pending |
| **AC-4** | 테스트 파일 존재 | `test_api.py` 파일 확인 | ⏳ Pending |
| **AC-5** | 테스트 통과 (exit code 0) | `pytest test_api.py` 실행 | ⏳ Pending |

---

## 📦 Phase 4: 산출물 목록

| 파일 | 용도 | 생성 시점 | 해당 AC |
|------|------|-----------|---------|
| `app.py` | Flask 데모 서버 (cherry 포함) | Phase 2 (작업 A) | AC-1, AC-3 |
| `README.md` | 서버 및 상품 문서화 | Phase 2 (작업 B) | AC-2, AC-3 |
| `test_api.py` | API 자동 테스트 | Phase 2 (작업 C) | AC-4, AC-5 |
| `PRD.md` | 요구사항 정의서 | 사전 존재 | - |
| `plan.md` | 실행 계획서 | 사전 존재 | - |

---

## 🚨 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| Flask 미설치 | 서버 기동 실패 | `pip install flask` 사전 실행 |
| 포트 5000 점유 | 서버 바인딩 실패 | 환경변수 `PORT=8080`으로 override + README 업데이트 |
| pytest 미설치 | 테스트 실행 불가 | `pip install pytest` 사전 실행 |
| Windows 방화벽 | 로컬 curl 차단 | `localhost` 사용 (외부 접근 아님) |

---

## 📝 다음 단계

1. **본 plan.md 승인** → Phase 2 병렬 작업 실행
2. **Phase 2 완료** → Phase 3 통합 검증
3. **모든 AC 통과** → 작업 완료 보고

---

**끝.**
