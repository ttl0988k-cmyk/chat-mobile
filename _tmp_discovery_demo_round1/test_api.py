"""
test_api.py — GET /api/items 엔드포인트 검증 테스트

데모 서버(app.py)의 GET /api/items 응답에 'cherry' 상품이 포함되어 있는지 검증합니다.

테스트 전략:
  1. Flask 테스트 클라이언트 (in-process, 서버 기동 불필요)
  2. subprocess 기반 통합 테스트 (실제 서버 기동 후 HTTP 요청)

실행 방법:
  pytest test_api.py -v

의존성: flask, pytest, requests (통합 테스트용)
"""

import os
import sys
import json
import time
import signal
import subprocess

import pytest

# ---------------------------------------------------------------------------
# 경로 설정: app.py가 있는 폴더를 sys.path에 추가
# ---------------------------------------------------------------------------
DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
if DEMO_DIR not in sys.path:
    sys.path.insert(0, DEMO_DIR)


# ===================================================================
# Part 1: Flask 테스트 클라이언트 기반 단위 테스트
# ===================================================================

@pytest.fixture(scope="module")
def client():
    """Flask app의 테스트 클라이언트를 생성합니다."""
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


class TestFlaskClient:
    """Flask 내장 테스트 클라이언트를 사용한 API 검증"""

    def test_get_items_status_code(self, client):
        """GET /api/items가 HTTP 200을 반환하는지 확인"""
        response = client.get("/api/items")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}"
        )

    def test_items_is_json_list(self, client):
        """응답이 JSON 형식의 리스트인지 확인"""
        response = client.get("/api/items")
        data = response.get_json()
        assert data is not None, "Response is not valid JSON"
        assert isinstance(data, list), (
            f"Expected list, got {type(data).__name__}"
        )
        assert len(data) >= 1, "Items list should not be empty"

    def test_items_contains_cherry(self, client):
        """응답 본문에 'cherry' 상품이 포함되어 있는지 확인 (핵심 테스트)"""
        response = client.get("/api/items")
        data = response.get_json()

        # 방법 1: 리스트 안에서 name == 'cherry'인 항목 탐색
        cherry_items = [
            item for item in data
            if isinstance(item, dict) and item.get("name") == "cherry"
        ]
        assert len(cherry_items) >= 1, (
            f"'cherry' item not found in response. Got: {json.dumps(data, ensure_ascii=False)}"
        )

    def test_items_contains_cherry_in_raw_text(self, client):
        """응답 원본 텍스트에 'cherry' 문자열이 포함되어 있는지 확인"""
        response = client.get("/api/items")
        raw_text = response.data.decode("utf-8")
        assert "cherry" in raw_text.lower(), (
            f"'cherry' not found in raw response: {raw_text}"
        )

    def test_cherry_item_structure(self, client):
        """cherry 항목이 올바른 구조(id, name, description)를 갖는지 확인"""
        response = client.get("/api/items")
        data = response.get_json()

        cherry = None
        for item in data:
            if isinstance(item, dict) and item.get("name") == "cherry":
                cherry = item
                break

        assert cherry is not None, "cherry item not found"
        assert "id" in cherry, "cherry item missing 'id' field"
        assert "name" in cherry, "cherry item missing 'name' field"
        assert "description" in cherry, "cherry item missing 'description' field"
        assert cherry["name"] == "cherry"


# ===================================================================
# Part 2: Subprocess 기반 통합 테스트 (실제 서버 기동)
# ===================================================================

SERVER_PORT = int(os.environ.get("PORT", 5000))


@pytest.fixture(scope="module")
def live_server():
    """실제 Flask 서버를 subprocess로 기동하고 종료합니다."""
    app_path = os.path.join(DEMO_DIR, "app.py")

    env = os.environ.copy()
    env["PORT"] = str(SERVER_PORT)

    proc = subprocess.Popen(
        [sys.executable, app_path],
        cwd=DEMO_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # 서버가 기동할 때까지 대기 (최대 10초)
    import urllib.request
    import urllib.error

    max_wait = 10
    start = time.time()
    ready = False
    while time.time() - start < max_wait:
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{SERVER_PORT}/api/items",
                timeout=2,
            )
            ready = True
            break
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.5)

    if not ready:
        proc.terminate()
        proc.wait(timeout=5)
        pytest.skip(
            f"Server did not start on port {SERVER_PORT} within {max_wait}s"
        )

    yield proc

    # 정리: 서버 프로세스 종료
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


class TestLiveServer:
    """실제 기동된 서버에 HTTP 요청을 보내는 통합 테스트"""

    def test_live_server_returns_cherry(self, live_server):
        """실제 서버의 GET /api/items 응답에 'cherry'가 포함되는지 확인"""
        import urllib.request

        url = f"http://127.0.0.1:{SERVER_PORT}/api/items"
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)

        assert isinstance(data, list), "Expected JSON list"
        names = [item.get("name") for item in data if isinstance(item, dict)]
        assert "cherry" in names, (
            f"'cherry' not in items list. Got names: {names}"
        )

    def test_live_server_port_not_9090(self, live_server):
        """서버가 금지된 포트 9090을 사용하지 않는지 확인"""
        assert SERVER_PORT != 9090, (
            "Port 9090 is forbidden (conflicts with Daon app)"
        )
