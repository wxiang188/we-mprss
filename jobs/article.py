"""
文章处理回调模块
复刻原项目的文章处理逻辑
"""
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable

from core.db import DB
from core.models import Feed, Article
from core.config import cfg


class ArticleHandler:
    """文章处理器"""

    @staticmethod
    def update_article(art: Dict[str, Any], check_exist: bool = False) -> bool:
        """更新/保存文章

        Args:
            art: 文章数据字典
            check_exist: 是否检查文章是否已存在

        Returns:
            是否保存成功
        """
        session = DB.get_session()
        try:
            # 解析文章数据
            article_id = art.get('id') or art.get('aid')
            if not article_id:
                # 生成文章ID
                article_id = f"art_{int(time.time())}_{uuid.uuid4().hex[:8]}"

            mp_id = art.get('mp_id')
            title = art.get('title', '无标题')
            url = art.get('url') or art.get('link', '')
            pic_url = art.get('pic_url') or art.get('cover', '')
            content = art.get('content', '')
            description = art.get('description') or art.get('digest', '')
            author = art.get('author', '')

            # 解析发布时间
            publish_time = art.get('publish_time') or art.get('update_time', 0)
            if isinstance(publish_time, str):
                try:
                    publish_time = int(publish_time)
                except (ValueError, TypeError):
                    publish_time = 0
            elif isinstance(publish_time, datetime):
                publish_time = int(publish_time.timestamp())

            # 检查是否已存在
            if check_exist:
                existing = session.query(Article).filter(
                    Article.mp_id == mp_id,
                    Article.title == title
                ).first()
                if existing:
                    return False

            # 创建或更新文章
            article = session.query(Article).filter(Article.id == article_id).first()

            if article:
                # 更新现有文章
                article.title = title
                article.url = url
                article.pic_url = pic_url
                article.content = content
                article.description = description
                article.author = author
                article.publish_time = publish_time
            else:
                # 创建新文章
                article = Article(
                    id=article_id,
                    mp_id=mp_id,
                    title=title,
                    url=url,
                    pic_url=pic_url,
                    content=content,
                    description=description,
                    author=author,
                    publish_time=publish_time,
                    status=1,
                    is_export=0
                )
                session.add(article)

            session.commit()
            return True

        except Exception as e:
            session.rollback()
            print(f"保存文章失败: {e}")
            return False
        finally:
            session.close()

    @staticmethod
    def update_over(data: Any = None):
        """文章更新完成回调"""
        print("文章更新完成")
        pass


# 导出快捷函数，与原项目保持一致
UpdateArticle = ArticleHandler.update_article
Update_Over = ArticleHandler.update_over
