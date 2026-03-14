from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()


class Feed(Base):
    """公众号模型"""
    __tablename__ = 'feeds'

    id = Column(String(255), primary_key=True)
    mp_name = Column(String(255), nullable=False)  # 公众号名称
    mp_cover = Column(String(500))  # 封面图
    mp_intro = Column(String(1000))  # 简介
    faker_id = Column(String(255), unique=True)  # 微信 Faker ID
    status = Column(Integer, default=1)  # 状态: 0=禁用, 1=正常
    sync_time = Column(Integer)  # 最后同步时间
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'mp_name': self.mp_name,
            'mp_cover': self.mp_cover,
            'mp_intro': self.mp_intro,
            'faker_id': self.faker_id,
            'status': self.status,
            'sync_time': self.sync_time,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Article(Base):
    """文章模型"""
    __tablename__ = 'articles'

    id = Column(String(255), primary_key=True)
    mp_id = Column(String(255), nullable=False)  # 公众号 ID
    title = Column(String(1000), nullable=False)  # 标题
    url = Column(String(500))  # 原文链接
    pic_url = Column(String(500))  # 封面图
    description = Column(Text)  # 描述/摘要
    digest = Column(Text)  # 摘要（与 description 相同）
    content = Column(Text)  # 文章内容
    content_html = Column(Text)  # HTML 内容
    author = Column(String(255))  # 作者
    publish_time = Column(Integer)  # 发布时间戳
    status = Column(Integer, default=1)  # 状态
    is_read = Column(Integer, default=0)  # 已读标记
    is_export = Column(Integer, default=0)  # 已导出标记

    # AI 处理字段
    ai_category = Column(String(50), default="其他")  # AI 分类
    ai_summary = Column(String(2000))  # AI 总结
    ai_tags = Column(Text)  # AI 标签 (JSON 数组)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'mp_id': self.mp_id,
            'title': self.title,
            'url': self.url,
            'pic_url': self.pic_url,
            'description': self.description,
            'digest': self.digest,
            'content': self.content,
            'content_html': self.content_html,
            'author': self.author,
            'publish_time': self.publish_time,
            'status': self.status,
            'is_read': self.is_read,
            'is_export': self.is_export,
            'ai_category': self.ai_category,
            'ai_summary': self.ai_summary,
            'ai_tags': self.ai_tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Tag(Base):
    """标签模型"""
    __tablename__ = 'tags'

    id = Column(String(255), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)  # 标签名称
    cover = Column(String(500))  # 封面图
    intro = Column(String(500))  # 描述
    status = Column(Integer, default=1)
    mps_id = Column(Text)  # 关联的公众号 ID 列表 (JSON)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'cover': self.cover,
            'intro': self.intro,
            'status': self.status,
            'mps_id': self.mps_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Config(Base):
    """系统配置模型"""
    __tablename__ = 'config'

    key = Column(String(100), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'key': self.key,
            'value': self.value,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
