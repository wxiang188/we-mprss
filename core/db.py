"""数据库模块"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from core.models import Base
from core.config import cfg


class Database:
    """数据库管理类"""

    _engine = None
    _session_factory = None

    @classmethod
    def init(cls):
        """初始化数据库连接"""
        db_path = cfg.get("database.path", "./data/db.db")

        # 确保目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        # 创建数据库引擎
        db_url = f"sqlite:///{db_path}"
        cls._engine = create_engine(
            db_url,
            echo=cfg.get("server.debug", False),
            pool_pre_ping=True
        )

        # 创建会话工厂
        cls._session_factory = scoped_session(
            sessionmaker(bind=cls._engine, expire_on_commit=False)
        )

        # 创建所有表
        Base.metadata.create_all(cls._engine)
        print(f"数据库初始化完成: {db_path}")

    @classmethod
    def get_session(cls):
        """获取数据库会话"""
        if cls._session_factory is None:
            cls.init()
        return cls._session_factory()

    @classmethod
    def close(cls):
        """关闭数据库连接"""
        if cls._session_factory:
            cls._session_factory.remove()
        if cls._engine:
            cls._engine.dispose()


# 数据库实例
DB = Database()
