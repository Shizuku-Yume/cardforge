"""
异常处理器模块

提供 FastAPI 异常处理器，将自定义异常转换为统一的 API 响应格式。
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.api_models import ApiResponse
from app.core.exceptions import CardForgeException


async def cardforge_exception_handler(
    request: Request, exc: CardForgeException
) -> JSONResponse:
    """统一异常响应处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(
            success=False,
            error=exc.message,
            error_code=exc.error_code,
        ).model_dump(),
    )
