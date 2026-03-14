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
from core.wx.article import parse_wechat_article, get_mp_info_by_article
from core.wx.mp import get_mp_list, get_mp_articles, search_biz
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
        is_logged_in = result.get('is_logged_in', False)
        # 返回增强后的状态格式 (修复返回格式)
        return success_response({
            "is_logged_in": is_logged_in,
            "status": result.get('status', 0),
            "status_msg": result.get('status_msg', ''),
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
    status: Optional[int] = None,
    sort: str = Query("created_desc", description="排序: created_desc, created_asc, articles_desc, articles_asc, name_asc, name_desc")
):
    """获取公众号列表"""
    from core.models import Article
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

        # 排序处理
        if sort == "created_asc":
            query = query.order_by(Feed.created_at.asc())
        elif sort == "name_asc":
            query = query.order_by(Feed.mp_name.asc())
        elif sort == "name_desc":
            query = query.order_by(Feed.mp_name.desc())
        # created_desc 是默认的

        # 分页
        mps = query.offset(offset).limit(limit).all()

        # 获取每个公众号的文章数量
        mp_list = []
        for mp in mps:
            mp_dict = mp.to_dict()
            # 统计文章数量
            article_count = session.query(Article).filter(
                Article.mp_id == mp.id,
                Article.status == 1
            ).count()
            mp_dict['article_count'] = article_count
            mp_list.append(mp_dict)

        # 如果需要按文章数量排序（在内存中排序）
        if sort == "articles_desc":
            mp_list.sort(key=lambda x: x.get('article_count', 0), reverse=True)
        elif sort == "articles_asc":
            mp_list.sort(key=lambda x: x.get('article_count', 0))

        return success_response({
            "total": total,
            "list": mp_list
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

        # 添加成功后尝试同步文章
        sync_result = None
        if session_info.get('is_logged_in') and request.faker_id:
            try:
                from core.wx.mp import get_mp_articles as fetch_mp_articles
                from core.models import Article

                articles = fetch_mp_articles(request.faker_id, max_count=5)
                saved_count = 0

                for art in articles:
                    # 检查文章是否已存在
                    existing_art = session.query(Article).filter(
                        Article.mp_id == mp_id,
                        Article.title == art.get('title', '')
                    ).first()

                    if not existing_art:
                        publish_time = art.get('update_time', 0)
                        if isinstance(publish_time, str):
                            try:
                                publish_time = int(publish_time)
                            except:
                                publish_time = 0

                        new_article = Article(
                            id=art.get('id', f"art_{int(time.time())}_{saved_count}"),
                            mp_id=mp_id,
                            title=art.get('title', '无标题'),
                            author=art.get('author', ''),
                            content=art.get('content', ''),
                            digest=art.get('digest', ''),
                            publish_time=publish_time,
                            pic_url=art.get('cover', ''),
                            url=art.get('link', ''),
                            is_export=0
                        )
                        session.add(new_article)
                        saved_count += 1

                session.commit()
                sync_result = {"saved_count": saved_count, "total": len(articles)}
            except Exception as sync_e:
                print(f"首次同步文章失败: {sync_e}")

        result = mp.to_dict()
        if sync_result:
            result['sync_result'] = sync_result

        return success_response(result, "添加公众号成功")
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
        # 获取当前活跃 session 的 cookies
        auth = get_wechat_auth()
        session_info = auth.get_session_info()
        active_cookies = session_info.get('cookies_str', '') or cfg.get("wechat.cookies", "")

        # 使用新增强的 get_mp_info_by_article 函数
        mp_info = get_mp_info_by_article(url, active_cookies)

        if not mp_info or not mp_info.get("mp_name"):
            # 如果失败，尝试使用旧的解析器
            mp_info = parse_wechat_article(url, active_cookies)

        if not mp_info:
            return error_response(40401, "无法解析文章链接，请确保链接正确")

        # 返回公众号信息
        return success_response({
            "mp_name": mp_info.get("mp_name", ""),
            "mp_cover": mp_info.get("mp_cover", ""),
            "mp_intro": mp_info.get("mp_intro", ""),
            "mp_id": mp_info.get("mp_id", ""),
            "biz": mp_info.get("biz", ""),
            "article_url": mp_info.get("article_url", ""),
            "article_id": mp_info.get("article_id", "")
        })

    except Exception as e:
        return error_response(50006, f"获取公众号信息失败: {str(e)}")


@router.get("/search/{kw}", summary="搜索公众号")
async def search_mp(
    kw: str,
    limit: int = Query(5, ge=1, le=20),
    offset: int = Query(0, ge=0)
):
    """搜索公众号 - 复刻原项目 search_Biz 功能"""
    try:
        result = search_biz(kw, limit, offset)

        if result.get("error"):
            return error_response(50007, result.get("error"))

        return success_response({
            "list": result.get("list", []),
            "total": result.get("total", 0),
            "page": {
                "limit": limit,
                "offset": offset
            }
        })

    except Exception as e:
        return error_response(50007, f"搜索公众号失败: {str(e)}")


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

        # 检查授权状态
        auth = get_wechat_auth()
        session_info = auth.get_session_info()

        if not session_info.get('is_logged_in'):
            return error_response(50008, "请先扫码授权登录")

        # 获取 faker_id 用于调用微信 API
        faker_id = mp.faker_id
        if not faker_id:
            # 尝试从 mp_id 中提取
            if mp_id.startswith("MP_WXS_"):
                faker_id = mp_id.replace("MP_WXS_", "")

        if not faker_id:
            return error_response(50009, "无法获取公众号ID")

        # 调用获取文章列表
        from core.wx.mp import get_mp_articles as fetch_mp_articles
        articles = fetch_mp_articles(faker_id, max_count=10)

        # 保存文章到数据库
        from core.models import Article
        saved_count = 0
        for art in articles:
            # 检查文章是否已存在
            existing = session.query(Article).filter(
                Article.mp_id == mp_id,
                Article.title == art.get('title', '')
            ).first()

            if not existing:
                # 解析文章发布时间
                publish_time = art.get('update_time', 0)
                if isinstance(publish_time, str):
                    try:
                        publish_time = int(publish_time)
                    except:
                        publish_time = 0

                new_article = Article(
                    id=art.get('id', f"art_{int(time.time())}_{saved_count}"),
                    mp_id=mp_id,
                    title=art.get('title', '无标题'),
                    author=art.get('author', ''),
                    content=art.get('content', ''),
                    digest=art.get('digest', ''),
                    publish_time=publish_time,
                    pic_url=art.get('cover', ''),
                    url=art.get('link', ''),
                    is_export=0
                )
                session.add(new_article)
                saved_count += 1

        session.commit()

        # 更新同步时间
        mp.sync_time = int(time.time())
        session.commit()

        return success_response({
            "message": "同步成功",
            "saved_count": saved_count,
            "total_articles": len(articles)
        })
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        return error_response(50007, f"同步失败: {str(e)}")


# ========== 定时任务管理 API ==========

from pydantic import BaseModel


class CronJobRequest(BaseModel):
    """定时任务请求"""
    cron_expr: str  # Cron 表达式
    mp_ids: list = None  # 公众号ID列表，为空则同步所有


@router.post("/cron/start", summary="启动定时同步任务")
async def start_cron_job(request: CronJobRequest):
    """启动定时同步任务"""
    try:
        from jobs.mps import start_cron_job
        from core.models import Feed

        # 获取要同步的公众号
        session = DB.get_session()
        try:
            if request.mp_ids:
                feeds = session.query(Feed).filter(
                    Feed.id.in_(request.mp_ids),
                    Feed.status == 1
                ).all()
            else:
                feeds = session.query(Feed).filter(Feed.status == 1).all()

            if not feeds:
                return error_response(50010, "没有可同步的公众号")

            # 启动定时任务
            start_cron_job(request.cron_expr, feeds)

            return success_response({
                "message": "定时任务已启动",
                "cron_expr": request.cron_expr,
                "feed_count": len(feeds)
            })
        finally:
            session.close()

    except Exception as e:
        return error_response(50010, f"启动定时任务失败: {str(e)}")


@router.get("/cron/stop", summary="停止定时同步任务")
async def stop_cron_job():
    """停止所有定时同步任务"""
    try:
        from jobs import scheduler

        scheduler.stop()

        return success_response({"message": "定时任务已停止"})
    except Exception as e:
        return error_response(50011, f"停止定时任务失败: {str(e)}")


@router.get("/cron/status", summary="获取定时任务状态")
async def get_cron_status():
    """获取定时任务状态"""
    try:
        from jobs import scheduler

        return success_response({
            "running": scheduler.running,
            "jobs": scheduler.get_jobs()
        })
    except Exception as e:
        return error_response(50012, f"获取任务状态失败: {str(e)}")


@router.post("/cron/run-all", summary="立即同步所有公众号")
async def run_all_now():
    """立即同步所有公众号"""
    try:
        from jobs.mps import fetch_all_articles
        import threading

        # 在后台线程中执行
        thread = threading.Thread(target=fetch_all_articles, daemon=True)
        thread.start()

        return success_response({"message": "同步任务已启动"})
    except Exception as e:
        return error_response(50013, f"启动同步失败: {str(e)}")
