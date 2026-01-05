"""
Security 模块测试

测试 URL 白名单、私网 IP 过滤、日志脱敏等安全功能。
"""

import pytest

from app.core.security import (
    is_private_ip,
    is_localhost,
    is_hostname_in_allowlist,
    validate_url_security,
    redact_sensitive_data,
    URLBlockedError,
    PrivateIPError,
)


class TestIsPrivateIP:
    """私网 IP 检测测试"""
    
    def test_private_ipv4_10_range(self):
        """10.0.0.0/8 应被识别为私网"""
        assert is_private_ip("10.0.0.1") is True
        assert is_private_ip("10.255.255.255") is True
    
    def test_private_ipv4_172_range(self):
        """172.16.0.0/12 应被识别为私网"""
        assert is_private_ip("172.16.0.1") is True
        assert is_private_ip("172.31.255.255") is True
    
    def test_private_ipv4_192_range(self):
        """192.168.0.0/16 应被识别为私网"""
        assert is_private_ip("192.168.0.1") is True
        assert is_private_ip("192.168.255.255") is True
    
    def test_loopback(self):
        """127.0.0.0/8 应被识别为私网"""
        assert is_private_ip("127.0.0.1") is True
        assert is_private_ip("127.255.255.255") is True
    
    def test_link_local(self):
        """169.254.0.0/16 应被识别为私网"""
        assert is_private_ip("169.254.0.1") is True
        assert is_private_ip("169.254.169.254") is True  # Cloud metadata
    
    def test_cgnat(self):
        """100.64.0.0/10 (CGNAT) 应被识别为私网"""
        assert is_private_ip("100.64.0.1") is True
        assert is_private_ip("100.127.255.255") is True
    
    def test_unspecified(self):
        """0.0.0.0 / :: 应被识别为私网"""
        assert is_private_ip("0.0.0.0") is True
        assert is_private_ip("::") is True
    
    def test_public_ipv4(self):
        """公网 IP 不应被识别为私网"""
        assert is_private_ip("8.8.8.8") is False
        assert is_private_ip("1.1.1.1") is False
        assert is_private_ip("208.67.222.222") is False
    
    def test_ipv6_loopback(self):
        """::1 应被识别为私网"""
        assert is_private_ip("::1") is True
    
    def test_invalid_ip(self):
        """无效 IP 应被视为私网（安全优先）"""
        assert is_private_ip("not-an-ip") is True
        assert is_private_ip("") is True


class TestIsLocalhost:
    """Localhost 检测测试"""
    
    def test_localhost_variants(self):
        """各种 localhost 变体"""
        assert is_localhost("localhost") is True
        assert is_localhost("LOCALHOST") is True
        assert is_localhost("127.0.0.1") is True
        assert is_localhost("::1") is True
        assert is_localhost("[::1]") is True
    
    def test_localhost_subdomain(self):
        """localhost 子域名"""
        assert is_localhost("localhost.localdomain") is True
        assert is_localhost("localhost.test") is True
    
    def test_127_x_x_x(self):
        """127.x.x.x 范围"""
        assert is_localhost("127.0.0.2") is True
        assert is_localhost("127.1.2.3") is True
    
    def test_not_localhost(self):
        """非 localhost"""
        assert is_localhost("google.com") is False
        assert is_localhost("api.openai.com") is False


class TestIsHostnameInAllowlist:
    """白名单检测测试"""
    
    def test_exact_match(self):
        """精确匹配"""
        allowlist = ["api.openai.com"]
        assert is_hostname_in_allowlist("api.openai.com", allowlist) is True
        assert is_hostname_in_allowlist("API.OPENAI.COM", allowlist) is True
    
    def test_subdomain_match(self):
        """子域名匹配"""
        allowlist = ["openai.com"]
        assert is_hostname_in_allowlist("api.openai.com", allowlist) is True
        assert is_hostname_in_allowlist("chat.openai.com", allowlist) is True
    
    def test_wildcard_match(self):
        """通配符匹配"""
        allowlist = ["*.openai.com"]
        assert is_hostname_in_allowlist("api.openai.com", allowlist) is True
        assert is_hostname_in_allowlist("openai.com", allowlist) is True
    
    def test_no_match(self):
        """不匹配"""
        allowlist = ["api.openai.com"]
        assert is_hostname_in_allowlist("evil.com", allowlist) is False
        assert is_hostname_in_allowlist("openai.com.evil.com", allowlist) is False


class TestValidateUrlSecurity:
    """URL 安全验证测试"""
    
    def test_allowed_url(self):
        """白名单内的 URL 应通过"""
        validate_url_security("https://api.openai.com/v1/chat")
    
    def test_blocked_url(self):
        """白名单外的 URL 应被阻止"""
        with pytest.raises(URLBlockedError):
            validate_url_security("https://evil.com/api")
    
    def test_localhost_blocked_by_default(self):
        """默认阻止 localhost"""
        with pytest.raises(URLBlockedError):
            validate_url_security("http://localhost:11434/api")
    
    def test_localhost_allowed_when_enabled(self):
        """启用时允许 localhost"""
        validate_url_security(
            "http://localhost:11434/api",
            allow_localhost=True,
        )
    
    def test_private_ip_blocked(self):
        """私网 IP 应被阻止"""
        with pytest.raises(URLBlockedError):
            validate_url_security("http://192.168.1.1:8080/api")
    
    def test_invalid_url(self):
        """无效 URL 应被阻止"""
        with pytest.raises(URLBlockedError):
            validate_url_security("not-a-url")


class TestRedactSensitiveData:
    """日志脱敏测试"""
    
    def test_redact_openai_key(self):
        """脱敏 OpenAI API Key"""
        text = "Using key: sk-1234567890abcdefghij1234567890ab"
        result = redact_sensitive_data(text)
        assert "sk-" in result
        assert "1234567890" not in result
        assert "[REDACTED]" in result
    
    def test_redact_bearer_token(self):
        """脱敏 Bearer Token"""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = redact_sensitive_data(text)
        assert "[REDACTED]" in result
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
    
    def test_redact_api_key_header(self):
        """脱敏 X-API-Key 头"""
        text = 'x-api-key: "my-secret-api-key-12345"'
        result = redact_sensitive_data(text)
        assert "my-secret-api-key" not in result
    
    def test_preserve_normal_text(self):
        """保留正常文本"""
        text = "Normal log message without secrets"
        result = redact_sensitive_data(text)
        assert result == text
