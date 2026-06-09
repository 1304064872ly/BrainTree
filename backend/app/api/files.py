"""
文件管理 API 路由模块
===================

本模块提供文件管理相关的 API 接口，负责：
1. 上传文件（支持 PDF、DOCX、TXT、Markdown）
2. 获取文件列表
3. 获取文件详情
4. 删除文件

API 接口：
- POST /api/files/upload - 上传文件
- GET /api/files - 获取文件列表（不包含 content）
- GET /api/files/{file_id} - 获取文件详情（包含 content）
- DELETE /api/files/{file_id} - 删除文件

文件处理流程：
1. 验证文件格式和大小
2. 读取文件内容
3. 解析文件提取文本
4. 保存到数据库

支持的文件格式：
- PDF: 使用 pymupdf/PyPDF2/OCR 解析
- DOCX: 使用 python-docx 解析
- TXT: 支持多种编码（UTF-8、GBK 等）
- Markdown: 按文本解析

限制：
- 单文件最大 50MB
- 只支持特定格式
"""

# ============================================================
# 第一部分：导入依赖
# ============================================================
import os                               # 文件路径处理
import uuid                             # UUID 生成
from typing import List, Dict           # 类型注解
from datetime import datetime           # 日期时间处理
from fastapi import (                   # FastAPI 核心组件
    APIRouter,      # 路由定义
    UploadFile,     # 上传文件
    File,           # 文件参数
    HTTPException,  # HTTP 异常
    Depends         # 依赖注入
)
from sqlalchemy.orm import Session      # 数据库会话

# 导入数据模型
from app.models.schemas import (
    SourceFile,     # 源文件响应模型
    ApiResponse     # 通用响应模型
)
from app.models.db_models import (
    SourceFileDB,       # 文件数据库模型
    TreeSourceFileDB    # 思维树-文件关联数据库模型
)

# 导入核心组件
from app.core.database import get_db    # 数据库会话依赖注入

# 导入服务层
from app.services.file_parser import FileParser  # 文件解析器

# ============================================================
# 第二部分：创建路由实例和常量
# ============================================================
router = APIRouter()

# 允许的文件扩展名
# 只支持这些格式的文件上传
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md', '.markdown'}


# ============================================================
# 第三部分：辅助函数
# ============================================================

def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名

    从文件名中提取扩展名并转换为小写。

    Args:
        filename: 文件名

    Returns:
        str: 小写的文件扩展名（包含点号）

    示例：
        get_file_extension("document.PDF")  # 返回 ".pdf"
        get_file_extension("notes.txt")     # 返回 ".txt"
    """
    return os.path.splitext(filename)[1].lower()


# ============================================================
# 第四部分：API 路由
# ============================================================

@router.post("/upload", response_model=ApiResponse[SourceFile])
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    上传文件

    处理文件上传请求，包括：
    1. 验证文件格式
    2. 验证文件大小
    3. 解析文件内容
    4. 保存到数据库

    Args:
        file: 上传的文件对象（FastAPI 自动解析）
        db: 数据库会话（依赖注入）

    Returns:
        ApiResponse[SourceFile]: 上传成功后的文件信息

    Raises:
        HTTPException: 文件格式不支持、文件过大或解析失败

    使用示例：
        POST /api/files/upload
        Content-Type: multipart/form-data
        Body: file=@document.pdf

    注意：
    - 列表接口不返回 content 字段（避免响应过大）
    - 详情接口返回完整的 content 字段
    """
    # ============================================================
    # 步骤1：验证文件扩展名
    # ============================================================
    ext = get_file_extension(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}，只支持 PDF、DOCX、TXT、Markdown 格式"
        )

    # ============================================================
    # 步骤2：读取文件内容
    # ============================================================
    content = await file.read()
    file_size = len(content)

    # ============================================================
    # 步骤3：验证文件大小（50MB）
    # ============================================================
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="文件大小不能超过 50MB"
        )

    # ============================================================
    # 步骤4：解析文件内容
    # ============================================================
    parser = FileParser()
    try:
        text_content = await parser.parse(file.filename, content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"文件解析失败: {str(e)}"
        )

    # 如果解析内容为空，给一个默认提示
    if not text_content or text_content.strip() == "":
        text_content = f"[文件 {file.filename} 内容为空或无法提取文本]"

    # ============================================================
    # 步骤5：保存到数据库
    # ============================================================
    file_id = str(uuid.uuid4())  # 生成唯一 ID
    file_type = ext[1:]          # 去掉点号（如 ".pdf" -> "pdf"）

    try:
        db_file = SourceFileDB(
            id=file_id,
            name=file.filename,
            type=file_type,
            size=file_size,
            content=text_content,
            uploaded_at=datetime.now()
        )
        db.add(db_file)
        db.commit()        # 提交事务
        db.refresh(db_file) # 刷新对象获取最新数据
    except Exception as e:
        db.rollback()  # 回滚事务
        raise HTTPException(
            status_code=500,
            detail=f"数据库保存失败: {str(e)}"
        )

    # ============================================================
    # 步骤6：构建响应
    # ============================================================
    # 列表中不返回 content（避免响应过大）
    source_file = SourceFile(
        id=db_file.id,
        name=db_file.name,
        type=db_file.type,
        size=db_file.size,
        content="",  # 列表中不返回 content
        uploadedAt=db_file.uploaded_at
    )

    return ApiResponse(
        success=True,
        data=source_file,
        message="文件上传成功"
    )


@router.get("", response_model=ApiResponse[List[SourceFile]])
async def get_files(db: Session = Depends(get_db)):
    """
    获取文件列表（不包含 content）

    返回所有已上传的文件列表。
    为了性能考虑，不返回 content 字段。

    Args:
        db: 数据库会话（依赖注入）

    Returns:
        ApiResponse[List[SourceFile]]: 文件列表

    使用场景：
        - 文件上传页面显示已上传文件
        - 选择文件进行 AI 分析

    注意：
    - 不返回 content 字段（避免响应过大）
    - 如需获取完整内容，请使用详情接口
    """
    # 查询所有文件
    db_files = db.query(SourceFileDB).all()

    # 构建响应列表（不包含 content）
    files_list = [
        SourceFile(
            id=f.id,
            name=f.name,
            type=f.type,
            size=f.size,
            content="",  # 列表中不返回 content
            uploadedAt=f.uploaded_at
        )
        for f in db_files
    ]

    return ApiResponse(
        success=True,
        data=files_list
    )


@router.get("/{file_id}", response_model=ApiResponse[SourceFile])
async def get_file(file_id: str, db: Session = Depends(get_db)):
    """
    获取文件详情（包含 content）

    根据文件 ID 获取文件的完整信息，包括提取的文本内容。

    Args:
        file_id: 文件 ID
        db: 数据库会话（依赖注入）

    Returns:
        ApiResponse[SourceFile]: 文件详情

    Raises:
        HTTPException: 文件不存在

    使用场景：
        - 查看文件详情
        - 预览文件内容
    """
    # 查询文件
    db_file = db.query(SourceFileDB).filter(SourceFileDB.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 构建响应（包含 content）
    source_file = SourceFile(
        id=db_file.id,
        name=db_file.name,
        type=db_file.type,
        size=db_file.size,
        content=db_file.content,  # 详情中返回 content
        uploadedAt=db_file.uploaded_at
    )

    return ApiResponse(
        success=True,
        data=source_file
    )


@router.delete("/{file_id}", response_model=ApiResponse)
async def delete_file(file_id: str, db: Session = Depends(get_db)):
    """
    删除文件

    根据文件 ID 删除文件及其关联记录。

    Args:
        file_id: 文件 ID
        db: 数据库会话（依赖注入）

    Returns:
        ApiResponse: 删除结果

    Raises:
        HTTPException: 文件不存在或删除失败

    删除顺序：
    1. 先删除思维树-文件关联记录
    2. 再删除文件本身

    注意：
    - 删除文件会同时删除关联记录
    - 不会删除已生成的思维树
    """
    # 查询文件
    db_file = db.query(SourceFileDB).filter(SourceFileDB.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        # 先删除关联记录（思维树-文件关联）
        db.query(TreeSourceFileDB).filter(TreeSourceFileDB.file_id == file_id).delete()

        # 再删除文件本身
        db.delete(db_file)
        db.commit()  # 提交事务
    except Exception as e:
        db.rollback()  # 回滚事务
        raise HTTPException(
            status_code=500,
            detail=f"删除失败: {str(e)}"
        )

    return ApiResponse(
        success=True,
        message="文件删除成功"
    )
