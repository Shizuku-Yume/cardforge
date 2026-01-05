"""
Rate Limit 中间件测试

测试限流器和限流中间件。
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from app.middleware.rate_limit import (
    RateLimiter,
    get_client_ip,
)


class TestRateLimiter:
    """限流器测试"""
    
    def test_allows_requests_under_limit(self):
        """限制内的请求应被允许"""
        limiter = RateLimiter(requests=5, window_seconds=60)
        
        for _ in range(5):
            assert limiter.is_allowed("test-ip") is True
    
    def test_blocks_requests_over_limit(self):
        """超限的请求应被阻止"""
        limiter = RateLimiter(requests=3, window_seconds=60)
        
        for _ in range(3):
            limiter.is_allowed("test-ip")
        
        assert limiter.is_allowed("test-ip") is False
    
    def test_different_keys_independent(self):
        """不同键应独立计数"""
        limiter = RateLimiter(requests=2, window_seconds=60)
        
        assert limiter.is_allowed("ip-1") is True
        assert limiter.is_allowed("ip-1") is True
        assert limiter.is_allowed("ip-1") is False
        
        assert limiter.is_allowed("ip-2") is True
        assert limiter.is_allowed("ip-2") is True
    
    def test_get_remaining(self):
        """获取剩余请求数"""
        limiter = RateLimiter(requests=5, window_seconds=60)
        
        assert limiter.get_remaining("test-ip") == 5
        
        limiter.is_allowed("test-ip")
        assert limiter.get_remaining("test-ip") == 4
        
        limiter.is_allowed("test-ip")
        limiter.is_allowed("test-ip")
        assert limiter.get_remaining("test-ip") == 2
    
    def test_sliding_window(self):
        """滑动窗口应正确过期"""
        limiter = RateLimiter(requests=2, window_seconds=1)
        
        assert limiter.is_allowed("test-ip") is True
        assert limiter.is_allowed("test-ip") is True
        assert limiter.is_allowed("test-ip") is False
        
        time.sleep(1.1)
        
        assert limiter.is_allowed("test-ip") is True
    
    def test_cleanup(self):
        """清理过期记录"""
        limiter = RateLimiter(requests=2, window_seconds=1)
        
        limiter.is_allowed("ip-1")
        limiter.is_allowed("ip-2")
        
        time.sleep(1.1)
        
        removed = limiter.cleanup()
        assert removed == 2
    
    def test_get_reset_time(self):
        """获取重置时间"""
        limiter = RateLimiter(requests=2, window_seconds=10)
        
        assert limiter.get_reset_time("test-ip") is None
        
        limiter.is_allowed("test-ip")
        reset_time = limiter.get_reset_time("test-ip")
        
        assert reset_time is not None
        assert 9 < reset_time <= 10


class TestGetClientIP:
    """客户端 IP 获取测试"""
    
    def test_direct_client(self):
        """直连客户端（无可信代理）"""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "1.2.3.4"
        
        mock_settings = MagicMock()
        mock_settings.trusted_proxies = []
        with patch("app.middleware.rate_limit.get_settings", return_value=mock_settings):
            assert get_client_ip(request) == "1.2.3.4"
    
    def test_x_forwarded_for_ignored_without_trusted_proxy(self):
        """无可信代理时忽略 X-Forwarded-For"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"
        
        mock_settings = MagicMock()
        mock_settings.trusted_proxies = []
        with patch("app.middleware.rate_limit.get_settings", return_value=mock_settings):
            assert get_client_ip(request) == "10.0.0.1"
    
    def test_x_forwarded_for_trusted(self):
        """可信代理时使用 X-Forwarded-For"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        
        mock_settings = MagicMock()
        mock_settings.trusted_proxies = ["127.0.0.1"]
        with patch("app.middleware.rate_limit.get_settings", return_value=mock_settings):
            assert get_client_ip(request) == "1.2.3.4"
    
    def test_x_real_ip_trusted(self):
        """可信代理时使用 X-Real-IP"""
        request = MagicMock()
        request.headers = {"X-Real-IP": "1.2.3.4"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        
        mock_settings = MagicMock()
        mock_settings.trusted_proxies = ["127.0.0.1"]
        with patch("app.middleware.rate_limit.get_settings", return_value=mock_settings):
            assert get_client_ip(request) == "1.2.3.4"
    
    def test_no_client(self):
        """无客户端信息"""
        request = MagicMock()
        request.headers = {}
        request.client = None
        
        mock_settings = MagicMock()
        mock_settings.trusted_proxies = []
        with patch("app.middleware.rate_limit.get_settings", return_value=mock_settings):
            assert get_client_ip(request) == "unknown"
