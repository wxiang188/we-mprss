#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WeChat MP RSS - 微信公众号 RSS 生成器 (复刻版)

主要功能：
1. 公众号订阅管理
2. 扫码授权获取公众号信息
3. 文章抓取
4. AI 自动总结、标签、分类
5. 数据导出 (CSV, JSON, PDF, DOCX)
"""

import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from core.config import cfg
from web import app


def main():
    """主函数"""
    print("=" * 60)
    print("  WeChat MP RSS - 微信公众号 RSS 生成器")
    print("  版本: 1.0.0")
    print("=" * 60)

    # 加载配置
    cfg.load()

    # 服务器配置
    host = cfg.get("server.host", "0.0.0.0")
    port = cfg.get("server.port", 8000)
    debug = cfg.get("server.debug", False)

    print(f"\n启动服务: http://{host}:{port}")
    print(f"API 文档: http://{host}:{port}/docs")
    print("\n按 Ctrl+C 停止服务\n")

    # 启动服务
    uvicorn.run(
        "web:app",
        host=host,
        port=port,
        reload=debug
    )


if __name__ == "__main__":
    main()
