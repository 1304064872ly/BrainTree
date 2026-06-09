import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# MySQL 连接配置
# 格式: mysql+pymysql://用户名:密码@主机:端口/数据库名
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:123456@localhost:3306/brain_tree")

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    echo=True,  # 打印SQL语句，生产环境可关闭
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 最大溢出连接数
    pool_pre_ping=True  # 自动检测断开的连接
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库（创建表）"""
    from app.models import db_models
    Base.metadata.create_all(bind=engine)
