"""
安全策略模块

提供 URL 白名单校验、私网 IP 过滤等 SSRF 防护功能。
"""

import ipaddress
import re
import socket
from typing import List, Optional
from urllib.parse import urlparse

from app.settings import get_settings


class SecurityError(Exception):
    """安全策略阻止的请求"""
    
    def __init__(self, message: str, code: str = "SECURITY_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class URLBlockedError(SecurityError):
    """URL 被阻止（不在白名单内）"""
    
    def __init__(self, url: str, reason: str = "URL not in allowlist"):
        super().__init__(f"Blocked URL: {reason}", "URL_BLOCKED")
        self.url = url


class PrivateIPError(SecurityError):
    """私网 IP 被阻止"""
    
    def __init__(self, ip: str):
        super().__init__(f"Private/internal IP blocked: {ip}", "PRIVATE_IP_BLOCKED")
        self.ip = ip


CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")


def is_private_ip(ip_str: str) -> bool:
    """检查 IP 是否为私网/内网地址。
    
    阻止的地址范围：
    - 10.0.0.0/8 (RFC 1918)
    - 172.16.0.0/12 (RFC 1918)
    - 192.168.0.0/16 (RFC 1918)
    - 169.254.0.0/16 (Link-local / Cloud metadata)
    - 100.64.0.0/10 (CGNAT / Shared Address Space)
    - 127.0.0.0/8 (Loopback)
    - 0.0.0.0 / :: (Unspecified)
    - ::1 (IPv6 loopback)
    - fc00::/7 (IPv6 private)
    - fe80::/10 (IPv6 link-local)
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        
        if ip.is_private:
            return True
        if ip.is_loopback:
            return True
        if ip.is_link_local:
            return True
        if ip.is_reserved:
            return True
        if ip.is_multicast:
            return True
        if ip.is_unspecified:
            return True
        
        if isinstance(ip, ipaddress.IPv4Address):
            if ip in ipaddress.ip_network("169.254.0.0/16"):
                return True
            if ip in CGNAT_NETWORK:
                return True
        
        return False
    except ValueError:
        return True


def is_localhost(hostname: str) -> bool:
    """检查主机名是否为 localhost 变体。"""
    localhost_patterns = [
        "localhost",
        "localhost.localdomain",
        "127.0.0.1",
        "::1",
        "[::1]",
    ]
    hostname_lower = hostname.lower()
    
    if hostname_lower in localhost_patterns:
        return True
    
    if hostname_lower.startswith("127."):
        return True
    
    if re.match(r"^localhost\.\w+$", hostname_lower):
        return True
    
    return False


def resolve_hostname(hostname: str) -> List[str]:
    """解析主机名到 IP 地址列表。"""
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
        ips = list(set(addr[4][0] for addr in results))
        return ips
    except socket.gaierror:
        return []


def validate_url_security(url: str, allow_localhost: Optional[bool] = None) -> None:
    """验证 URL 的安全性。
    
    检查：
    1. URL 是否在白名单内
    2. 目标 IP 是否为私网地址
    3. 是否允许 localhost（可配置）
    
    Args:
        url: 要验证的 URL
        allow_localhost: 是否允许 localhost，None 表示使用配置
        
    Raises:
        URLBlockedError: URL 不在白名单内
        PrivateIPError: 目标为私网 IP
    """
    settings = get_settings()
    
    if allow_localhost is None:
        allow_localhost = settings.proxy_allow_localhost
    
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    
    if not hostname:
        raise URLBlockedError(url, "Invalid URL: no hostname")
    
    if is_localhost(hostname):
        if allow_localhost:
            return
        raise URLBlockedError(url, "localhost access not allowed")
    
    if is_hostname_in_allowlist(hostname, settings.proxy_url_allowlist):
        ips = resolve_hostname(hostname)
        for ip in ips:
            if is_private_ip(ip):
                if not (allow_localhost and is_localhost(hostname)):
                    raise PrivateIPError(ip)
        return
    
    raise URLBlockedError(url, f"Host '{hostname}' not in allowlist")


def is_hostname_in_allowlist(hostname: str, allowlist: List[str]) -> bool:
    """检查主机名是否在白名单内。
    
    支持：
    - 精确匹配: "api.openai.com"
    - 子域名匹配: "*.openai.com" 匹配 "api.openai.com"
    """
    hostname_lower = hostname.lower()
    
    for pattern in allowlist:
        pattern_lower = pattern.lower()
        
        if pattern_lower.startswith("*."):
            suffix = pattern_lower[1:]
            if hostname_lower.endswith(suffix) or hostname_lower == pattern_lower[2:]:
                return True
        else:
            if hostname_lower == pattern_lower:
                return True
            if hostname_lower.endswith("." + pattern_lower):
                return True
    
    return False


def redact_sensitive_data(text: str) -> str:
    """脱敏敏感数据。
    
    替换：
    - API Key 格式: sk-xxx, key-xxx, etc.
    - Bearer Token
    - Cookie 值
    """
    patterns = [
        (r'(sk-)[a-zA-Z0-9]{20,}', r'\1[REDACTED]'),
        (r'(api[-_]?key["\'\s:=]+)[a-zA-Z0-9\-_]{20,}', r'\1[REDACTED]', re.IGNORECASE),
        (r'(bearer\s+)[a-zA-Z0-9\-_.]+', r'\1[REDACTED]', re.IGNORECASE),
        (r'(authorization["\'\s:=]+)[^\s"\']+', r'\1[REDACTED]', re.IGNORECASE),
        (r'(cookie["\'\s:=]+)[^\s"\']+', r'\1[REDACTED]', re.IGNORECASE),
        (r'(x-api-key["\'\s:=]+)[a-zA-Z0-9\-_.]+', r'\1[REDACTED]', re.IGNORECASE),
    ]
    
    result = text
    for pattern_tuple in patterns:
        if len(pattern_tuple) == 3:
            pattern, replacement, flags = pattern_tuple
            result = re.sub(pattern, replacement, result, flags=flags)
        else:
            pattern, replacement = pattern_tuple
            result = re.sub(pattern, replacement, result)
    
    return result


__all__ = [
    "SecurityError",
    "URLBlockedError",
    "PrivateIPError",
    "is_private_ip",
    "is_localhost",
    "validate_url_security",
    "is_hostname_in_allowlist",
    "redact_sensitive_data",
]
