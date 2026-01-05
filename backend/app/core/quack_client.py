"""
Quack API Client Module

Provides HTTP client functionality for fetching character data from QuackAI.
Handles Cookie parsing, User-Agent, and error classification.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from ..settings import get_settings
from .exceptions import NetworkError, RateLimitedError, TimeoutError, UnauthorizedError


# Common User-Agent for Quack requests
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class CookieParser:
    """
    Cookie parser supporting multiple formats:
    - Netscape format (cookies.txt export)
    - JSON format (EditThisCookie export)
    - Header string format (Cookie: key=value; key2=value2)
    """

    @staticmethod
    def parse(cookie_input: str) -> Dict[str, str]:
        """
        Parse cookies from various formats into a dict.
        
        Args:
            cookie_input: Cookie string in any supported format
            
        Returns:
            Dict of cookie name -> value
        """
        cookie_input = cookie_input.strip()
        
        if not cookie_input:
            return {}
        
        # Try JSON format first (array of cookie objects)
        if cookie_input.startswith("["):
            return CookieParser._parse_json(cookie_input)
        
        # Try Netscape format (tab-separated, starts with domain or comment)
        if "\t" in cookie_input or cookie_input.startswith("#"):
            return CookieParser._parse_netscape(cookie_input)
        
        # Fall back to header string format (key=value; key2=value2)
        return CookieParser._parse_header_string(cookie_input)

    @staticmethod
    def _parse_json(cookie_input: str) -> Dict[str, str]:
        """Parse JSON format cookies (EditThisCookie export)."""
        try:
            cookies = json.loads(cookie_input)
            if not isinstance(cookies, list):
                return {}
            
            result = {}
            for cookie in cookies:
                if isinstance(cookie, dict):
                    name = cookie.get("name", "")
                    value = cookie.get("value", "")
                    if name:
                        result[name] = value
            return result
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _parse_netscape(cookie_input: str) -> Dict[str, str]:
        """Parse Netscape format cookies (cookies.txt)."""
        result = {}
        lines = cookie_input.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            
            # Netscape format: domain  flag  path  secure  expiration  name  value
            parts = line.split("\t")
            if len(parts) >= 7:
                name = parts[5]
                value = parts[6]
                result[name] = value
        
        return result

    @staticmethod
    def _parse_header_string(cookie_input: str) -> Dict[str, str]:
        """Parse header string format (key=value; key2=value2)."""
        result = {}
        
        # Remove "Cookie: " prefix if present
        if cookie_input.lower().startswith("cookie:"):
            cookie_input = cookie_input[7:].strip()
        
        # Split by semicolon
        pairs = cookie_input.split(";")
        for pair in pairs:
            pair = pair.strip()
            if "=" in pair:
                # Only split on first '=' to handle values with '='
                idx = pair.index("=")
                name = pair[:idx].strip()
                value = pair[idx + 1:].strip()
                if name:
                    result[name] = value
        
        return result

    @staticmethod
    def to_header_string(cookies: Dict[str, str]) -> str:
        """Convert cookie dict to header string format."""
        return "; ".join(f"{k}={v}" for k, v in cookies.items())


def extract_quack_id(input_str: str) -> Optional[str]:
    """
    Extract Quack character ID from URL or direct ID input.
    
    Supports:
    - Direct numeric ID: "1234567"
    - Direct SID: "abc123def456"
    - Full URL: "https://quack.ai/character/1234567"
    - Mobile URL: "https://m.quack.ai/character/abc123"
    
    Returns:
        Character ID/SID or None if invalid
    """
    input_str = input_str.strip()
    
    if not input_str:
        return None
    
    # Try to parse as URL
    if "quack" in input_str.lower() or input_str.startswith("http"):
        try:
            parsed = urlparse(input_str)
            path_parts = parsed.path.strip("/").split("/")
            
            # Look for /character/{id} pattern
            for i, part in enumerate(path_parts):
                if part == "character" and i + 1 < len(path_parts):
                    return path_parts[i + 1]
            
            # If path is just an ID
            if len(path_parts) == 1 and path_parts[0]:
                return path_parts[0]
        except Exception:
            pass
    
    # Check if it's a direct ID (numeric or alphanumeric SID)
    if re.match(r"^[a-zA-Z0-9_-]+$", input_str):
        return input_str
    
    return None


class QuackClient:
    """
    Async HTTP client for QuackAI API.
    
    Handles:
    - Cookie-based authentication
    - Character info fetching
    - World book fetching
    - Error classification (401, 403, 429)
    """

    def __init__(
        self,
        cookies: Optional[Dict[str, str]] = None,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: Optional[int] = None,
    ):
        """
        Initialize QuackClient.
        
        Args:
            cookies: Dict of cookies for authentication
            user_agent: User-Agent header value
            timeout: Request timeout in seconds (default from settings)
        """
        settings = get_settings()
        self.cookies = cookies or {}
        self.user_agent = user_agent
        self.timeout = timeout or settings.http_timeout

    def _get_headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        if self.cookies:
            headers["Cookie"] = CookieParser.to_header_string(self.cookies)
        
        return headers

    def _classify_error(self, status_code: int, response_body: str) -> None:
        """
        Classify HTTP error and raise appropriate exception.
        
        Args:
            status_code: HTTP status code
            response_body: Response body for additional context
        """
        if status_code == 401:
            raise UnauthorizedError("Cookie Invalid - Please provide valid authentication cookies")
        
        if status_code == 403:
            raise NetworkError(
                "Access forbidden - Your IP may be blocked or cookies expired",
                details={"status_code": 403, "hint": "Try updating cookies or using a different network"}
            )
        
        if status_code == 429:
            raise RateLimitedError(
                "Rate limited by Quack API - Please wait before retrying"
            )
        
        if status_code >= 500:
            raise NetworkError(
                f"Quack API server error (HTTP {status_code})",
                details={"status_code": status_code}
            )
        
        if status_code >= 400:
            raise NetworkError(
                f"Quack API request failed (HTTP {status_code})",
                details={"status_code": status_code, "body": response_body[:500]}
            )

    async def fetch_character_info(self, character_id: str) -> Dict[str, Any]:
        """
        Fetch character info from Quack API.
        
        Args:
            character_id: Character ID or SID
            
        Returns:
            Character info dict
            
        Raises:
            UnauthorizedError: Cookie invalid (401)
            RateLimitedError: Rate limited (429)
            NetworkError: Other network errors
            TimeoutError: Request timeout
        """
        settings = get_settings()
        url = f"{settings.quack_base_url}{settings.quack_character_info_path}"
        params = {"id": character_id}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                )
                
                if response.status_code != 200:
                    self._classify_error(response.status_code, response.text)
                
                data = response.json()
                
                # Check for API-level errors
                if isinstance(data, dict):
                    code = data.get("code")
                    if code is not None and code != 0:
                        msg = data.get("message", data.get("msg", "Unknown error"))
                        if code == 401 or "auth" in str(msg).lower():
                            raise UnauthorizedError(f"Cookie Invalid - {msg}")
                        raise NetworkError(f"Quack API error: {msg}", details={"code": code})
                
                return data
                
            except httpx.TimeoutException:
                raise TimeoutError("Quack API request timed out")
            except httpx.RequestError as e:
                raise NetworkError(f"Network error: {str(e)}")

    async def fetch_lorebook(self, character_id: str) -> List[Dict[str, Any]]:
        """
        Fetch character world book from Quack API.
        
        Args:
            character_id: Character ID or SID
            
        Returns:
            List of world book entries
        """
        settings = get_settings()
        url = f"{settings.quack_base_url}{settings.quack_lorebook_path}"
        params = {"id": character_id}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                )
                
                if response.status_code != 200:
                    self._classify_error(response.status_code, response.text)
                
                data = response.json()
                
                # Extract entries from response
                if isinstance(data, dict):
                    code = data.get("code")
                    if code is not None and code != 0:
                        msg = data.get("message", data.get("msg", "Unknown error"))
                        raise NetworkError(f"Quack API error: {msg}", details={"code": code})
                    
                    # Quack lorebook format: {"code": 0, "data": [...]}
                    entries = data.get("data", [])
                    if isinstance(entries, list):
                        # Flatten if nested structure
                        result = []
                        for item in entries:
                            if isinstance(item, dict) and "entryList" in item:
                                result.extend(item.get("entryList", []))
                            elif isinstance(item, dict):
                                result.append(item)
                        return result
                    return []
                
                return data if isinstance(data, list) else []
                
            except httpx.TimeoutException:
                raise TimeoutError("Quack API request timed out")
            except httpx.RequestError as e:
                raise NetworkError(f"Network error: {str(e)}")

    async def fetch_character_complete(
        self, character_id: str
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Fetch complete character data (info + lorebook).
        
        Args:
            character_id: Character ID or SID
            
        Returns:
            Tuple of (character_info, lorebook_entries)
        """
        info = await self.fetch_character_info(character_id)
        
        # Try to fetch lorebook (may be empty or fail)
        try:
            lorebook = await self.fetch_lorebook(character_id)
        except Exception:
            lorebook = []
        
        return info, lorebook


__all__ = [
    "CookieParser",
    "QuackClient",
    "extract_quack_id",
    "DEFAULT_USER_AGENT",
]
