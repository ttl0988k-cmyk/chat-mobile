# Demo Server — 상품 목록 API

> 간단한 Python Flask 기반의 데모 서버입니다. 인메모리 상품 목록을 JSON API로 제공합니다.

---

## 🚀 빠른 시작

### 의존성 설치

```bash
pip install flask pytest
```

### 서버 실행

```bash
python app.py
```

서버는 기본적으로 **포트 5000**에서 실행됩니다.
환경변수 `PORT`를 설정하면 다른 포트로 바인딩할 수 있습니다:

```bash
set PORT=8080
python app.py
```

### API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/items` | 전체 상품 목록을 JSON 배열로 반환 |

### 사용 예시

```bash
curl http://localhost:5000/api/items
```

응답:

```json
[
  {"id": 1, "name": "apple", "description": "Fresh red apple"},
  {"id": 2, "name": "banana", "description": "Sweet yellow banana"},
  {"id": 3, "name": "cherry", "description": "Sweet red cherry"}
]
```

---

## 🛒 상품 목록

| ID | 상품명 | 설명 | 비고 |
|----|--------|------|------|
| 1 | apple | Fresh red apple | 기존 상품 |
| 2 | banana | Sweet yellow banana | 기존 상품 |
| 3 | **cherry** | **Sweet red cherry** | 🆕 신규 추가 상품 |

### 🆕 신규 상품: cherry

**cherry**가 이번 업데이트에서 상품 목록에 새로 등록되었습니다.
달콤한 빨간색 체리(Sweet red cherry)로, ID 3번으로 `/api/items` 엔드포인트를 통해 조회할 수 있습니다.

---

## 🧪 테스트

```bash
pytest test_api.py -v
```

테스트는 Flask 내장 테스트 클라이언트를 사용하여, 별도 서버 기동 없이 `/api/items` 응답에 cherry가 포함되어 있는지 검증합니다.

---

## ⚙️ 서버 설정

| 항목 | 값 |
|------|------|
| **언어** | Python 3.x |
| **프레임워크** | Flask |
| **기본 포트** | **5000** |
| **포트 환경변수** | `PORT` (미설정 시 5000 사용) |
| **데이터 저장소** | 인메모리 Python 리스트 |

---

## 📁 프로젝트 구조

```
_tmp_discovery_demo/
├── app.py          # Flask 서버 (메인)
├── README.md       # 본 문서
├── test_api.py     # API 테스트 (pytest)
├── plan.md         # 실행 계획서
└── PRD.md          # 요구사항 정의서
```
