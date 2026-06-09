"""
数据库配置模块
=============

本模块负责配置和管理 MySQL 数据库连接。
使用 SQLAlchemy 作为 ORM 框架，提供：
1. 数据库连接引擎
2. 会话工厂
3. 声明基类
4. 依赖注入函数
5. 数据库初始化函数

技术栈：
- SQLAlchemy: Python SQL 工具包和 ORM
- PyMySQL: MySQL 驱动
- MySQL: 关系型数据库

配置来源：
- 优先从 .env 文件读取 DATABASE_URL
- 格式: mysql+pymysql://用户名:密码@主机:端口/数据库名

主要导出：
- engine: SQLAlchemy 引擎实例
- SessionLocal: 会话工厂
- Base: ORM 模型基类
- get_db(): 依赖注入函数
- init_db(): 数据库初始化函数
"""

# ============================================================
# 第一部分：导入依赖
# ============================================================
import os                           # 读取环境变量
from sqlalchemy import create_engine  # 创建数据库引擎
from sqlalchemy.ext.declarative import declarative_base  # 声明基类
from sqlalchemy.orm import sessionmaker  # 会话工厂
from dotenv import load_dotenv       # 加载 .env 文件

# 加载 .env 文件中的环境变量
load_dotenv()

# ============================================================
# 第二部分：数据库连接配置
# ============================================================

# MySQL 连接字符串
# 格式: mysql+pymysql://用户名:密码@主机:端口/数据库名
# 从环境变量读取，如果未配置则使用默认值
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:123456@localhost:3306/brain_tree"  # 默认值
)

# ============================================================
# 第三部分：创建 SQLAlchemy 引擎
# ============================================================

# SQLAlchemy 引擎是数据库连接的核心
# 负责管理连接池、执行 SQL 语句、处理事务
engine = create_engine(
    DATABASE_URL,
    echo=True,            # 打印 SQL 语句（调试用，生产环境应关闭）
    pool_size=10,         # 连接池大小：保持10个空闲连接
    max_overflow=20,      # 最大溢出连接数：高峰期最多额外创建20个连接
    pool_pre_ping=True    # 自动检测断开的连接：使用前先 ping 一下
)

# ============================================================
# 第四部分：创建会话工厂
# ============================================================

# SessionLocal 是会话工厂，每次请求创建一个新的数据库会话
# 会话用于执行查询、添加记录、提交事务等操作
SessionLocal = sessionmaker(
    autocommit=False,  # 不自动提交事务（需要手动 commit）
    autoflush=False,   # 不自动刷新（查询前不自动提交未决的更改）
    bind=engine        # 绑定到引擎
)

# ============================================================
# 第五部分：创建声明基类
# ============================================================

# Base 是所有 ORM 模型的基类
# 所有数据表模型都必须继承这个类
# SQLAlchemy 通过它来管理表结构和模型映射
Base = declarative_base()

# ============================================================
# 第六部分：数据库工具函数
# ============================================================

def get_db():
    """
    获取数据库会话（依赖注入函数）

    这是一个生成器函数，用于 FastAPI 的依赖注入。
    每次请求时创建一个新的数据库会话，请求结束后自动关闭。

    使用方式：
        @router.get("/example")
        async def example(db: Session = Depends(get_db)):
            result = db.query(SomeModel).all()
            return result

    Yields:
        Session: SQLAlchemy 数据库会话

    注意：
    - 使用 yield 而不是 return，确保会话在请求结束后被关闭
    - FastAPI 会自动处理生成器的生命周期
    """
    db = SessionLocal()  # 创建新会话
    try:
        yield db          # 将会话提供给路由函数
    finally:
        db.close()        # 请求结束后关闭会话，释放连接

def init_db():
    """
    初始化数据库（创建所有数据表）

    根据 ORM 模型定义创建所有数据表。
    如果表已存在，则不会重复创建。

    调用时机：
    - 应用启动时（main.py 的 startup_event）
    - 手动执行 init_db.py 脚本

    注意：
    - 只创建表结构，不会修改已有数据
    - 如果需要修改表结构，需要使用数据库迁移工具（如 Alembic）
    """
    # 导入所有 ORM 模型，确保它们被注册到 Base.metadata 中
    from app.models import db_models

    # 创建所有数据表
    # checkfirst=True 表示如果表已存在则跳过
    Base.metadata.create_all(bind=engine)
