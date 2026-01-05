"""
AI Client 模块测试

测试 AIClient 的请求构建和响应解析。
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.ai_client import (
    Message,
    ChatRequest,
    ChatResponse,
    ChatChoice,
    StreamChunk,
    ModelInfo,
    ModelsResponse,
    ImageRequest,
    ImageData,
    ImageResponse,
    AIClient,
    UpstreamError,
    NetworkError,
    TimeoutError,
    RateLimitedError,
)


class TestMessage:
    """消息模型测试"""
    
    def test_message_creation(self):
        """创建消息"""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name is None
    
    def test_message_with_name(self):
        """带名称的消息"""
        msg = Message(role="system", content="You are helpful", name="System")
        assert msg.name == "System"


class TestChatRequest:
    """聊天请求测试"""
    
    def test_to_dict_basic(self):
        """基本请求转换"""
        request = ChatRequest(
            messages=[Message(role="user", content="Hello")],
            model="gpt-4",
        )
        data = request.to_dict()
        
        assert data["model"] == "gpt-4"
        assert len(data["messages"]) == 1
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "Hello"
        assert data["temperature"] == 0.7
        assert data["stream"] is False
    
    def test_to_dict_with_options(self):
        """带选项的请求转换"""
        request = ChatRequest(
            messages=[Message(role="user", content="Hello")],
            model="gpt-4",
            temperature=0.5,
            max_tokens=100,
            top_p=0.9,
            stream=True,
        )
        data = request.to_dict()
        
        assert data["temperature"] == 0.5
        assert data["max_tokens"] == 100
        assert data["top_p"] == 0.9
        assert data["stream"] is True
    
    def test_to_dict_excludes_none(self):
        """None 值不包含在输出中"""
        request = ChatRequest(
            messages=[],
            model="gpt-4",
        )
        data = request.to_dict()
        
        assert "max_tokens" not in data
        assert "top_p" not in data
        assert "stop" not in data


class TestImageRequest:
    """图像请求测试"""
    
    def test_to_dict(self):
        """请求转换"""
        request = ImageRequest(
            prompt="A cat",
            model="dall-e-3",
            size="1024x1024",
        )
        data = request.to_dict()
        
        assert data["prompt"] == "A cat"
        assert data["model"] == "dall-e-3"
        assert data["size"] == "1024x1024"
        assert data["n"] == 1


class TestStreamChunk:
    """流式响应块测试"""
    
    def test_is_done_false(self):
        """未结束"""
        chunk = StreamChunk(
            id="test",
            object="chat.completion.chunk",
            created=0,
            model="gpt-4",
            choices=[ChatChoice(index=0, delta={"content": "Hi"})],
        )
        assert chunk.is_done is False
    
    def test_is_done_true(self):
        """已结束"""
        chunk = StreamChunk(
            id="test",
            object="chat.completion.chunk",
            created=0,
            model="gpt-4",
            choices=[ChatChoice(index=0, finish_reason="stop")],
        )
        assert chunk.is_done is True


class TestAIClientParsing:
    """AI 客户端响应解析测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端（跳过 URL 验证）"""
        with patch("app.core.ai_client.validate_url_security"):
            return AIClient(
                base_url="https://api.openai.com",
                api_key="test-key",
            )
    
    def test_parse_chat_response(self, client):
        """解析聊天响应"""
        data = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-4",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        
        response = client._parse_chat_response(data)
        
        assert response.id == "chatcmpl-123"
        assert response.model == "gpt-4"
        assert len(response.choices) == 1
        assert response.choices[0].message.content == "Hello!"
        assert response.usage["total_tokens"] == 15
    
    def test_parse_stream_chunk(self, client):
        """解析流式响应块"""
        data = {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1677652288,
            "model": "gpt-4",
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": "Hello"},
                    "finish_reason": None,
                }
            ],
        }
        
        chunk = client._parse_stream_chunk(data)
        
        assert chunk.id == "chatcmpl-123"
        assert chunk.choices[0].delta == {"content": "Hello"}
    
    def test_parse_models_response(self, client):
        """解析模型列表响应"""
        data = {
            "object": "list",
            "data": [
                {"id": "gpt-4", "object": "model", "owned_by": "openai"},
                {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "openai"},
            ],
        }
        
        response = client._parse_models_response(data)
        
        assert response.object == "list"
        assert len(response.data) == 2
        assert response.data[0].id == "gpt-4"
    
    def test_parse_image_response(self, client):
        """解析图像响应"""
        data = {
            "created": 1677652288,
            "data": [
                {
                    "url": "https://example.com/image.png",
                    "revised_prompt": "A cute cat",
                }
            ],
        }
        
        response = client._parse_image_response(data)
        
        assert response.created == 1677652288
        assert len(response.data) == 1
        assert response.data[0].url == "https://example.com/image.png"


class TestAIClientErrors:
    """AI 客户端错误测试"""
    
    def test_upstream_error(self):
        """上游错误"""
        error = UpstreamError("API error: 500", status_code=500)
        assert error.code == "UPSTREAM_ERROR"
        assert error.status_code == 500
    
    def test_network_error(self):
        """网络错误"""
        error = NetworkError("Connection failed")
        assert error.code == "NETWORK_ERROR"
    
    def test_timeout_error(self):
        """超时错误"""
        error = TimeoutError()
        assert error.code == "TIMEOUT"
        assert "timed out" in error.message.lower()
    
    def test_rate_limited_error(self):
        """限流错误"""
        error = RateLimitedError()
        assert error.code == "RATE_LIMITED"
        assert error.status_code == 429
