"""
AI 客户端模块

提供 OpenAI 兼容的 AI 服务客户端，支持流式和非流式响应。
"""

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.settings import get_settings
from app.core.security import validate_url_security, redact_sensitive_data


@dataclass
class Message:
    """聊天消息"""
    role: str  # "system" | "user" | "assistant"
    content: str
    name: Optional[str] = None


@dataclass
class ChatRequest:
    """聊天请求"""
    messages: List[Message]
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为 API 请求字典。"""
        data = {
            "model": self.model,
            "messages": [
                {k: v for k, v in {"role": m.role, "content": m.content, "name": m.name}.items() if v is not None}
                for m in self.messages
            ],
            "temperature": self.temperature,
            "stream": self.stream,
        }
        
        if self.max_tokens is not None:
            data["max_tokens"] = self.max_tokens
        if self.top_p is not None:
            data["top_p"] = self.top_p
        if self.frequency_penalty is not None:
            data["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty is not None:
            data["presence_penalty"] = self.presence_penalty
        if self.stop:
            data["stop"] = self.stop
        
        return data


@dataclass
class ChatChoice:
    """聊天响应选项"""
    index: int
    message: Optional[Message] = None
    delta: Optional[Dict[str, str]] = None
    finish_reason: Optional[str] = None


@dataclass
class ChatResponse:
    """聊天响应"""
    id: str
    object: str
    created: int
    model: str
    choices: List[ChatChoice]
    usage: Optional[Dict[str, int]] = None


@dataclass
class StreamChunk:
    """流式响应块"""
    id: str
    object: str
    created: int
    model: str
    choices: List[ChatChoice]
    
    @property
    def is_done(self) -> bool:
        """检查是否为结束标记。"""
        return len(self.choices) > 0 and self.choices[0].finish_reason is not None


@dataclass
class ModelInfo:
    """模型信息"""
    id: str
    object: str = "model"
    created: Optional[int] = None
    owned_by: Optional[str] = None


@dataclass
class ModelsResponse:
    """模型列表响应"""
    object: str = "list"
    data: List[ModelInfo] = field(default_factory=list)


@dataclass
class ImageRequest:
    """图像生成请求"""
    prompt: str
    model: str = "dall-e-3"
    n: int = 1
    size: str = "1024x1024"
    quality: str = "standard"
    response_format: str = "url"
    style: str = "vivid"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "model": self.model,
            "n": self.n,
            "size": self.size,
            "quality": self.quality,
            "response_format": self.response_format,
            "style": self.style,
        }


@dataclass
class ImageData:
    """图像数据"""
    url: Optional[str] = None
    b64_json: Optional[str] = None
    revised_prompt: Optional[str] = None


@dataclass
class ImageResponse:
    """图像生成响应"""
    created: int
    data: List[ImageData]


class AIClientError(Exception):
    """AI 客户端错误"""
    
    def __init__(self, message: str, code: str, status_code: Optional[int] = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class UpstreamError(AIClientError):
    """上游 AI 服务错误"""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message, "UPSTREAM_ERROR", status_code)


class NetworkError(AIClientError):
    """网络错误"""
    
    def __init__(self, message: str):
        super().__init__(message, "NETWORK_ERROR")


class TimeoutError(AIClientError):
    """超时错误"""
    
    def __init__(self, message: str = "Request timed out"):
        super().__init__(message, "TIMEOUT")


class RateLimitedError(AIClientError):
    """限流错误"""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, "RATE_LIMITED", 429)


class AIClient:
    """OpenAI 兼容 AI 客户端"""
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 60.0,
        max_response_size: int = 50 * 1024 * 1024,  # 50MB
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_response_size = max_response_size
        
        validate_url_security(self.base_url)
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头。"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """发送聊天请求（非流式）。"""
        request.stream = False
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=self._get_headers(),
                    json=request.to_dict(),
                )
                
                if response.status_code == 429:
                    raise RateLimitedError()
                
                if response.status_code >= 400:
                    error_body = response.text
                    raise UpstreamError(
                        f"API error: {error_body}",
                        status_code=response.status_code,
                    )
                
                data = response.json()
                return self._parse_chat_response(data)
                
            except httpx.TimeoutException:
                raise TimeoutError()
            except httpx.NetworkError as e:
                raise NetworkError(f"Network error: {str(e)}")
    
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """发送流式聊天请求。"""
        request.stream = True
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/chat/completions",
                    headers=self._get_headers(),
                    json=request.to_dict(),
                ) as response:
                    if response.status_code == 429:
                        raise RateLimitedError()
                    
                    if response.status_code >= 400:
                        error_body = await response.aread()
                        raise UpstreamError(
                            f"API error: {error_body.decode()}",
                            status_code=response.status_code,
                        )
                    
                    buffer = ""
                    bytes_read = 0
                    
                    async for chunk in response.aiter_text():
                        bytes_read += len(chunk.encode())
                        if bytes_read > self.max_response_size:
                            raise UpstreamError("Response too large")
                        
                        buffer += chunk
                        
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            
                            if not line:
                                continue
                            
                            if line.startswith("data: "):
                                data_str = line[6:]
                                
                                if data_str == "[DONE]":
                                    return
                                
                                try:
                                    data = json.loads(data_str)
                                    yield self._parse_stream_chunk(data)
                                except json.JSONDecodeError:
                                    continue
                            
            except httpx.TimeoutException:
                raise TimeoutError()
            except httpx.NetworkError as e:
                raise NetworkError(f"Network error: {str(e)}")
    
    async def list_models(self) -> ModelsResponse:
        """获取模型列表。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/v1/models",
                    headers=self._get_headers(),
                )
                
                if response.status_code == 429:
                    raise RateLimitedError()
                
                if response.status_code >= 400:
                    error_body = response.text
                    raise UpstreamError(
                        f"API error: {error_body}",
                        status_code=response.status_code,
                    )
                
                data = response.json()
                return self._parse_models_response(data)
                
            except httpx.TimeoutException:
                raise TimeoutError()
            except httpx.NetworkError as e:
                raise NetworkError(f"Network error: {str(e)}")
    
    async def generate_image(self, request: ImageRequest) -> ImageResponse:
        """生成图像。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/v1/images/generations",
                    headers=self._get_headers(),
                    json=request.to_dict(),
                )
                
                if response.status_code == 429:
                    raise RateLimitedError()
                
                if response.status_code >= 400:
                    error_body = response.text
                    raise UpstreamError(
                        f"API error: {error_body}",
                        status_code=response.status_code,
                    )
                
                data = response.json()
                return self._parse_image_response(data)
                
            except httpx.TimeoutException:
                raise TimeoutError()
            except httpx.NetworkError as e:
                raise NetworkError(f"Network error: {str(e)}")
    
    def _parse_chat_response(self, data: Dict[str, Any]) -> ChatResponse:
        """解析聊天响应。"""
        choices = []
        for choice_data in data.get("choices", []):
            message_data = choice_data.get("message", {})
            message = Message(
                role=message_data.get("role", "assistant"),
                content=message_data.get("content", ""),
            )
            choices.append(ChatChoice(
                index=choice_data.get("index", 0),
                message=message,
                finish_reason=choice_data.get("finish_reason"),
            ))
        
        return ChatResponse(
            id=data.get("id", ""),
            object=data.get("object", "chat.completion"),
            created=data.get("created", 0),
            model=data.get("model", ""),
            choices=choices,
            usage=data.get("usage"),
        )
    
    def _parse_stream_chunk(self, data: Dict[str, Any]) -> StreamChunk:
        """解析流式响应块。"""
        choices = []
        for choice_data in data.get("choices", []):
            delta = choice_data.get("delta", {})
            choices.append(ChatChoice(
                index=choice_data.get("index", 0),
                delta=delta,
                finish_reason=choice_data.get("finish_reason"),
            ))
        
        return StreamChunk(
            id=data.get("id", ""),
            object=data.get("object", "chat.completion.chunk"),
            created=data.get("created", 0),
            model=data.get("model", ""),
            choices=choices,
        )
    
    def _parse_models_response(self, data: Dict[str, Any]) -> ModelsResponse:
        """解析模型列表响应。"""
        models = []
        for model_data in data.get("data", []):
            models.append(ModelInfo(
                id=model_data.get("id", ""),
                object=model_data.get("object", "model"),
                created=model_data.get("created"),
                owned_by=model_data.get("owned_by"),
            ))
        
        return ModelsResponse(
            object=data.get("object", "list"),
            data=models,
        )
    
    def _parse_image_response(self, data: Dict[str, Any]) -> ImageResponse:
        """解析图像生成响应。"""
        images = []
        for img_data in data.get("data", []):
            images.append(ImageData(
                url=img_data.get("url"),
                b64_json=img_data.get("b64_json"),
                revised_prompt=img_data.get("revised_prompt"),
            ))
        
        return ImageResponse(
            created=data.get("created", 0),
            data=images,
        )


__all__ = [
    "Message",
    "ChatRequest",
    "ChatChoice",
    "ChatResponse",
    "StreamChunk",
    "ModelInfo",
    "ModelsResponse",
    "ImageRequest",
    "ImageData",
    "ImageResponse",
    "AIClientError",
    "UpstreamError",
    "NetworkError",
    "TimeoutError",
    "RateLimitedError",
    "AIClient",
]
