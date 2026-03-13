"""Web 应用入口"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os

from core.config import cfg
from core.db import DB

# API 路由
from apis.mps import router as mps_router
from apis.articles import router as articles_router
from apis.ai import router as ai_router
from apis.export import router as export_router

# 创建 FastAPI 应用
app = FastAPI(
    title="WeChat MP RSS API",
    description="微信公众号 RSS 生成服务 API",
    version="1.0.0"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(mps_router, prefix="/api")
app.include_router(articles_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(export_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    print("=" * 50)
    print("WeChat MP RSS 启动中...")
    print("=" * 50)

    # 初始化数据库
    DB.init()

    print("=" * 50)
    print("服务启动完成！")
    print("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    DB.close()
    print("服务已关闭")


@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc):
    """处理 404 错误，支持 SPA 路由和根目录静态文件"""
    path = request.url.path

    # 1. API 或文档请求直接返回 404
    if path.startswith("/api") or path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi.json"):
        return JSONResponse(status_code=404, content={"message": "Not Found", "path": path})

    # 2. 尝试匹配 static 目录下的物理文件 (例如 /favicon.svg)
    # 去除开头的斜杠
    file_path = path.lstrip("/")
    if not file_path:
        file_path = "index.html"

    static_file = os.path.join(os.path.dirname(__file__), "static", file_path)
    if os.path.isfile(static_file):
        return FileResponse(static_file)

    # 3. 否则返回 index.html (支持前端 SPA 路由，如 /mps, /articles)
    index_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)

    return JSONResponse(status_code=404, content={"message": "Not Found", "path": path})


@app.get("/")
async def root():
    """根路径 - 优先返回前端 UI"""
    index_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "name": "WeChat MP RSS API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


# 静态文件服务
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
# 同时挂载资产目录（适配 Vite 构建）
assets_dir = os.path.join(static_dir, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


if __name__ == "__main__":
    import uvicorn

    host = cfg.get("server.host", "0.0.0.0")
    port = cfg.get("server.port", 8000)
    debug = cfg.get("server.debug", False)

    uvicorn.run(app, host=host, port=port)
