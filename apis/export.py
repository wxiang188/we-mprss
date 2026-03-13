"""数据导出 API"""
import csv
import json
import os
import time
import uuid
import zipfile
from datetime import datetime
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from core.db import DB
from core.models import Feed, Article

router = APIRouter(prefix="/wx/export", tags=["数据导出"])


def get_export_dir():
    """获取导出目录"""
    export_dir = "./data/exports"
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    return export_dir


@router.get("/mps", summary="导出公众号列表")
async def export_mps(
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    kw: str = Query("")
):
    """导出公众号列表为 CSV"""
    session = DB.get_session()
    try:
        query = session.query(Feed)
        if kw:
            query = query.filter(Feed.mp_name.ilike(f"%{kw}%"))

        mps = query.order_by(Feed.created_at.desc()).limit(limit).offset(offset).all()

        # CSV 头部
        headers = ["id", "公众号名称", "封面图", "简介", "状态", "创建时间", "faker_id"]

        # CSV 数据
        data = [[
            mp.id,
            mp.mp_name,
            mp.mp_cover,
            mp.mp_intro,
            mp.status,
            mp.created_at.isoformat() if mp.created_at else "",
            mp.faker_id
        ] for mp in mps]

        # 创建临时 CSV 文件
        export_dir = get_export_dir()
        temp_file = f"{export_dir}/mps_{int(time.time())}.csv"

        with open(temp_file, "w", encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)

        return FileResponse(
            temp_file,
            media_type="text/csv; charset=utf-8-sig",
            filename="公众号列表.csv",
            background=BackgroundTask(lambda: os.remove(temp_file))
        )

    except Exception as e:
        print(f"导出公众号列表错误: {str(e)}")
        raise HTTPException(status_code=500, detail="导出失败")


@router.get("/tags", summary="导出标签列表")
async def export_tags(
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    kw: str = Query("")
):
    """导出标签列表为 CSV"""
    session = DB.get_session()
    from core.models import Tag

    try:
        query = session.query(Tag)
        if kw:
            query = query.filter(Tag.name.ilike(f"%{kw}%"))

        tags = query.order_by(Tag.created_at.desc()).limit(limit).offset(offset).all()

        headers = ["id", "标签名称", "描述", "状态", "创建时间", "mps_id"]
        data = [[
            tag.id,
            tag.name,
            tag.intro,
            tag.status,
            tag.created_at.isoformat() if tag.created_at else "",
            tag.mps_id
        ] for tag in tags]

        export_dir = get_export_dir()
        temp_file = f"{export_dir}/tags_{int(time.time())}.csv"

        with open(temp_file, "w", encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)

        return FileResponse(
            temp_file,
            media_type="text/csv; charset=utf-8-sig",
            filename="标签列表.csv",
            background=BackgroundTask(lambda: os.remove(temp_file))
        )

    except Exception as e:
        print(f"导出标签列表错误: {str(e)}")
        raise HTTPException(status_code=500, detail="导出失败")


@router.get("/articles", summary="导出文章列表")
async def export_articles(
    mp_id: str = None,
    limit: int = Query(100, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    format: str = Query("csv", regex="^(csv|json)$")
):
    """导出文章列表"""
    session = DB.get_session()
    try:
        query = session.query(Article).filter(Article.status == 1)
        if mp_id:
            query = query.filter(Article.mp_id == mp_id)

        articles = query.order_by(Article.publish_time.desc()).limit(limit).offset(offset).all()

        export_dir = get_export_dir()

        if format == "csv":
            # CSV 格式
            headers = ["文章标题", "所属公众号", "分类标签", "AI总结", "发布时间", "原文链接"]

            data = []
            for art in articles:
                mp = session.query(Feed).filter(Feed.id == art.mp_id).first()
                mp_name = mp.mp_name if mp else ""

                data.append([
                    art.title,
                    mp_name,
                    art.ai_category or "",
                    art.ai_summary or "",
                    datetime.fromtimestamp(art.publish_time).strftime("%Y-%m-%d %H:%M:%S") if art.publish_time else "",
                    art.url or ""
                ])

            temp_file = f"{export_dir}/articles_{int(time.time())}.csv"

            with open(temp_file, "w", encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(data)

            return FileResponse(
                temp_file,
                media_type="text/csv; charset=utf-8-sig",
                filename="文章列表.csv",
                background=BackgroundTask(lambda: os.remove(temp_file))
            )

        else:
            # JSON 格式
            result = []
            for art in articles:
                mp = session.query(Feed).filter(Feed.id == art.mp_id).first()
                art_dict = art.to_dict()
                art_dict["mp_name"] = mp.mp_name if mp else ""
                result.append(art_dict)

            temp_file = f"{export_dir}/articles_{int(time.time())}.json"

            with open(temp_file, "w", encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            return FileResponse(
                temp_file,
                media_type="application/json; charset=utf-8",
                filename="文章列表.json",
                background=BackgroundTask(lambda: os.remove(temp_file))
            )

    except Exception as e:
        print(f"导出文章列表错误: {str(e)}")
        raise HTTPException(status_code=500, detail="导出失败")


@router.post("/articles/zip", summary="导出文章详细内容")
async def export_articles_zip(
    mp_id: str = None,
    limit: int = Query(10, ge=1, le=100),
    include_content: bool = True,
    export_csv: bool = True,
    export_json: bool = True,
    export_md: bool = False
):
    """导出文章详细内容（打包为 ZIP）"""
    session = DB.get_session()
    try:
        query = session.query(Article).filter(Article.status == 1)
        if mp_id:
            query = query.filter(Article.mp_id == mp_id)

        articles = query.order_by(Article.publish_time.desc()).limit(limit).all()

        export_dir = get_export_dir()
        zip_filename = f"{export_dir}/articles_{int(time.time())}.zip"

        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 导出 CSV
            if export_csv:
                csv_data = StringIO()
                writer = csv.writer(csv_data)
                writer.writerow(["文章标题", "所属公众号", "分类标签", "AI总结", "发布时间", "原文链接"])

                for art in articles:
                    mp = session.query(Feed).filter(Feed.id == art.mp_id).first()
                    mp_name = mp.mp_name if mp else ""

                    writer.writerow([
                        art.title,
                        mp_name,
                        art.ai_category or "",
                        art.ai_summary or "",
                        datetime.fromtimestamp(art.publish_time).strftime("%Y-%m-%d %H:%M:%S") if art.publish_time else "",
                        art.url or ""
                    ])

                zipf.writestr("articles.csv", csv_data.getvalue())

            # 导出 JSON
            if export_json:
                result = []
                for art in articles:
                    mp = session.query(Feed).filter(Feed.id == art.mp_id).first()
                    art_dict = art.to_dict()
                    art_dict["mp_name"] = mp.mp_name if mp else ""
                    result.append(art_dict)

                zipf.writestr("articles.json", json.dumps(result, ensure_ascii=False, indent=2))

            # 导出 Markdown
            if export_md:
                for art in articles:
                    mp = session.query(Feed).filter(Feed.id == art.mp_id).first()
                    mp_name = mp.mp_name if mp else ""

                    md_content = f"""# {art.title}

**所属公众号**: {mp_name}
**发布时间**: {datetime.fromtimestamp(art.publish_time).strftime("%Y-%m-%d %H:%M:%S") if art.publish_time else ""}
**分类**: {art.ai_category or "未分类"}
**标签**: {art.ai_tags or ""}
**AI总结**: {art.ai_summary or "暂无"}

---

{art.content or art.description or ""}
"""

                    filename = f"articles/{art.title[:50]}.md"
                    zipf.writestr(filename, md_content)

        return FileResponse(
            zip_filename,
            media_type="application/zip",
            filename=f"文章导出_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            background=BackgroundTask(lambda: os.remove(zip_filename))
        )

    except Exception as e:
        print(f"导出文章内容错误: {str(e)}")
        raise HTTPException(status_code=500, detail="导出失败")
