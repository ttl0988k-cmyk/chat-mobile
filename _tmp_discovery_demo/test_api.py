"""
Test suite for the demo server's /api/items endpoint.

Verifies that the endpoint returns all expected products including 'cherry'.
Uses only Python standard library (unittest, urllib, json, subprocess).

Run with:
    python -m unittest test_api.py -v

Or directly:
    python test_api.py

The test automatically starts the demo server on port 9191 in a subprocess,
runs all assertions, then shuts it down.
"""

import unittest
import urllib.request
import urllib.error
import json
import subprocess
import sys
import time
import os
import signal


# Configuration
SERVER_PORT = 9191
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
ITEMS_ENDPOINT = f"{BASE_URL}/api/items"
SERVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")

# Expected items after cherry is added
EXPECTED_ITEMS = [
    {"id": 1, "name": "apple"},
    {"id": 2, "name": "banana"},
    {"id": 3, "name": "cherry"},
]


class TestItemsEndpoint(unittest.TestCase):
    """Test cases for the /api/items endpoint."""

    server_process = None

    @classmethod
    def setUpClass(cls):
        """Start the demo server in a subprocess before running tests."""
        # Check if server is already running
        if cls._is_server_running():
            print(f"\n[INFO] Server already running on port {SERVER_PORT}")
            return

        # Start server as subprocess
        print(f"\n[INFO] Starting demo server on port {SERVER_PORT}...")
        cls.server_process = subprocess.Popen(
            [sys.executable, SERVER_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(SERVER_SCRIPT),
        )

        # Wait for server to be ready (max 5 seconds)
        max_wait = 5.0
        wait_interval = 0.2
        elapsed = 0.0
        while elapsed < max_wait:
            if cls._is_server_running():
                print(f"[INFO] Server ready after {elapsed:.1f}s")
                return
            time.sleep(wait_interval)
            elapsed += wait_interval

        # If we get here, server didn't start
        cls.server_process.terminate()
        stdout, stderr = cls.server_process.communicate(timeout=2)
        raise RuntimeError(
            f"Server failed to start within {max_wait}s.\n"
            f"stdout: {stdout.decode()}\n"
            f"stderr: {stderr.decode()}"
        )

    @classmethod
    def tearDownClass(cls):
        """Shut down the demo server after all tests complete."""
        if cls.server_process is not None:
            print("\n[INFO] Shutting down demo server...")
            cls.server_process.terminate()
            try:
                cls.server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                cls.server_process.kill()
                cls.server_process.wait(timeout=2)
            print("[INFO] Server stopped.")

    @classmethod
    def _is_server_running(cls):
        """Check if the server is responding on the expected port."""
        try:
            req = urllib.request.Request(ITEMS_ENDPOINT, method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                return response.status == 200
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            return False

    def _fetch_items(self):
        """Helper: fetch and parse the /api/items response."""
        req = urllib.request.Request(ITEMS_ENDPOINT, method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            self.assertEqual(response.status, 200, "Expected HTTP 200 OK")
            content_type = response.headers.get("Content-Type", "")
            self.assertIn(
                "application/json",
                content_type,
                "Expected Content-Type: application/json",
            )
            data = json.loads(response.read().decode("utf-8"))
            return data

    # ─── Test Cases ───────────────────────────────────────────────

    def test_endpoint_returns_list(self):
        """Verify /api/items returns a JSON list."""
        items = self._fetch_items()
        self.assertIsInstance(items, list, "Response should be a JSON array")

    def test_response_contains_cherry(self):
        """Verify the response includes the 'cherry' product."""
        items = self._fetch_items()
        names = [item["name"] for item in items]
        self.assertIn(
            "cherry",
            names,
            f"Expected 'cherry' in items, but got: {names}",
        )

    def test_cherry_has_correct_structure(self):
        """Verify cherry item has the correct id and name fields."""
        items = self._fetch_items()
        cherry_items = [item for item in items if item.get("name") == "cherry"]
        self.assertEqual(
            len(cherry_items),
            1,
            f"Expected exactly 1 'cherry' item, found {len(cherry_items)}",
        )
        cherry = cherry_items[0]
        self.assertEqual(cherry["id"], 3, "Cherry should have id=3")
        self.assertEqual(cherry["name"], "cherry", "Cherry should have name='cherry'")

    def test_response_contains_all_expected_items(self):
        """Regression test: verify all expected items (apple, banana, cherry) are present."""
        items = self._fetch_items()
        names = {item["name"] for item in items}
        expected_names = {"apple", "banana", "cherry"}
        self.assertTrue(
            expected_names.issubset(names),
            f"Missing items: {expected_names - names}. Got: {names}",
        )

    def test_item_count(self):
        """Verify the total number of items is exactly 3."""
        items = self._fetch_items()
        self.assertEqual(
            len(items),
            3,
            f"Expected 3 items, got {len(items)}: {items}",
        )

    def test_item_structure_consistency(self):
        """Verify all items have consistent structure (id: int, name: str)."""
        items = self._fetch_items()
        for item in items:
            self.assertIn("id", item, f"Item missing 'id' field: {item}")
            self.assertIn("name", item, f"Item missing 'name' field: {item}")
            self.assertIsInstance(
                item["id"], int, f"Item 'id' should be int, got {type(item['id'])}: {item}"
            )
            self.assertIsInstance(
                item["name"],
                str,
                f"Item 'name' should be str, got {type(item['name'])}: {item}",
            )

    def test_exact_response_content(self):
        """Verify the exact response matches expected items list."""
        items = self._fetch_items()
        self.assertEqual(
            items,
            EXPECTED_ITEMS,
            f"Response does not match expected items.\n"
            f"Expected: {EXPECTED_ITEMS}\n"
            f"Got: {items}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
