"""
AI 代理 API 路由

提供 AI 服务代理功能，支持聊天、模型列表、图像生成。
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.ai_client import (
    AIClient,
    ChatRequest,
    ImageRequest,
    Message,
    AIClientError,
    UpstreamError,
    NetworkError,
    TimeoutError as AITimeoutError,
    RateLimitedError as AIRateLimitedError,
)
from app.core.security import (
    URLBlockedError,
    PrivateIPError,
    redact_sensitive_data,
)
from app.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proxy", tags=["AI Proxy"])


class MessageModel(BaseModel):
    """聊天消息模型"""
    role: str = Field(..., description="消息角色: system, user, assistant")
    content: str = Field(..., description="消息内容")
    name: Optional[str] = Field(default=None, description="发送者名称")


class ChatRequestModel(BaseModel):
    """聊天请求模型"""
    base_url: str = Field(..., description="AI 服务 Base URL")
    api_key: str = Field(..., description="API Key")
    model: str = Field(..., description="模型名称")
    messages: List[MessageModel] = Field(..., description="消息列表")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(default=None, gt=0, description="最大生成 token 数")
    stream: bool = Field(default=True, description="是否流式响应")
    top_p: Optional[float] = Field(default=None, ge=0, le=1, description="Top-P 采样")
    frequency_penalty: Optional[float] = Field(default=None, ge=-2, le=2, description="频率惩罚")
    presence_penalty: Optional[float] = Field(default=None, ge=-2, le=2, description="存在惩罚")
    stop: Optional[List[str]] = Field(default=None, description="停止词列表")


class ModelsRequestModel(BaseModel):
    """模型列表请求模型"""
    base_url: str = Field(..., description="AI 服务 Base URL")
    api_key: str = Field(..., description="API Key")


class ModelInfoModel(BaseModel):
    """模型信息"""
    id: str = Field(..., description="模型 ID")
    object: str = Field(default="model", description="对象类型")
    created: Optional[int] = Field(default=None, description="创建时间")
    owned_by: Optional[str] = Field(default=None, description="所有者")


class ModelsResponseModel(BaseModel):
    """模型列表响应"""
    object: str = Field(default="list", description="对象类型")
    data: List[ModelInfoModel] = Field(default_factory=list, description="模型列表")


class ImageRequestModel(BaseModel):
    """图像生成请求模型"""
    base_url: str = Field(..., description="AI 服务 Base URL")
    api_key: str = Field(..., description="API Key")
    prompt: str = Field(..., description="图像描述提示词")
    model: str = Field(default="dall-e-3", description="模型名称")
    n: int = Field(default=1, ge=1, le=10, description="生成数量")
    size: str = Field(default="1024x1024", description="图像尺寸")
    quality: str = Field(default="standard", description="图像质量")
    response_format: str = Field(default="url", description="响应格式: url 或 b64_json")
    style: str = Field(default="vivid", description="风格: vivid 或 natural")


class ImageDataModel(BaseModel):
    """图像数据"""
    url: Optional[str] = Field(default=None, description="图像 URL")
    b64_json: Optional[str] = Field(default=None, description="Base64 编码图像")
    revised_prompt: Optional[str] = Field(default=None, description="修改后的提示词")


class ImageResponseModel(BaseModel):
    """图像生成响应"""
    created: int = Field(..., description="创建时间戳")
    data: List[ImageDataModel] = Field(..., description="图像数据列表")


class SSEError(BaseModel):
    """SSE 错误帧"""
    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误信息")


def _log_request(endpoint: str, base_url: str) -> None:
    """记录请求日志（脱敏）。"""
    settings = get_settings()
    if settings.log_redact:
        base_url = redact_sensitive_data(base_url)
    logger.info(f"Proxy request: {endpoint} -> {base_url}")


def _handle_security_error(e: Exception) -> HTTPException:
    """处理安全错误。"""
    if isinstance(e, URLBlockedError):
        logger.warning(f"URL blocked: {redact_sensitive_data(e.url)}")
        return HTTPException(
            status_code=403,
            detail=f"URL not allowed: {e.message}",
        )
    elif isinstance(e, PrivateIPError):
        logger.warning(f"Private IP blocked: {e.ip}")
        return HTTPException(
            status_code=403,
            detail="Access to private/internal networks is not allowed",
        )
    return HTTPException(status_code=500, detail="Security error")


def _handle_ai_error(e: AIClientError) -> Dict[str, Any]:
    """处理 AI 客户端错误，返回 SSE 错误帧数据。"""
    return {
        "code": e.code,
        "message": redact_sensitive_data(e.message),
    }


async def _generate_chat_stream(client: AIClient, request: ChatRequest):
    """生成 SSE 聊天流。"""
    try:
        async for chunk in client.chat_stream(request):
            choices_data = []
            for choice in chunk.choices:
                choice_dict = {
                    "index": choice.index,
                    "delta": choice.delta or {},
                }
                if choice.finish_reason:
                    choice_dict["finish_reason"] = choice.finish_reason
                choices_data.append(choice_dict)
            
            data = {
                "id": chunk.id,
                "object": chunk.object,
                "created": chunk.created,
                "model": chunk.model,
                "choices": choices_data,
            }
            yield f"data: {json.dumps(data)}\n\n"
        
        yield "data: [DONE]\n\n"
        
    except AIRateLimitedError as e:
        error_data = _handle_ai_error(e)
        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
    except AITimeoutError as e:
        error_data = _handle_ai_error(e)
        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
    except NetworkError as e:
        error_data = _handle_ai_error(e)
        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
    except UpstreamError as e:
        error_data = _handle_ai_error(e)
        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
    except Exception as e:
        logger.exception("Unexpected error in chat stream")
        error_data = {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
        }
        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"


@router.post("/chat", summary="AI 聊天代理")
async def proxy_chat(request: ChatRequestModel):
    """
    AI 聊天代理接口。
    
    支持流式 (SSE) 和非流式响应：
    - stream=true: 返回 text/event-stream，使用 SSE 协议
    - stream=false: 返回 JSON 响应
    
    **SSE 事件格式：**
    - 正常数据: `data: {"choices": [{"delta": {"content": "Hello"}}]}`
    - 结束标记: `data: [DONE]`
    - 错误事件: `event: error` + `data: {"code": "...", "message": "..."}`
    
    **错误码：**
    - UPSTREAM_ERROR: 上游 AI 服务返回错误
    - NETWORK_ERROR: 网络连接问题
    - TIMEOUT: 请求超时
    - RATE_LIMITED: 请求频率超限
    """
    _log_request("/chat", request.base_url)
    
    try:
        client = AIClient(
            base_url=request.base_url,
            api_key=request.api_key,
        )
    except (URLBlockedError, PrivateIPError) as e:
        raise _handle_security_error(e)
    
    messages = [
        Message(role=m.role, content=m.content, name=m.name)
        for m in request.messages
    ]
    
    chat_request = ChatRequest(
        messages=messages,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        stream=request.stream,
        top_p=request.top_p,
        frequency_penalty=request.frequency_penalty,
        presence_penalty=request.presence_penalty,
        stop=request.stop,
    )
    
    if request.stream:
        return StreamingResponse(
            _generate_chat_stream(client, chat_request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        try:
            response = await client.chat(chat_request)
            
            choices_data = []
            for choice in response.choices:
                choice_dict = {
                    "index": choice.index,
                    "message": {
                        "role": choice.message.role if choice.message else "assistant",
                        "content": choice.message.content if choice.message else "",
                    },
                }
                if choice.finish_reason:
                    choice_dict["finish_reason"] = choice.finish_reason
                choices_data.append(choice_dict)
            
            return {
                "id": response.id,
                "object": response.object,
                "created": response.created,
                "model": response.model,
                "choices": choices_data,
                "usage": response.usage,
            }
            
        except AIRateLimitedError:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        except AITimeoutError:
            raise HTTPException(status_code=504, detail="Request timed out")
        except NetworkError as e:
            raise HTTPException(status_code=502, detail=str(e))
        except UpstreamError as e:
            raise HTTPException(
                status_code=e.status_code or 502,
                detail=redact_sensitive_data(e.message),
            )


@router.post("/models", response_model=ModelsResponseModel, summary="获取模型列表")
async def proxy_models(request: ModelsRequestModel) -> ModelsResponseModel:
    """
    获取 AI 服务的可用模型列表。
    
    返回模型 ID、创建时间、所有者等信息。
    """
    _log_request("/models", request.base_url)
    
    try:
        client = AIClient(
            base_url=request.base_url,
            api_key=request.api_key,
        )
    except (URLBlockedError, PrivateIPError) as e:
        raise _handle_security_error(e)
    
    try:
        response = await client.list_models()
        
        return ModelsResponseModel(
            object=response.object,
            data=[
                ModelInfoModel(
                    id=model.id,
                    object=model.object,
                    created=model.created,
                    owned_by=model.owned_by,
                )
                for model in response.data
            ],
        )
        
    except AIRateLimitedError:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    except AITimeoutError:
        raise HTTPException(status_code=504, detail="Request timed out")
    except NetworkError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except UpstreamError as e:
        raise HTTPException(
            status_code=e.status_code or 502,
            detail=redact_sensitive_data(e.message),
        )


@router.post("/image", response_model=ImageResponseModel, summary="图像生成代理")
async def proxy_image(request: ImageRequestModel) -> ImageResponseModel:
    """
    AI 图像生成代理接口。
    
    支持 DALL-E 等图像生成模型。
    """
    _log_request("/image", request.base_url)
    
    try:
        client = AIClient(
            base_url=request.base_url,
            api_key=request.api_key,
        )
    except (URLBlockedError, PrivateIPError) as e:
        raise _handle_security_error(e)
    
    image_request = ImageRequest(
        prompt=request.prompt,
        model=request.model,
        n=request.n,
        size=request.size,
        quality=request.quality,
        response_format=request.response_format,
        style=request.style,
    )
    
    try:
        response = await client.generate_image(image_request)
        
        return ImageResponseModel(
            created=response.created,
            data=[
                ImageDataModel(
                    url=img.url,
                    b64_json=img.b64_json,
                    revised_prompt=img.revised_prompt,
                )
                for img in response.data
            ],
        )
        
    except AIRateLimitedError:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    except AITimeoutError:
        raise HTTPException(status_code=504, detail="Request timed out")
    except NetworkError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except UpstreamError as e:
        raise HTTPException(
            status_code=e.status_code or 502,
            detail=redact_sensitive_data(e.message),
        )
