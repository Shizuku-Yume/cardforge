"""
请求限流中间件

基于 IP 的简单滑动窗口限流实现。
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.settings import get_settings


@dataclass
class RateLimitConfig:
    """限流配置"""
    requests: int  # 允许的请求数
    window_seconds: int  # 时间窗口（秒）


class RateLimiter:
    """滑动窗口限流器"""
    
    def __init__(self, requests: int = 10, window_seconds: int = 60):
        self.requests = requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)
    
    def is_allowed(self, key: str) -> bool:
        """检查请求是否被允许。
        
        Args:
            key: 限流键（通常是 IP 地址）
            
        Returns:
            True 如果允许，False 如果超限
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        self._requests[key] = [
            ts for ts in self._requests[key] if ts > window_start
        ]
        
        if len(self._requests[key]) >= self.requests:
            return False
        
        self._requests[key].append(now)
        return True
    
    def get_remaining(self, key: str) -> int:
        """获取剩余可用请求数。"""
        now = time.time()
        window_start = now - self.window_seconds
        
        valid_requests = [
            ts for ts in self._requests[key] if ts > window_start
        ]
        
        return max(0, self.requests - len(valid_requests))
    
    def get_reset_time(self, key: str) -> Optional[float]:
        """获取限流重置时间（秒）。"""
        if not self._requests[key]:
            return None
        
        now = time.time()
        window_start = now - self.window_seconds
        
        valid_requests = [
            ts for ts in self._requests[key] if ts > window_start
        ]
        
        if not valid_requests:
            return None
        
        oldest = min(valid_requests)
        return self.window_seconds - (now - oldest)
    
    def cleanup(self) -> int:
        """清理过期的请求记录。
        
        Returns:
            清理的键数量
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        keys_to_remove = []
        for key, timestamps in self._requests.items():
            valid = [ts for ts in timestamps if ts > window_start]
            if not valid:
                keys_to_remove.append(key)
            else:
                self._requests[key] = valid
        
        for key in keys_to_remove:
            del self._requests[key]
        
        return len(keys_to_remove)


_proxy_limiter: Optional[RateLimiter] = None


def get_proxy_rate_limiter() -> RateLimiter:
    """获取代理接口限流器（单例）。"""
    global _proxy_limiter
    if _proxy_limiter is None:
        settings = get_settings()
        _proxy_limiter = RateLimiter(
            requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
    return _proxy_limiter


def get_client_ip(request: Request) -> str:
    """获取客户端真实 IP。
    
    仅在请求来自可信代理时信任代理头（X-Forwarded-For、X-Real-IP）。
    """
    settings = get_settings()
    trusted_proxies = set(settings.trusted_proxies)
    
    direct_ip = request.client.host if request.client else "unknown"
    
    if trusted_proxies and direct_ip in trusted_proxies:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
    
    return direct_ip


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""
    
    def __init__(self, app, limiter: RateLimiter, path_prefix: str = "/api/proxy"):
        super().__init__(app)
        self.limiter = limiter
        self.path_prefix = path_prefix
    
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith(self.path_prefix):
            return await call_next(request)
        
        client_ip = get_client_ip(request)
        
        if not self.limiter.is_allowed(client_ip):
            reset_time = self.limiter.get_reset_time(client_ip)
            headers = {}
            if reset_time is not None:
                headers["Retry-After"] = str(int(reset_time) + 1)
                headers["X-RateLimit-Reset"] = str(int(time.time() + reset_time))
            
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers=headers,
            )
        
        response = await call_next(request)
        
        remaining = self.limiter.get_remaining(client_ip)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response


__all__ = [
    "RateLimitConfig",
    "RateLimiter",
    "RateLimitMiddleware",
    "get_proxy_rate_limiter",
    "get_client_ip",
]
