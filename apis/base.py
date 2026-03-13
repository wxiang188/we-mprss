"""API 基础响应模块"""
from typing import Any, Optional
from fastapi import HTTPException


def success_response(data: Any = None, message: str = "success") -> dict:
    """成功响应"""
    return {
        "code": 0,
        "message": message,
        "data": data
    }


def error_response(code: int = 40000, message: str = "error", data: Any = None) -> dict:
    """错误响应"""
    return {
        "code": code,
        "message": message,
        "data": data
    }


def raise_http_error(code: int, message: str):
    """抛出 HTTP 错误"""
    raise HTTPException(status_code=code, detail=error_response(code, message))
