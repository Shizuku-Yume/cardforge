"""
Tests for Quack Client Module.

Tests Cookie parsing, ID extraction, and error classification.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.core.quack_client import (
    CookieParser,
    QuackClient,
    extract_quack_id,
    DEFAULT_USER_AGENT,
)
from app.core.exceptions import (
    NetworkError,
    RateLimitedError,
    TimeoutError,
    UnauthorizedError,
)


class TestCookieParser:
    """Tests for CookieParser class."""

    def test_parse_empty_string(self):
        """Empty string returns empty dict."""
        result = CookieParser.parse("")
        assert result == {}

    def test_parse_header_string_simple(self):
        """Parse simple header string format."""
        cookie_str = "session=abc123; token=xyz789"
        result = CookieParser.parse(cookie_str)
        assert result == {"session": "abc123", "token": "xyz789"}

    def test_parse_header_string_with_prefix(self):
        """Parse header string with 'Cookie: ' prefix."""
        cookie_str = "Cookie: session=abc123; token=xyz789"
        result = CookieParser.parse(cookie_str)
        assert result == {"session": "abc123", "token": "xyz789"}

    def test_parse_header_string_with_equals_in_value(self):
        """Parse cookie value containing '=' character."""
        cookie_str = "auth=base64==token; simple=value"
        result = CookieParser.parse(cookie_str)
        assert result == {"auth": "base64==token", "simple": "value"}

    def test_parse_json_format(self):
        """Parse JSON format (EditThisCookie export)."""
        cookies = [
            {"name": "session", "value": "abc123"},
            {"name": "token", "value": "xyz789"},
        ]
        result = CookieParser.parse(json.dumps(cookies))
        assert result == {"session": "abc123", "token": "xyz789"}

    def test_parse_json_format_with_extra_fields(self):
        """Parse JSON format with extra fields (full EditThisCookie export)."""
        cookies = [
            {
                "name": "session",
                "value": "abc123",
                "domain": ".example.com",
                "path": "/",
                "expirationDate": 1234567890,
            },
        ]
        result = CookieParser.parse(json.dumps(cookies))
        assert result == {"session": "abc123"}

    def test_parse_json_invalid(self):
        """Invalid JSON returns empty dict."""
        result = CookieParser.parse("[invalid json")
        assert result == {}

    def test_parse_netscape_format(self):
        """Parse Netscape cookies.txt format."""
        netscape = """# Netscape HTTP Cookie File
.quack.ai\tTRUE\t/\tFALSE\t1234567890\tsession\tabc123
.quack.ai\tTRUE\t/\tFALSE\t1234567890\ttoken\txyz789"""
        result = CookieParser.parse(netscape)
        assert result == {"session": "abc123", "token": "xyz789"}

    def test_parse_netscape_with_comment_only(self):
        """Netscape format with only comments."""
        netscape = "# Just a comment\n# Another comment"
        result = CookieParser.parse(netscape)
        assert result == {}

    def test_to_header_string(self):
        """Convert cookie dict to header string."""
        cookies = {"session": "abc123", "token": "xyz789"}
        result = CookieParser.to_header_string(cookies)
        assert "session=abc123" in result
        assert "token=xyz789" in result
        assert "; " in result


class TestExtractQuackId:
    """Tests for extract_quack_id function."""

    def test_extract_numeric_id(self):
        """Extract numeric ID directly."""
        assert extract_quack_id("1234567") == "1234567"

    def test_extract_alphanumeric_sid(self):
        """Extract alphanumeric SID directly."""
        assert extract_quack_id("abc123def456") == "abc123def456"

    def test_extract_from_full_url(self):
        """Extract ID from full Quack URL."""
        url = "https://quack.ai/character/1234567"
        assert extract_quack_id(url) == "1234567"

    def test_extract_from_mobile_url(self):
        """Extract ID from mobile Quack URL."""
        url = "https://m.quack.ai/character/abc123"
        assert extract_quack_id(url) == "abc123"

    def test_extract_from_url_with_query(self):
        """Extract ID from URL with query parameters."""
        url = "https://quack.ai/character/1234567?ref=share"
        assert extract_quack_id(url) == "1234567"

    def test_extract_empty_string(self):
        """Empty string returns None."""
        assert extract_quack_id("") is None

    def test_extract_invalid_input(self):
        """Invalid input returns None."""
        assert extract_quack_id("not-valid-@#$%") is None

    def test_extract_with_whitespace(self):
        """Strip whitespace from input."""
        assert extract_quack_id("  1234567  ") == "1234567"


class TestQuackClientHeaders:
    """Tests for QuackClient header building."""

    def test_headers_without_cookies(self):
        """Headers without cookies."""
        client = QuackClient()
        headers = client._get_headers()
        assert headers["User-Agent"] == DEFAULT_USER_AGENT
        assert headers["Accept"] == "application/json"
        assert "Cookie" not in headers

    def test_headers_with_cookies(self):
        """Headers with cookies."""
        client = QuackClient(cookies={"session": "abc123"})
        headers = client._get_headers()
        assert headers["Cookie"] == "session=abc123"

    def test_custom_user_agent(self):
        """Custom User-Agent."""
        client = QuackClient(user_agent="CustomAgent/1.0")
        headers = client._get_headers()
        assert headers["User-Agent"] == "CustomAgent/1.0"


class TestQuackClientErrorClassification:
    """Tests for QuackClient error classification."""

    def test_error_401_unauthorized(self):
        """401 raises UnauthorizedError."""
        client = QuackClient()
        with pytest.raises(UnauthorizedError) as exc_info:
            client._classify_error(401, "Unauthorized")
        assert "Cookie Invalid" in str(exc_info.value)

    def test_error_403_forbidden(self):
        """403 raises NetworkError with hint."""
        client = QuackClient()
        with pytest.raises(NetworkError) as exc_info:
            client._classify_error(403, "Forbidden")
        assert "blocked" in str(exc_info.value).lower() or "forbidden" in str(exc_info.value).lower()

    def test_error_429_rate_limited(self):
        """429 raises RateLimitedError."""
        client = QuackClient()
        with pytest.raises(RateLimitedError) as exc_info:
            client._classify_error(429, "Rate limited")
        assert "Rate limited" in str(exc_info.value)

    def test_error_500_server_error(self):
        """500 raises NetworkError."""
        client = QuackClient()
        with pytest.raises(NetworkError) as exc_info:
            client._classify_error(500, "Internal Server Error")
        assert "500" in str(exc_info.value)


class TestQuackClientAsync:
    """Async tests for QuackClient."""

    @pytest.mark.asyncio
    async def test_fetch_character_info_success(self):
        """Successful character info fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "name": "TestChar",
            "charList": [{"name": "TestChar"}],
        }
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = QuackClient(cookies={"session": "test"})
            result = await client.fetch_character_info("1234567")
            
            assert result["name"] == "TestChar"
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_character_info_401(self):
        """401 error raises UnauthorizedError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = QuackClient()
            with pytest.raises(UnauthorizedError):
                await client.fetch_character_info("1234567")

    @pytest.mark.asyncio
    async def test_fetch_character_info_timeout(self):
        """Timeout raises TimeoutError."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client_class.return_value = mock_client
            
            client = QuackClient()
            with pytest.raises(TimeoutError):
                await client.fetch_character_info("1234567")

    @pytest.mark.asyncio
    async def test_fetch_lorebook_success(self):
        """Successful lorebook fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": [
                {
                    "bid": "book1",
                    "name": "Test Book",
                    "entryList": [
                        {"id": "entry1", "name": "Entry 1", "content": "Content 1"},
                    ],
                }
            ],
        }
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = QuackClient()
            result = await client.fetch_lorebook("1234567")
            
            assert len(result) == 1
            assert result[0]["name"] == "Entry 1"

    @pytest.mark.asyncio
    async def test_fetch_character_complete(self):
        """Fetch complete character data (info + lorebook)."""
        info_response = MagicMock()
        info_response.status_code = 200
        info_response.json.return_value = {
            "code": 0,
            "name": "TestChar",
            "charList": [{"name": "TestChar"}],
        }
        
        lorebook_response = MagicMock()
        lorebook_response.status_code = 200
        lorebook_response.json.return_value = {"code": 0, "data": []}
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=[info_response, lorebook_response])
            mock_client_class.return_value = mock_client
            
            client = QuackClient()
            info, lorebook = await client.fetch_character_complete("1234567")
            
            assert info["name"] == "TestChar"
            assert lorebook == []


class TestCookieParserEdgeCases:
    """Edge case tests for CookieParser."""

    def test_parse_whitespace_handling(self):
        """Handle various whitespace scenarios."""
        cookie_str = "  session = abc123 ; token=xyz789  "
        result = CookieParser.parse(cookie_str)
        assert "session" in result or "session " in result

    def test_parse_empty_value(self):
        """Handle empty cookie values."""
        cookie_str = "empty=; valid=value"
        result = CookieParser.parse(cookie_str)
        assert result["empty"] == ""
        assert result["valid"] == "value"

    def test_parse_unicode_value(self):
        """Handle unicode in cookie values."""
        cookies = [{"name": "test", "value": "你好世界"}]
        result = CookieParser.parse(json.dumps(cookies))
        assert result["test"] == "你好世界"
