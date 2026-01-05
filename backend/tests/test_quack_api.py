"""Quack API endpoint tests.

Tests for:
- POST /api/quack/import (full card, only_lorebook, json output, png output)
- POST /api/quack/preview
- JSON fallback mode (manual paste)
- Error handling (invalid input, no lorebook)
"""

import base64
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# ============================================================
# Test Fixtures
# ============================================================


@pytest.fixture
def sample_quack_data():
    """Sample Quack API response data."""
    return {
        "charList": [
            {
                "name": "TestCharacter",
                "intro": "A test character for unit testing",
                "attrs": [
                    {"label": "Age", "value": "25", "isVisible": True},
                    {"label": "Personality", "value": "Friendly", "isVisible": True},
                ],
                "adviseAttrs": [],
                "customAttrs": [],
            }
        ],
        "intro": "A test character for unit testing",
        "authorName": "TestAuthor",
        "tags": ["test", "demo"],
        "firstMes": "<p>Hello, I'm a test character!</p>",
        "alternate_greetings": ["<p>Alternative greeting</p>"],
        "characterbooks": [
            {
                "entryList": [
                    {
                        "name": "Test Entry",
                        "keywords": ["test", "entry"],
                        "content": "This is test content",
                        "enabled": True,
                        "constant": False,
                    }
                ]
            }
        ],
    }


@pytest.fixture
def sample_quack_data_no_lorebook():
    """Sample Quack data without lorebook."""
    return {
        "charList": [
            {
                "name": "NoLorebookChar",
                "intro": "Character without lorebook",
                "attrs": [],
            }
        ],
        "intro": "Character without lorebook",
        "authorName": "TestAuthor",
        "tags": [],
        "firstMes": "Hello!",
    }


# ============================================================
# Import Endpoint Tests - JSON Mode (Manual Paste)
# ============================================================


class TestQuackImportJsonMode:
    """Tests for JSON fallback mode (manual paste)."""

    def test_import_json_full_card(self, sample_quack_data):
        """Test importing full card from pasted JSON."""
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": json.dumps(sample_quack_data),
                "mode": "full",
                "output_format": "json",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["source"] == "json"
        assert data["data"]["card"] is not None
        assert data["data"]["card"]["data"]["name"] == "TestCharacter"
        assert "QuackAI" in data["data"]["card"]["data"]["tags"]
        assert "使用手动粘贴的 JSON 数据" in data["data"]["warnings"]

    def test_import_json_only_lorebook(self, sample_quack_data):
        """Test importing only lorebook from pasted JSON."""
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": json.dumps(sample_quack_data),
                "mode": "only_lorebook",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["lorebook"] is not None
        assert len(data["data"]["lorebook"]["entries"]) == 1
        assert data["data"]["card"] is None

    def test_import_json_png_output(self, sample_quack_data):
        """Test importing card with PNG output format."""
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": json.dumps(sample_quack_data),
                "mode": "full",
                "output_format": "png",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["png_base64"] is not None
        
        # Verify it's valid base64
        png_bytes = base64.b64decode(data["data"]["png_base64"])
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    def test_import_json_no_lorebook_only_lorebook_mode(self, sample_quack_data_no_lorebook):
        """Test error when requesting only_lorebook but no lorebook exists."""
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": json.dumps(sample_quack_data_no_lorebook),
                "mode": "only_lorebook",
            },
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "没有世界书数据" in data["detail"]["error"]

    def test_import_json_attrs_formatted(self, sample_quack_data):
        """Test that attrs are formatted as [Label: Value]."""
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": json.dumps(sample_quack_data),
                "mode": "full",
                "output_format": "json",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        description = data["data"]["card"]["data"]["description"]
        assert "[Age: 25]" in description
        assert "[Personality: Friendly]" in description

    def test_import_json_html_preserved(self, sample_quack_data):
        """Test that HTML in greetings is preserved."""
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": json.dumps(sample_quack_data),
                "mode": "full",
                "output_format": "json",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        first_mes = data["data"]["card"]["data"]["first_mes"]
        assert "<p>" in first_mes
        assert "</p>" in first_mes


# ============================================================
# Import Endpoint Tests - Invalid Input
# ============================================================


class TestQuackImportInvalidInput:
    """Tests for invalid input handling."""

    def test_import_invalid_id(self):
        """Test error for invalid Quack ID."""
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": "not a valid input!!!",
            },
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "无效的 Quack ID" in data["detail"]["error"]

    def test_import_empty_input(self):
        """Test error for empty input."""
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": "",
            },
        )
        
        assert response.status_code == 400

    def test_import_invalid_json(self):
        """Test error for invalid JSON input."""
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": "{invalid json",
            },
        )
        
        assert response.status_code == 400


# ============================================================
# Preview Endpoint Tests
# ============================================================


class TestQuackPreview:
    """Tests for preview endpoint."""

    def test_preview_json_input(self, sample_quack_data):
        """Test preview with pasted JSON."""
        response = client.post(
            "/api/quack/preview",
            json={
                "quack_input": json.dumps(sample_quack_data),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "TestCharacter"
        assert data["data"]["creator"] == "TestAuthor"
        assert data["data"]["attr_count"] == 2
        assert data["data"]["lorebook_count"] == 1
        assert data["data"]["source"] == "json"

    def test_preview_invalid_input(self):
        """Test error for invalid input in preview."""
        response = client.post(
            "/api/quack/preview",
            json={
                "quack_input": "not valid!!!",
            },
        )
        
        assert response.status_code == 400


# ============================================================
# API Mode Tests (Mocked)
# ============================================================


class TestQuackImportApiMode:
    """Tests for API mode (with mocked HTTP client)."""

    @patch("app.api.quack.QuackClient")
    def test_import_api_success(self, mock_client_class, sample_quack_data):
        """Test successful import via API mode."""
        mock_client = AsyncMock()
        mock_client.fetch_character_complete.return_value = (
            sample_quack_data,
            sample_quack_data["characterbooks"][0]["entryList"],
        )
        mock_client_class.return_value = mock_client
        
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": "12345",
                "cookies": "token=abc123",
                "mode": "full",
                "output_format": "json",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["source"] == "api"

    @patch("app.api.quack.QuackClient")
    def test_import_api_url_input(self, mock_client_class, sample_quack_data):
        """Test import with URL input."""
        mock_client = AsyncMock()
        mock_client.fetch_character_complete.return_value = (
            sample_quack_data,
            [],
        )
        mock_client_class.return_value = mock_client
        
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": "https://quack.ai/character/12345",
                "mode": "full",
            },
        )
        
        assert response.status_code == 200

    @patch("app.api.quack.QuackClient")
    def test_import_api_unauthorized(self, mock_client_class):
        """Test unauthorized error from API."""
        from app.core.exceptions import UnauthorizedError
        
        mock_client = AsyncMock()
        mock_client.fetch_character_complete.side_effect = UnauthorizedError("Cookie Invalid")
        mock_client_class.return_value = mock_client
        
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": "12345",
            },
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error_code"] == "UNAUTHORIZED"

    @patch("app.api.quack.QuackClient")
    def test_import_api_rate_limited(self, mock_client_class):
        """Test rate limited error from API."""
        from app.core.exceptions import RateLimitedError
        
        mock_client = AsyncMock()
        mock_client.fetch_character_complete.side_effect = RateLimitedError("Rate limited")
        mock_client_class.return_value = mock_client
        
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": "12345",
            },
        )
        
        assert response.status_code == 429

    @patch("app.api.quack.QuackClient")
    def test_import_api_network_error(self, mock_client_class):
        """Test network error from API."""
        from app.core.exceptions import NetworkError
        
        mock_client = AsyncMock()
        mock_client.fetch_character_complete.side_effect = NetworkError("Connection failed")
        mock_client_class.return_value = mock_client
        
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": "12345",
            },
        )
        
        assert response.status_code == 502
        data = response.json()
        assert "hint" in data["detail"]


# ============================================================
# Hard Constraint Tests
# ============================================================


class TestQuackHardConstraints:
    """Tests for hard constraints from spec."""

    def test_constant_true_empty_keys_preserved(self):
        """Test that constant=true entries with empty keys are preserved."""
        quack_data = {
            "charList": [{"name": "Test", "attrs": []}],
            "characterbooks": [
                {
                    "entryList": [
                        {
                            "name": "Constant Entry",
                            "keywords": [],
                            "content": "Always present",
                            "enabled": True,
                            "constant": True,
                        }
                    ]
                }
            ],
            "firstMes": "Hello",
        }
        
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": json.dumps(quack_data),
                "mode": "full",
                "output_format": "json",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        entries = data["data"]["card"]["data"]["character_book"]["entries"]
        assert len(entries) == 1
        assert entries[0]["constant"] is True
        assert entries[0]["keys"] == []  # Empty keys preserved

    def test_selective_calculated_from_secondary_keys(self):
        """Test that selective is True only when secondary_keys exist."""
        quack_data = {
            "charList": [{"name": "Test", "attrs": []}],
            "characterbooks": [
                {
                    "entryList": [
                        {
                            "name": "With Secondary",
                            "keywords": ["key1"],
                            "secondaryKeys": ["sec1"],
                            "content": "Content",
                            "enabled": True,
                        },
                        {
                            "name": "Without Secondary",
                            "keywords": ["key2"],
                            "content": "Content",
                            "enabled": True,
                        },
                    ]
                }
            ],
            "firstMes": "Hello",
        }
        
        response = client.post(
            "/api/quack/import",
            json={
                "quack_input": json.dumps(quack_data),
                "mode": "full",
                "output_format": "json",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        entries = data["data"]["card"]["data"]["character_book"]["entries"]
        
        # Entry with secondary_keys should have selective=True
        assert entries[0]["selective"] is True
        assert entries[0]["secondary_keys"] == ["sec1"]
        
        # Entry without secondary_keys should have selective=False
        assert entries[1]["selective"] is False
