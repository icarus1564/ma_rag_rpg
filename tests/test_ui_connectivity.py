"""
Basic UI connectivity tests for Phase 5 UI implementation.

These tests verify that:
1. The UI static files are served correctly
2. The root endpoint redirects to the UI
3. All required static files (HTML, CSS, JS) are accessible
"""

import pytest
from fastapi.testclient import TestClient
from src.api.app import app


class TestUIConnectivity:
    """Test suite for UI static file serving and connectivity"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)

    def test_root_redirects_to_ui(self, client):
        """Test that root endpoint redirects to UI"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307  # Redirect status
        assert response.headers["location"] == "/ui/index.html"

    def test_ui_index_accessible(self, client):
        """Test that UI index page is accessible"""
        response = client.get("/ui/index.html")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Multi-Agent RAG RPG" in response.content

    def test_ui_css_accessible(self, client):
        """Test that CSS files are accessible"""
        response = client.get("/ui/css/main.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]

    def test_ui_js_files_accessible(self, client):
        """Test that all required JavaScript files are accessible"""
        js_files = [
            "utils.js",
            "api-client.js",
            "game-tab.js",
            "status-tab.js",
            "config-tab.js",
            "feedback-tab.js",
            "main.js",
        ]

        for js_file in js_files:
            response = client.get(f"/ui/js/{js_file}")
            assert response.status_code == 200, f"{js_file} not accessible"
            assert (
                "javascript" in response.headers["content-type"]
                or "text/plain" in response.headers["content-type"]
            ), f"{js_file} has wrong content type"

    def test_index_contains_required_elements(self, client):
        """Test that index.html contains all required tabs"""
        response = client.get("/ui/index.html")
        content = response.content.decode("utf-8")

        # Check for tab navigation
        assert "game-tab" in content
        assert "status-tab" in content
        assert "config-tab" in content
        assert "feedback-tab" in content

        # Check for tab panes
        assert "gameTab" in content
        assert "statusTab" in content
        assert "configTab" in content
        assert "feedbackTab" in content

        # Check for Bootstrap and other dependencies
        assert "bootstrap" in content.lower()
        assert "font-awesome" in content.lower() or "fontawesome" in content.lower()

    def test_api_endpoints_still_work(self, client):
        """Test that API endpoints are not affected by static file mounting"""
        # Health endpoint should still work
        response = client.get("/health")
        assert response.status_code == 200

        # API endpoints should still be accessible
        # Note: These might fail if indices aren't loaded, but should at least be routable
        response = client.get("/api/status/system")
        assert response.status_code in [200, 500]  # Either works or fails gracefully

    def test_nonexistent_static_file_returns_404(self, client):
        """Test that accessing non-existent static files returns 404"""
        response = client.get("/ui/nonexistent.html")
        assert response.status_code == 404


class TestUIIntegration:
    """Integration tests for UI functionality"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)

    def test_api_client_endpoints_match(self, client):
        """Test that API endpoints referenced in api-client.js exist"""
        # Get the api-client.js file
        response = client.get("/ui/js/api-client.js")
        assert response.status_code == 200

        content = response.content.decode("utf-8")

        # Verify that the API client references valid endpoints
        # These are the main endpoint categories that should exist
        assert "/api/new_game" in content
        assert "/api/turn" in content
        assert "/api/status/system" in content
        assert "/api/status/corpus" in content
        assert "/api/status/agents" in content
        assert "/health" in content

    def test_ui_loads_all_required_js_modules(self, client):
        """Test that index.html loads all required JavaScript modules in correct order"""
        response = client.get("/ui/index.html")
        content = response.content.decode("utf-8")

        # Check that JS files are loaded in the correct order
        # Utils should come first
        utils_pos = content.find("js/utils.js")
        api_client_pos = content.find("js/api-client.js")
        main_pos = content.find("js/main.js")

        assert utils_pos > 0, "utils.js not found"
        assert api_client_pos > 0, "api-client.js not found"
        assert main_pos > 0, "main.js not found"

        # Utils should be loaded before api-client and main
        assert utils_pos < api_client_pos, "utils.js should load before api-client.js"
        assert api_client_pos < main_pos, "api-client.js should load before main.js"
