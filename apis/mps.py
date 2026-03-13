"""公众号管理 API"""
import time
import uuid
import base64
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel

from core.db import DB
from core.models import Feed
from core.wx.auth import generate_qr_code, check_login_status, get_wechat_auth
from core.wx.article import parse_wechat_article
from core.wx.mp import get_mp_list, get_mp_articles
from core.config import cfg
from apis.base import success_response, error_response

router = APIRouter(prefix="/wx/mps", tags=["公众号管理"])


class AddMPRequest(BaseModel):
    """添加公众号请求"""
    faker_id: str  # 微信 Faker ID
    mp_name: Optional[str] = None
    mp_cover: Optional[str] = None
    mp_intro: Optional[str] = None


class ScanQRCodeRequest(BaseModel):
    """扫码请求"""
    ticket: str


@router.get("/scan-status", summary="检查扫码状态")
async def scan_status():
    """检查扫码登录状态"""
    try:
        result = check_login_status()
        return success_response({
            "is_logged_in": result.get('is_logged_in', False),
            "has_token": bool(result.get('token')),
            "token": result.get('token', '')[:20] + '...' if result.get('token') else ''
        })
    except Exception as e:
        return error_response(50006, f"检查状态失败: {str(e)}")


@router.get("/account-list", summary="获取微信账号列表")
async def get_account_list():
    """获取当前登录微信绑定的公众号列表"""
    try:
        mps = get_mp_list()
        return success_response({"list": mps})
    except Exception as e:
        return error_response(50007, f"获取账号列表失败: {str(e)}")


@router.get("", summary="获取公众号列表")
async def get_mps(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    kw: str = Query(""),
    status: Optional[int] = None
):
    """获取公众号列表"""
    session = DB.get_session()
    try:
        query = session.query(Feed)

        # 关键词搜索
        if kw:
            query = query.filter(Feed.mp_name.ilike(f"%{kw}%"))

        # 状态过滤
        if status is not None:
            query = query.filter(Feed.status == status)

        # 总数
        total = query.count()

        # 分页
        mps = query.order_by(Feed.created_at.desc()).offset(offset).limit(limit).all()

        return success_response({
            "total": total,
            "list": [mp.to_dict() for mp in mps]
        })
    except Exception as e:
        return error_response(50001, f"获取公众号列表失败: {str(e)}")


@router.get("/{mp_id}", summary="获取公众号详情")
async def get_mp(mp_id: str):
    """获取公众号详情"""
    session = DB.get_session()
    try:
        mp = session.query(Feed).filter(Feed.id == mp_id).first()
        if not mp:
            raise HTTPException(status_code=404, detail="公众号不存在")

        return success_response(mp.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        return error_response(50002, f"获取公众号详情失败: {str(e)}")


@router.post("", summary="添加公众号")
async def add_mp(request: AddMPRequest):
    """添加公众号"""
    session = DB.get_session()
    try:
        # 检查是否已存在
        existing = session.query(Feed).filter(Feed.faker_id == request.faker_id).first()
        if existing:
            return error_response(40001, "公众号已存在")

        # 使用全局授权实例 (修复状态丢失)
        auth = get_wechat_auth()
        session_info = auth.get_session_info()

        # 公众号信息 (优先使用请求中的信息)
        mp_name = request.mp_name
        mp_cover = request.mp_cover
        mp_intro = request.mp_intro

        # 如果关键信息缺失且已登录，尝试从账号列表动态匹配 (修复 get_mp_info 缺失问题)
        if not mp_name and session_info.get('is_logged_in'):
            from core.wx.mp import get_mp_list
            mps = get_mp_list()
            for item in mps:
                if item.get('user_name') == request.faker_id:
                    mp_name = item.get('nickname')
                    mp_cover = item.get('headimgurl')
                    break

        # 生成 ID
        mp_id = f"MP_{request.faker_id[:8]}_{int(time.time())}"

        # 创建公众号
        mp = Feed(
            id=mp_id,
            mp_name=mp_name or "未知公众号",
            mp_cover=mp_cover or "",
            mp_intro=mp_intro or "",
            faker_id=request.faker_id,
            status=1,
            sync_time=int(time.time())
        )

        session.add(mp)
        session.commit()

        return success_response(mp.to_dict(), "添加公众号成功")
    except Exception as e:
        session.rollback()
        return error_response(50003, f"添加公众号失败: {str(e)}")


@router.delete("/{mp_id}", summary="删除公众号")
async def delete_mp(mp_id: str):
    """删除公众号"""
    session = DB.get_session()
    try:
        mp = session.query(Feed).filter(Feed.id == mp_id).first()
        if not mp:
            raise HTTPException(status_code=404, detail="公众号不存在")

        session.delete(mp)
        session.commit()

        return success_response(message="删除成功")
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        return error_response(50004, f"删除公众号失败: {str(e)}")


@router.post("/by-article", summary="通过文章链接获取公众号信息")
async def get_mp_by_article(url: str = Query(..., min_length=1)):
    """通过公众号文章链接获取公众号信息"""
    try:
        # 获取当前活跃 session 的 cookies (修复 API 调用错误/Cookies 过期)
        auth = get_wechat_auth()
        session_info = auth.get_session_info()
        active_cookies = session_info.get('cookies_str', '') or cfg.get("wechat.cookies", "")

        # 解析文章链接
        mp_info = parse_wechat_article(url, active_cookies)

        if not mp_info:
            return error_response(40401, "无法解析文章链接，请确保链接正确")

        # 返回公众号信息
        return success_response({
            "mp_name": mp_info.get("mp_name", ""),
            "mp_cover": mp_info.get("mp_cover", ""),
            "mp_intro": mp_info.get("mp_intro", ""),
            "mp_id": mp_info.get("mp_id", ""),
            "article_url": mp_info.get("article_url", "")
        })

    except Exception as e:
        return error_response(50006, f"获取公众号信息失败: {str(e)}")


@router.post("/scan-qrcode", summary="生成扫码二维码")
async def scan_qrcode():
    """生成扫码二维码，用户微信扫码登录"""
    try:
        result = generate_qr_code()
        if result.get('code'):
            return success_response({
                "qrcode": result['code'],
                "uuid": result.get('uuid', ''),
                "message": result.get('msg', '请扫码')
            })
        return error_response(50005, result.get('msg', '生成二维码失败'))
    except Exception as e:
        return error_response(50005, f"生成二维码失败: {str(e)}")


@router.get("/{fakeid}/articles", summary="获取公众号文章列表")
async def get_mp_articles_api(fakeid: str, limit: int = Query(10, ge=1, le=50)):
    """获取指定公众号的文章列表"""
    try:
        articles = get_mp_articles(fakeid, limit)
        return success_response({"list": articles})
    except Exception as e:
        return error_response(50008, f"获取文章失败: {str(e)}")


@router.post("/{mp_id}/sync", summary="同步公众号文章")
async def sync_articles(mp_id: str):
    """同步公众号文章"""
    session = DB.get_session()
    try:
        mp = session.query(Feed).filter(Feed.id == mp_id).first()
        if not mp:
            raise HTTPException(status_code=404, detail="公众号不存在")

        # TODO: 调用文章抓取逻辑

        # 更新同步时间
        mp.sync_time = int(time.time())
        session.commit()

        return success_response(message="同步成功")
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        return error_response(50007, f"同步失败: {str(e)}")
