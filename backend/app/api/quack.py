"""Quack import and preview API endpoints.

POST /api/quack/import - Import character from Quack API or JSON
POST /api/quack/preview - Preview character info (optional)
"""

import io
import json
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..core import (
    ApiResponse,
    CharacterCardV3,
    CookieParser,
    ErrorCode,
    Lorebook,
    QuackClient,
    export_to_png,
    extract_quack_id,
    map_quack_lorebook_only,
    map_quack_to_v3,
)
from ..core.exceptions import (
    NetworkError,
    RateLimitedError,
    TimeoutError,
    UnauthorizedError,
)
from ..settings import get_settings

router = APIRouter(prefix="/quack", tags=["quack"])


# ============================================================
# Request/Response Models
# ============================================================


class QuackImportRequest(BaseModel):
    """Quack 导入请求"""

    quack_input: str = Field(
        ..., description="Quack ID/URL 或 手动粘贴的 JSON 数据"
    )
    cookies: Optional[str] = Field(
        default=None, description="Cookie 字符串 (支持 Netscape/JSON/Header String 格式)"
    )
    mode: Literal["full", "only_lorebook"] = Field(
        default="full", description="导入模式: full=完整卡片, only_lorebook=仅世界书"
    )
    output_format: Literal["json", "png"] = Field(
        default="json", description="输出格式: json=JSON数据, png=Base64 PNG"
    )


class QuackPreviewRequest(BaseModel):
    """Quack 预览请求"""

    quack_input: str = Field(..., description="Quack ID/URL 或 手动粘贴的 JSON 数据")
    cookies: Optional[str] = Field(default=None, description="Cookie 字符串")


class QuackImportResult(BaseModel):
    """Quack 导入结果"""

    card: Optional[CharacterCardV3] = Field(default=None, description="导入的角色卡")
    lorebook: Optional[Lorebook] = Field(default=None, description="导入的世界书 (only_lorebook 模式)")
    png_base64: Optional[str] = Field(default=None, description="Base64 编码的 PNG (output_format=png)")
    source: Literal["api", "json"] = Field(..., description="数据来源")
    warnings: list[str] = Field(default_factory=list, description="警告信息")


class QuackPreviewResult(BaseModel):
    """Quack 预览结果"""

    name: str = Field(..., description="角色名称")
    creator: str = Field(default="", description="创作者")
    intro: str = Field(default="", description="简介")
    tags: list[str] = Field(default_factory=list, description="标签")
    attr_count: int = Field(default=0, description="属性数量")
    lorebook_count: int = Field(default=0, description="世界书条目数")
    source: Literal["api", "json"] = Field(..., description="数据来源")


# ============================================================
# Helper Functions
# ============================================================


def _try_parse_json(input_str: str) -> Optional[dict]:
    """尝试解析输入为 JSON (仅接受对象类型)"""
    input_str = input_str.strip()
    if not input_str.startswith("{"):
        return None
    try:
        result = json.loads(input_str)
        # 确保是 dict 类型
        if not isinstance(result, dict):
            return None
        return result
    except json.JSONDecodeError:
        return None


def _generate_placeholder_png() -> bytes:
    """生成占位符 PNG 图片 (1x1 透明像素)"""
    from PIL import Image
    
    img = Image.new("RGBA", (512, 512), (128, 128, 128, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def _extract_preview_from_quack(data: dict) -> QuackPreviewResult:
    """从 Quack 数据提取预览信息"""
    char_list = data.get("charList", [])
    char = char_list[0] if char_list else {}
    
    name = char.get("name", data.get("name", "Unknown"))
    creator = data.get("authorName", data.get("author", ""))
    intro = data.get("intro", char.get("intro", ""))[:200]  # 截断
    
    tags = data.get("tags", [])
    if not tags:
        image_tags = char.get("generateImage", {}).get("allTags", [])
        tags = [t.get("label", t.get("value", "")) for t in image_tags if isinstance(t, dict)]
    
    attrs = char.get("attrs", []) + char.get("adviseAttrs", []) + char.get("customAttrs", [])
    
    lorebook_count = 0
    books = data.get("characterbooks", [])
    for book in books if isinstance(books, list) else []:
        if isinstance(book, dict):
            lorebook_count += len(book.get("entryList", []))
    
    return QuackPreviewResult(
        name=name,
        creator=creator,
        intro=intro,
        tags=[str(t) for t in tags if t][:10],  # 最多 10 个标签
        attr_count=len(attrs),
        lorebook_count=lorebook_count,
        source="json",
    )


# ============================================================
# API Endpoints
# ============================================================


@router.post(
    "/import",
    response_model=ApiResponse[QuackImportResult],
    summary="从 Quack 导入角色卡",
    description="支持两种模式: 1) 通过 ID/URL + Cookie 从 Quack API 获取; 2) 手动粘贴 JSON 数据",
)
async def import_from_quack(
    request: QuackImportRequest,
) -> ApiResponse[QuackImportResult]:
    """导入 Quack 角色数据"""
    import base64
    
    warnings: list[str] = []
    source: Literal["api", "json"] = "api"
    quack_data: Optional[dict] = None
    lorebook_entries: list[dict] = []
    
    # 尝试解析为 JSON (手动粘贴模式)
    json_data = _try_parse_json(request.quack_input)
    
    if json_data:
        # 手动粘贴 JSON 模式
        source = "json"
        quack_data = json_data
        warnings.append("使用手动粘贴的 JSON 数据")
        
        # 尝试从 JSON 中提取世界书
        books = json_data.get("characterbooks", [])
        for book in books if isinstance(books, list) else []:
            if isinstance(book, dict) and "entryList" in book:
                lorebook_entries.extend(book.get("entryList", []))
    else:
        # API 获取模式
        quack_id = extract_quack_id(request.quack_input)
        if not quack_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "无效的 Quack ID 或 URL",
                    "error_code": ErrorCode.VALIDATION_ERROR,
                },
            )
        
        # 解析 Cookie
        cookies = {}
        if request.cookies:
            cookies = CookieParser.parse(request.cookies)
            if not cookies:
                warnings.append("Cookie 解析失败，将尝试无认证请求")
        
        # 从 API 获取数据
        client = QuackClient(cookies=cookies)
        
        try:
            quack_data, lorebook_entries = await client.fetch_character_complete(quack_id)
        except UnauthorizedError as e:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": str(e),
                    "error_code": ErrorCode.UNAUTHORIZED,
                    "hint": "请检查 Cookie 是否有效",
                },
            )
        except RateLimitedError as e:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": str(e),
                    "error_code": ErrorCode.RATE_LIMITED,
                },
            )
        except TimeoutError as e:
            raise HTTPException(
                status_code=504,
                detail={
                    "error": str(e),
                    "error_code": ErrorCode.TIMEOUT,
                },
            )
        except NetworkError as e:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": str(e),
                    "error_code": ErrorCode.NETWORK_ERROR,
                    "hint": "如果 IP 被封禁，请使用手动粘贴 JSON 模式",
                },
            )
    
    if not quack_data:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "无法获取 Quack 数据",
                "error_code": ErrorCode.PARSE_ERROR,
            },
        )
    
    # only_lorebook 模式
    if request.mode == "only_lorebook":
        if not lorebook_entries:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "该角色没有世界书数据",
                    "error_code": ErrorCode.PARSE_ERROR,
                },
            )
        
        lorebook = map_quack_lorebook_only(lorebook_entries)
        return ApiResponse(
            success=True,
            data=QuackImportResult(
                lorebook=lorebook,
                source=source,
                warnings=warnings,
            ),
        )
    
    # 完整卡片模式
    card = map_quack_to_v3(quack_data, lorebook_entries)
    
    # PNG 输出
    if request.output_format == "png":
        placeholder_png = _generate_placeholder_png()
        result_png = export_to_png(placeholder_png, card, include_v2_compat=True)
        png_base64 = base64.b64encode(result_png).decode("utf-8")
        warnings.append("使用占位符图片生成 PNG，请在前端替换为实际图片")
        
        return ApiResponse(
            success=True,
            data=QuackImportResult(
                card=card,
                png_base64=png_base64,
                source=source,
                warnings=warnings,
            ),
        )
    
    # JSON 输出
    return ApiResponse(
        success=True,
        data=QuackImportResult(
            card=card,
            source=source,
            warnings=warnings,
        ),
    )


@router.post(
    "/preview",
    response_model=ApiResponse[QuackPreviewResult],
    summary="预览 Quack 角色信息",
    description="获取角色摘要信息，用于确认后再导入",
)
async def preview_quack(
    request: QuackPreviewRequest,
) -> ApiResponse[QuackPreviewResult]:
    """预览 Quack 角色信息"""
    
    # 尝试解析为 JSON
    json_data = _try_parse_json(request.quack_input)
    
    if json_data:
        # 手动粘贴 JSON 模式
        result = _extract_preview_from_quack(json_data)
        result.source = "json"
        return ApiResponse(success=True, data=result)
    
    # API 获取模式
    quack_id = extract_quack_id(request.quack_input)
    if not quack_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "无效的 Quack ID 或 URL",
                "error_code": ErrorCode.VALIDATION_ERROR,
            },
        )
    
    # 解析 Cookie
    cookies = {}
    if request.cookies:
        cookies = CookieParser.parse(request.cookies)
    
    # 从 API 获取数据
    client = QuackClient(cookies=cookies)
    
    try:
        quack_data = await client.fetch_character_info(quack_id)
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=401,
            detail={
                "error": str(e),
                "error_code": ErrorCode.UNAUTHORIZED,
            },
        )
    except RateLimitedError as e:
        raise HTTPException(
            status_code=429,
            detail={
                "error": str(e),
                "error_code": ErrorCode.RATE_LIMITED,
            },
        )
    except TimeoutError as e:
        raise HTTPException(
            status_code=504,
            detail={
                "error": str(e),
                "error_code": ErrorCode.TIMEOUT,
            },
        )
    except NetworkError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "error": str(e),
                "error_code": ErrorCode.NETWORK_ERROR,
            },
        )
    
    result = _extract_preview_from_quack(quack_data)
    result.source = "api"
    
    # 获取世界书数量
    try:
        lorebook = await client.fetch_lorebook(quack_id)
        result.lorebook_count = len(lorebook)
    except Exception:
        pass
    
    return ApiResponse(success=True, data=result)


__all__ = [
    "router",
    "QuackImportRequest",
    "QuackPreviewRequest",
    "QuackImportResult",
    "QuackPreviewResult",
]
