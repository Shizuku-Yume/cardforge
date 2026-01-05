"""
Proxy API 测试

测试 AI 代理 API 端点。
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestProxyChat:
    """聊天代理 API 测试"""
    
    @patch("app.api.proxy.AIClient")
    def test_chat_non_stream_success(self, mock_client_class):
        """非流式聊天成功"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.id = "chatcmpl-123"
        mock_response.object = "chat.completion"
        mock_response.created = 1677652288
        mock_response.model = "gpt-4"
        mock_response.usage = {"total_tokens": 15}
        
        mock_choice = MagicMock()
        mock_choice.index = 0
        mock_choice.message = MagicMock()
        mock_choice.message.role = "assistant"
        mock_choice.message.content = "Hello!"
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        
        mock_client.chat = AsyncMock(return_value=mock_response)
        
        response = client.post(
            "/api/proxy/chat",
            json={
                "base_url": "https://api.openai.com",
                "api_key": "sk-test",
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "chatcmpl-123"
        assert data["choices"][0]["message"]["content"] == "Hello!"
    
    def test_chat_blocked_url(self):
        """阻止非白名单 URL"""
        response = client.post(
            "/api/proxy/chat",
            json={
                "base_url": "https://evil.com",
                "api_key": "sk-test",
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
        )
        
        assert response.status_code == 403
        assert "not allowed" in response.json()["detail"].lower()
    
    def test_chat_blocked_private_ip(self):
        """阻止私网 IP"""
        response = client.post(
            "/api/proxy/chat",
            json={
                "base_url": "http://192.168.1.1:8080",
                "api_key": "sk-test",
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
        )
        
        assert response.status_code == 403
    
    def test_chat_validation_error(self):
        """请求验证错误"""
        response = client.post(
            "/api/proxy/chat",
            json={
                "base_url": "https://api.openai.com",
                "api_key": "sk-test",
                "model": "gpt-4",
                "messages": [],  # 空消息列表仍然有效，但缺少必需字段会失败
                "temperature": 3.0,  # 超出范围
            },
        )
        
        assert response.status_code == 422


class TestProxyModels:
    """模型列表 API 测试"""
    
    @patch("app.api.proxy.AIClient")
    def test_models_success(self, mock_client_class):
        """获取模型列表成功"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.object = "list"
        
        mock_model1 = MagicMock()
        mock_model1.id = "gpt-4"
        mock_model1.object = "model"
        mock_model1.created = None
        mock_model1.owned_by = "openai"
        
        mock_model2 = MagicMock()
        mock_model2.id = "gpt-3.5-turbo"
        mock_model2.object = "model"
        mock_model2.created = None
        mock_model2.owned_by = "openai"
        
        mock_response.data = [mock_model1, mock_model2]
        
        mock_client.list_models = AsyncMock(return_value=mock_response)
        
        response = client.post(
            "/api/proxy/models",
            json={
                "base_url": "https://api.openai.com",
                "api_key": "sk-test",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 2
        assert data["data"][0]["id"] == "gpt-4"
    
    def test_models_blocked_url(self):
        """阻止非白名单 URL"""
        response = client.post(
            "/api/proxy/models",
            json={
                "base_url": "https://evil.com",
                "api_key": "sk-test",
            },
        )
        
        assert response.status_code == 403


class TestProxyImage:
    """图像生成 API 测试"""
    
    @patch("app.api.proxy.AIClient")
    def test_image_success(self, mock_client_class):
        """图像生成成功"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.created = 1677652288
        
        mock_image = MagicMock()
        mock_image.url = "https://example.com/image.png"
        mock_image.b64_json = None
        mock_image.revised_prompt = "A cute cat"
        
        mock_response.data = [mock_image]
        
        mock_client.generate_image = AsyncMock(return_value=mock_response)
        
        response = client.post(
            "/api/proxy/image",
            json={
                "base_url": "https://api.openai.com",
                "api_key": "sk-test",
                "prompt": "A cute cat",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 1677652288
        assert len(data["data"]) == 1
        assert data["data"][0]["url"] == "https://example.com/image.png"
    
    def test_image_blocked_url(self):
        """阻止非白名单 URL"""
        response = client.post(
            "/api/proxy/image",
            json={
                "base_url": "https://evil.com",
                "api_key": "sk-test",
                "prompt": "A cute cat",
            },
        )
        
        assert response.status_code == 403


class TestRateLimitHeaders:
    """限流头测试"""
    
    @patch("app.api.proxy.AIClient")
    def test_rate_limit_headers_present(self, mock_client_class):
        """响应包含限流头"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.object = "list"
        mock_response.data = []
        
        mock_client.list_models = AsyncMock(return_value=mock_response)
        
        response = client.post(
            "/api/proxy/models",
            json={
                "base_url": "https://api.openai.com",
                "api_key": "sk-test",
            },
        )
        
        assert response.status_code == 200
        assert "x-ratelimit-limit" in response.headers
        assert "x-ratelimit-remaining" in response.headers


class TestSSEStream:
    """SSE 流式响应测试"""
    
    @patch("app.api.proxy.AIClient")
    def test_stream_response_headers(self, mock_client_class):
        """流式响应头正确"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        async def mock_stream():
            yield MagicMock(
                id="test",
                object="chat.completion.chunk",
                created=0,
                model="gpt-4",
                choices=[MagicMock(
                    index=0,
                    delta={"content": "Hi"},
                    finish_reason=None,
                )],
            )
        
        mock_client.chat_stream = mock_stream
        
        response = client.post(
            "/api/proxy/chat",
            json={
                "base_url": "https://api.openai.com",
                "api_key": "sk-test",
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True,
            },
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
