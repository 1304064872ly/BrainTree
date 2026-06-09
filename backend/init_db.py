"""数据库初始化脚本"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pymysql
from app.core.database import engine, init_db, DATABASE_URL

def create_database():
    """创建数据库（如果不存在）"""
    db_name = DATABASE_URL.split("/")[-1]

    try:
        parts = DATABASE_URL.replace("mysql+pymysql://", "").split("@")
        user_pass = parts[0].split(":") if ":" in parts[0] else [parts[0], ""]
        user = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ""

        host_port = parts[1].split("/")[0].split(":")
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 3306

        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4'
        )

        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"[OK] Database '{db_name}' created or already exists")

        connection.close()

    except Exception as e:
        print(f"[ERROR] Failed to create database: {e}")
        raise

def create_tables():
    """创建所有表"""
    try:
        init_db()
        print("[OK] All tables created successfully")
    except Exception as e:
        print(f"[ERROR] Failed to create tables: {e}")
        raise

if __name__ == "__main__":
    print("[START] Initializing database...")
    print(f"[INFO] Connection: {DATABASE_URL}")
    print()

    create_database()
    create_tables()

    print()
    print("[DONE] Database initialization completed!")
