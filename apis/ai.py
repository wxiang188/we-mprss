"""AI 处理 API"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from core.db import DB
from core.models import Article
from core.ai import ai_service
from apis.base import success_response, error_response

router = APIRouter(prefix="/wx/ai", tags=["AI 处理"])


class AISummaryRequest(BaseModel):
    """AI 总结请求"""
    article_ids: list[str]


class AICategoryRequest(BaseModel):
    """AI 分类请求"""
    article_ids: list[str]


class AITagsRequest(BaseModel):
    """AI 标签请求"""
    article_ids: list[str]


class AIAllRequest(BaseModel):
    """AI 全部处理请求"""
    article_ids: list[str]


@router.post("/summary", summary="AI 总结文章")
async def ai_summary(request: AISummaryRequest):
    """使用 AI 总结文章内容"""
    session = DB.get_session()
    results = []

    for article_id in request.article_ids:
        try:
            article = session.query(Article).filter(Article.id == article_id).first()
            if not article:
                results.append({"id": article_id, "status": "error", "message": "文章不存在"})
                continue

            # 调用 AI 总结
            summary = await ai_service.summarize(article.content or "", article.title or "")
            article.ai_summary = summary

            session.commit()
            results.append({"id": article_id, "status": "success", "summary": summary})

        except Exception as e:
            results.append({"id": article_id, "status": "error", "message": str(e)})

    return success_response({"results": results})


@router.post("/category", summary="AI 分类文章")
async def ai_category(request: AICategoryRequest):
    """使用 AI 对文章进行分类"""
    session = DB.get_session()
    results = []

    for article_id in request.article_ids:
        try:
            article = session.query(Article).filter(Article.id == article_id).first()
            if not article:
                results.append({"id": article_id, "status": "error", "message": "文章不存在"})
                continue

            # 调用 AI 分类
            category = await ai_service.categorize(article.content or "", article.title or "")
            article.ai_category = category

            session.commit()
            results.append({"id": article_id, "status": "success", "category": category})

        except Exception as e:
            results.append({"id": article_id, "status": "error", "message": str(e)})

    return success_response({"results": results})


@router.post("/tags", summary="AI 提取标签")
async def ai_tags(request: AITagsRequest):
    """使用 AI 提取文章标签"""
    session = DB.get_session()
    results = []

    for article_id in request.article_ids:
        try:
            article = session.query(Article).filter(Article.id == article_id).first()
            if not article:
                results.append({"id": article_id, "status": "error", "message": "文章不存在"})
                continue

            # 调用 AI 提取标签
            tags = await ai_service.extract_tags(article.content or "", article.title or "")
            article.ai_tags = json.dumps(tags, ensure_ascii=False)

            session.commit()
            results.append({"id": article_id, "status": "success", "tags": tags})

        except Exception as e:
            results.append({"id": article_id, "status": "error", "message": str(e)})

    return success_response({"results": results})


@router.post("/process", summary="AI 全部处理")
async def ai_process_all(request: AIAllRequest):
    """使用 AI 对文章进行总结、分类、提取标签"""
    session = DB.get_session()
    results = []

    for article_id in request.article_ids:
        try:
            article = session.query(Article).filter(Article.id == article_id).first()
            if not article:
                results.append({"id": article_id, "status": "error", "message": "文章不存在"})
                continue

            # 依次调用 AI 处理
            summary = await ai_service.summarize(article.content or "", article.title or "")
            category = await ai_service.categorize(article.content or "", article.title or "")
            tags = await ai_service.extract_tags(article.content or "", article.title or "")

            article.ai_summary = summary
            article.ai_category = category
            article.ai_tags = json.dumps(tags, ensure_ascii=False)

            session.commit()
            results.append({
                "id": article_id,
                "status": "success",
                "summary": summary,
                "category": category,
                "tags": tags
            })

        except Exception as e:
            results.append({"id": article_id, "status": "error", "message": str(e)})

    return success_response({"results": results})


@router.post("/process-all", summary="AI 批量处理全部文章")
async def ai_process_all_articles(
    mp_id: str = None,
    limit: int = Query(50, ge=1, le=500),
    skip_processed: bool = True
):
    """批量处理所有未 AI 处理的文章"""
    session = DB.get_session()
    try:
        query = session.query(Article).filter(Article.status == 1)

        if mp_id:
            query = query.filter(Article.mp_id == mp_id)

        # 跳过已处理的文章
        if skip_processed:
            query = query.filter(
                (Article.ai_summary == None) |
                (Article.ai_summary == "") |
                (Article.ai_category == None) |
                (Article.ai_category == "")
            )

        articles = query.order_by(Article.publish_time.desc()).limit(limit).all()

        results = []
        for article in articles:
            try:
                summary = await ai_service.summarize(article.content or "", article.title or "")
                category = await ai_service.categorize(article.content or "", article.title or "")
                tags = await ai_service.extract_tags(article.content or "", article.title or "")

                article.ai_summary = summary
                article.ai_category = category
                article.ai_tags = json.dumps(tags, ensure_ascii=False)

                session.commit()

                results.append({
                    "id": article.id,
                    "title": article.title,
                    "status": "success"
                })

            except Exception as e:
                results.append({
                    "id": article.id,
                    "title": article.title,
                    "status": "error",
                    "message": str(e)
                })

        return success_response({
            "total": len(articles),
            "results": results
        })

    except Exception as e:
        return error_response(50001, f"批量处理失败: {str(e)}")
