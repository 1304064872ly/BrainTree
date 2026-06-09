import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import files, trees, analyze, export, models, config
from app.core.database import init_db

app = FastAPI(
    title="思维树 API",
    description="思维树应用后端API，支持文件上传、AI分析、思维树管理和导出功能",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 前端开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(files.router, prefix="/api/files", tags=["文件管理"])
app.include_router(trees.router, prefix="/api/trees", tags=["思维树管理"])
app.include_router(analyze.router, prefix="/api/analyze", tags=["AI分析"])
app.include_router(export.router, prefix="/api/trees", tags=["导出功能"])
app.include_router(models.router, prefix="/api/models", tags=["模型管理"])
app.include_router(config.router, prefix="/api/config", tags=["配置管理"])

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    print("[STARTUP] Initializing database...")
    init_db()
    print("[STARTUP] Database initialized")

@app.get("/")
async def root():
    return {
        "message": "思维树 API 服务",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
