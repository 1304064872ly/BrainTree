"""
BrainTree 后端入口文件
====================

这是 FastAPI 应用的主入口文件，负责：
1. 创建 FastAPI 应用实例
2. 配置 CORS 跨域中间件（允许前端访问）
3. 注册所有 API 路由模块
4. 定义应用启动事件（初始化数据库）
5. 提供根路径和健康检查接口

启动方式：
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

# ============================================================
# 第一部分：标准输出编码设置
# ============================================================
# 在 Windows 环境下，Python 默认使用 GBK 编码输出，
# 这里强制将 stdout 切换为 UTF-8 编码，避免中文乱码问题
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ============================================================
# 第二部分：导入依赖
# ============================================================
from fastapi import FastAPI  # FastAPI 框架核心类
from fastapi.middleware.cors import CORSMiddleware  # CORS 跨域中间件

# 导入所有 API 路由模块
# 每个模块负责一组相关的 API 接口
from app.api import files      # 文件管理路由（上传、列表、删除）
from app.api import trees      # 思维树 CRUD 路由
from app.api import analyze    # AI 分析路由（分析文件、优化思维树）
from app.api import export     # 导出功能路由（JSON、Markdown、CSV）
from app.api import models     # 模型管理路由（服务商列表、模型列表）
from app.api import config     # 配置管理路由（AI 配置的增删改查）

# 导入数据库初始化函数
from app.core.database import init_db

# ============================================================
# 第三部分：创建 FastAPI 应用实例
# ============================================================
# FastAPI 构造函数参数说明：
# - title: API 文档标题（显示在 Swagger UI 页面顶部）
# - description: API 文档描述
# - version: API 版本号
app = FastAPI(
    title="思维树 API",
    description="思维树应用后端API，支持文件上传、AI分析、思维树管理和导出功能",
    version="1.0.0"
)

# ============================================================
# 第四部分：配置 CORS 跨域中间件
# ============================================================
# CORS（Cross-Origin Resource Sharing）跨域资源共享
# 由于前端（localhost:3000）和后端（localhost:8000）运行在不同端口，
# 浏览器会阻止跨域请求，需要配置 CORS 允许前端访问
#
# 参数说明：
# - allow_origins: 允许的前端地址列表（生产环境应限制为具体域名）
# - allow_credentials: 允许携带 Cookie 等认证信息
# - allow_methods: 允许的 HTTP 方法（* 表示全部允许）
# - allow_headers: 允许的请求头（* 表示全部允许）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 前端开发服务器地址
    allow_credentials=True,                    # 允许携带认证信息
    allow_methods=["*"],                       # 允许所有 HTTP 方法
    allow_headers=["*"],                       # 允许所有请求头
)

# ============================================================
# 第五部分：注册 API 路由
# ============================================================
# 将各个路由模块注册到 FastAPI 应用中
# 每个路由模块包含一组相关的 API 接口
#
# 参数说明：
# - router: 路由模块中的 APIRouter 实例
# - prefix: URL 前缀（所有该模块的路由都会加上这个前缀）
# - tags: API 文档分组标签（在 Swagger UI 中用于分组显示）

# 文件管理路由：处理文件上传、获取文件列表、获取文件详情、删除文件
# 完整路径示例：POST /api/files/upload, GET /api/files, GET /api/files/{id}
app.include_router(files.router, prefix="/api/files", tags=["文件管理"])

# 思维树 CRUD 路由：创建、读取、更新、删除思维树及其节点和连接
# 完整路径示例：POST /api/trees, GET /api/trees/{id}, PUT /api/trees/{id}
app.include_router(trees.router, prefix="/api/trees", tags=["思维树管理"])

# AI 分析路由：分析文件生成思维树、根据反馈优化思维树
# 完整路径示例：POST /api/analyze, POST /api/analyze/refine
app.include_router(analyze.router, prefix="/api/analyze", tags=["AI分析"])

# 导出功能路由：将思维树导出为 JSON、Markdown、CSV、图片、PDF 格式
# 完整路径示例：GET /api/trees/{id}/export/json, GET /api/trees/{id}/export/markdown
app.include_router(export.router, prefix="/api/trees", tags=["导出功能"])

# 模型管理路由：获取支持的 AI 服务商列表和模型列表
# 完整路径示例：GET /api/models/providers, GET /api/models/models
app.include_router(models.router, prefix="/api/models", tags=["模型管理"])

# 配置管理路由：获取、更新 AI 配置，测试连接
# 完整路径示例：GET /api/config, PUT /api/config, POST /api/config/test
app.include_router(config.router, prefix="/api/config", tags=["配置管理"])

# ============================================================
# 第六部分：应用启动事件
# ============================================================
# @app.on_event("startup") 装饰器定义应用启动时执行的函数
# 当 FastAPI 应用启动时，会自动调用此函数
#
# 功能：初始化数据库连接并创建所有数据表
# 注意：这只是确保表结构存在，不会修改已有数据
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    print("[STARTUP] Initializing database...")
    init_db()  # 调用数据库初始化函数，创建所有数据表
    print("[STARTUP] Database initialized")

# ============================================================
# 第七部分：基础路由
# ============================================================

@app.get("/")
async def root():
    """
    根路径接口

    返回 API 的基本信息，可用于：
    1. 验证后端服务是否正常运行
    2. 获取 API 文档地址
    3. 作为服务发现的入口

    Returns:
        dict: 包含消息、版本和文档地址的字典
    """
    return {
        "message": "思维树 API 服务",  # 服务名称
        "version": "1.0.0",            # API 版本
        "docs": "/docs"                 # Swagger API 文档地址
    }

@app.get("/health")
async def health_check():
    """
    健康检查接口

    用于监控系统或负载均衡器检查服务是否健康。
    返回 200 状态码表示服务正常运行。

    Returns:
        dict: 包含健康状态的字典
    """
    return {"status": "healthy"}  # 返回健康状态
