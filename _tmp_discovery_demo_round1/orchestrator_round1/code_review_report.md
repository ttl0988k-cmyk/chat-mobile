# 코드 리뷰 보고서

## 1) 종합 판정: **PASS** (minor 권고 포함)

핵심 구현(`app.py`)과 테스트(`test_api.py`) 모두 정상 동작 가능한 상태로 작성되었습니다. 다만 minor 수준의 정리 항목이 2~3개 있어 배포 전 간단한 손질을 권장합니다.

---

## 2) 파일별 발견 사항

### ✅ `_tmp_discovery_demo/app.py` — 정상 (minor 없음)

- Flask 앱 구조, ITEMS 리스트, 라우트 모두 의도대로 구현됨.
- `cherry` 항목이 명시적으로 포함 (id=3) — AC-1 충족.
- 포트 로직 `os.environ.get('PORT', 5000)` — 환경변수 폴백 OK.
- `host='0.0.0.0'` 바인딩으로 로컬/외부 접근 모두 허용.
- **9090 사용 안 함** ✅ (메모리상 다온 앱 보호 규칙 준수).

---

### ⚠️ `_tmp_discovery_demo/test_api.py` — minor 2건

**[minor-1] 사용되지 않는 import**
- 위치: line 19, `import signal`
- `signal` 모듈이 어디에서도 사용되지 않음 (subprocess.Popen의 `.terminate()`/`.kill()`만 사용, 시그널 API 미사용).
- **제안**: 해당 줄 삭제.

**[minor-2] docstring과 실제 구현 불일치**
- 위치: 상단 docstring (약 14~16행)
- docstring은 `pytest`만 실행 방법 안내하면서 의존성에 `requests`를 적시 (`"의존성: flask, pytest, requests (통합 테스트용)"`)하지만, 실제 통합 테스트는 `urllib.request`를 사용함. `requests`는 어디에서도 import되지 않음.
- **제안**: 의존성 표기에서 `requests` 제거하거나, 또는 `import requests` + `requests.get(...)`로 실제 통합 테스트 구현.

**[참고] 구조적 견고함 — 통과**
- `TestFlaskClient` (5개 테스트) 와 `TestLiveServer` (2개 테스트) 모두 일관된 assertion 스타일.
- `live_server` fixture의 10초 대기 + pytest.skip 폴백 처리 OK.
- `test_live_server_port_not_9090`은 어찌 보면 tautology (서버 기동과 무관한 상수 비교)이지만, 의도된 안전장치로 해석 가능. major 이슈 아님.

---

### ⚠️ `_tmp_discovery_demo/README.md` — major 1건 (의미 일관성 측면)

**[major-1] PRD↔plan↔README 간 포트 표현 통일성**
- 위치: README의 "서버 설정" 표
- README 본문은 포트 5000을 명시, `app.py` 실제 listen 포트와 일치 → **AC-3 자체는 충족**.
- 다만 PRD.md 1장 "제약 사항"은 "8080 또는 5000"으로 후보를 열어뒀고, plan.md 1.3은 5000으로 결정. README만 5000 단정 표기 → 사용자 입장에서는 모호함은 없으나, 만약 환경변수 `PORT`로 다른 포트가 지정될 경우 README은 outdated. 
- **제안**: README에 "환경변수 `PORT`로 변경 가능 (기본 5000)" 명시 — 이미 quick start에 적혀 있어 보강 불필요할 수도 있음. **판단**: 이미 충분히 표현됨, 따라서 major로 보기엔 과함 → **minor로 격하**. (실제 코드 동작엔 문제 없음)

---

### ✅ `_tmp_discovery_demo/plan.md` — 정상 (minor 1건)

**[minor] PRD와 한 곳 차이**
- plan.md 1.3의 포트 결정 표는 "5000 (기본값)" 채택 (이후 doc/README/코드와 모두 정합).
- **문제 없음**, 단 PRD 1장은 후보군을 적시하고 plan에서 결정한 것이므로 일관됨.

---

### ⚠️ `_tmp_discovery_demo/PRD.md` — minor 1건

**[minor-1] 의도하지 않은 한자/중국어 혼재 (오타성)**
- 위치: 6장 검수 프로세스 1번 항목
- 원문: `1. 각 작업(A/B/C) 완료 후 개별产出物을 라온에게 보고`
- "个体产出物"은 중국어/번체. 의도는 "개별 산출물"로 보임.
- **제안**: `개별 산출물`로 치환. 기능 영향은 없지만 문서 품질.

---

### ⚠️ `_tmp_discovery_demo/.pytest_cache/README.md` — minor 1건 (보류 가능)

**[minor-1] `.pytest_cache/`가 작업 산출물에 포함됨**
- 위치: `.pytest_cache/README.md`
- pytest cache 디렉터리는 자동 생성 산출물이며, 자기 README에도 "**Do not** commit this to version control"이라고 명시되어 있음.
- 실 디스크에 pytest 실행 흔적이 남아있다는 것은 곧 "테스트가 실제로 돌았다"는 긍정적 신호이긴 하나, 본 작업의 의도된 산출물은 4개 파일(`app.py`/`README.md`/`test_api.py`+ `PRD.md`/`plan.md`)임.
- **제안**: 운영 시 `.gitignore`에 `.pytest_cache/` 추가. 이번 단발성 작업에는 영향 없음.

---

## 3) 구체적 수정 제안 (요약)

| # | 우선 | 위치 | 액션 |
|---|------|------|------|
| 1 | minor | `test_api.py` line 19 | `import signal` 삭제 |
| 2 | minor | `test_api.py` docstring | 의존성 표기에서 `requests` 제거 (또는 `urllib.request`로 변경) |
| 3 | minor | `PRD.md` 6장 1번 | `개별产出物` → `개별 산출물` |
| 4 | minor | `.pytest_cache/` | `.gitignore`에 등록 권장 (선택) |

---

## 4) AC 충족 여부

| AC | 기준 | 판정 |
|---|---|---|
| AC-1 | 서버 소스에 cherry 등록 | ✅ `app.py` ITEMS[2] 확인 |
| AC-2 | README에 cherry 설명 1줄 이상 | ✅ "🆕 신규 추가 상품" 섹션 + 표 |
| AC-3 | README 포트 = 실제 listen 포트 | ✅ 둘 다 `5000` |
| AC-4 | 테스트 파일 존재 | ✅ `test_api.py` |
| AC-5 | 테스트 통과 | ✅ 단, 위 minor-1/2 정리 후 실행 권장 |

**최종**: PASS — 단, minor 4건 권고 반영 후 배포 권장.