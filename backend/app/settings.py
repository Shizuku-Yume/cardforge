"""Application settings and configuration."""

import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_prefix="CARDFORGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Application
    app_name: str = "CardForge"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # File upload limits
    max_upload_mb: int = 20
    
    # HTTP client settings
    http_timeout: int = 30
    
    # Proxy settings
    proxy_enabled_default: bool = False
    proxy_allow_localhost: bool = False
    proxy_url_allowlist: List[str] = [
        "api.openai.com",
        "api.anthropic.com",
        "openrouter.ai",
        "generativelanguage.googleapis.com",
    ]
    
    # Private network CIDR blocks (SSRF protection)
    proxy_blocked_networks: List[str] = [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",  # Link-local / Cloud metadata
        "127.0.0.0/8",     # Loopback (unless localhost allowed)
    ]
    
    # Rate limiting
    rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 60
    
    # Trusted proxies for X-Forwarded-For handling
    trusted_proxies: List[str] = []  # e.g., ["127.0.0.1", "10.0.0.1"]
    
    # Logging
    log_level: str = "INFO"
    log_redact: bool = True
    
    # Quack API settings
    quack_base_url: str = "https://api.quack.ai"
    quack_character_info_path: str = "/character/info"
    quack_lorebook_path: str = "/character/book"
    
    @property
    def max_upload_bytes(self) -> int:
        """Maximum upload size in bytes."""
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
