"""文章管理 API"""
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.db import DB
from core.models import Article, Feed
from apis.base import success_response, error_response

router = APIRouter(prefix="/wx/articles", tags=["文章管理"])


class UpdateArticleRequest(BaseModel):
    """更新文章请求"""
    ai_category: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_tags: Optional[str] = None
    is_read: Optional[int] = None


@router.get("", summary="获取文章列表")
async def get_articles(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    mp_id: Optional[str] = None,
    kw: str = Query(""),
    category: Optional[str] = None,
    tag: Optional[str] = None,
    is_read: Optional[int] = None
):
    """获取文章列表"""
    session = DB.get_session()
    try:
        query = session.query(Article).filter(Article.status == 1)

        # 公众号过滤
        if mp_id:
            query = query.filter(Article.mp_id == mp_id)

        # 关键词搜索
        if kw:
            query = query.filter(Article.title.ilike(f"%{kw}%"))

        # 分类过滤
        if category:
            query = query.filter(Article.ai_category == category)

        # 标签过滤
        if tag:
            query = query.filter(Article.ai_tags.ilike(f"%{tag}%"))

        # 已读过滤
        if is_read is not None:
            query = query.filter(Article.is_read == is_read)

        # 总数
        total = query.count()

        # 分页
        articles = query.order_by(Article.publish_time.desc()).offset(offset).limit(limit).all()

        # 补充公众号名称
        result = []
        for art in articles:
            art_dict = art.to_dict()
            mp = session.query(Feed).filter(Feed.id == art.mp_id).first()
            art_dict["mp_name"] = mp.mp_name if mp else ""
            result.append(art_dict)

        return success_response({
            "total": total,
            "list": result
        })
    except Exception as e:
        return error_response(50001, f"获取文章列表失败: {str(e)}")


@router.get("/{article_id}", summary="获取文章详情")
async def get_article(article_id: str):
    """获取文章详情"""
    session = DB.get_session()
    try:
        article = session.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise HTTPException(status_code=404, detail="文章不存在")

        result = article.to_dict()

        # 补充公众号信息
        mp = session.query(Feed).filter(Feed.id == article.mp_id).first()
        if mp:
            result["mp_name"] = mp.mp_name

        return success_response(result)
    except HTTPException:
        raise
    except Exception as e:
        return error_response(50002, f"获取文章详情失败: {str(e)}")


@router.put("/{article_id}", summary="更新文章")
async def update_article(article_id: str, request: UpdateArticleRequest):
    """更新文章"""
    session = DB.get_session()
    try:
        article = session.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise HTTPException(status_code=404, detail="文章不存在")

        # 更新字段
        if request.ai_category is not None:
            article.ai_category = request.ai_category
        if request.ai_summary is not None:
            article.ai_summary = request.ai_summary
        if request.ai_tags is not None:
            article.ai_tags = request.ai_tags
        if request.is_read is not None:
            article.is_read = request.is_read

        article.updated_at = time.time()
        session.commit()

        return success_response(article.to_dict(), "更新成功")
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        return error_response(50003, f"更新文章失败: {str(e)}")


@router.delete("/{article_id}", summary="删除文章")
async def delete_article(article_id: str):
    """删除文章"""
    session = DB.get_session()
    try:
        article = session.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise HTTPException(status_code=404, detail="文章不存在")

        # 软删除
        article.status = 0
        session.commit()

        return success_response(message="删除成功")
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        return error_response(50004, f"删除文章失败: {str(e)}")


@router.post("/{article_id}/read", summary="标记已读")
async def mark_read(article_id: str):
    """标记文章为已读"""
    session = DB.get_session()
    try:
        article = session.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise HTTPException(status_code=404, detail="文章不存在")

        article.is_read = 1
        session.commit()

        return success_response(message="标记成功")
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        return error_response(50005, f"标记失败: {str(e)}")


@router.get("/categories/all", summary="获取所有分类")
async def get_categories():
    """获取所有文章分类"""
    session = DB.get_session()
    try:
        # 获取所有不重复的分类
        categories = session.query(Article.ai_category).distinct().filter(
            Article.ai_category.isnot(None),
            Article.ai_category != ""
        ).all()

        return success_response([c[0] for c in categories if c[0]])
    except Exception as e:
        return error_response(50006, f"获取分类失败: {str(e)}")


@router.get("/tags/all", summary="获取所有标签")
async def get_tags():
    """获取所有文章标签"""
    session = DB.get_session()
    try:
        # 获取所有标签
        articles = session.query(Article.ai_tags).filter(
            Article.ai_tags.isnot(None),
            Article.ai_tags != ""
        ).all()

        # 解析标签
        all_tags = set()
        import json
        for art in articles:
            if art[0]:
                try:
                    tags = json.loads(art[0])
                    if isinstance(tags, list):
                        all_tags.update(tags)
                except:
                    pass

        return success_response(list(all_tags))
    except Exception as e:
        return error_response(50007, f"获取标签失败: {str(e)}")
