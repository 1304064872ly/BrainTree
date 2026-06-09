import os
import uuid
from typing import List, Dict
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.schemas import SourceFile, ApiResponse
from app.models.db_models import SourceFileDB, TreeSourceFileDB
from app.core.database import get_db
from app.services.file_parser import FileParser

router = APIRouter()

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md', '.markdown'}

def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return os.path.splitext(filename)[1].lower()

@router.post("/upload", response_model=ApiResponse[SourceFile])
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传文件"""
    # 验证文件扩展名（更宽松的检查）
    ext = get_file_extension(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}，只支持 PDF、DOCX、TXT、Markdown 格式"
        )

    # 读取文件内容
    content = await file.read()
    file_size = len(content)

    # 验证文件大小（50MB）
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="文件大小不能超过 50MB"
        )

    # 解析文件内容
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

    # 创建文件记录
    file_id = str(uuid.uuid4())
    file_type = ext[1:]  # 去掉点号

    # 保存到数据库
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
        db.commit()
        db.refresh(db_file)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"数据库保存失败: {str(e)}"
        )

    # 返回响应（不包含content以避免JSON序列化问题）
    source_file = SourceFile(
        id=db_file.id,
        name=db_file.name,
        type=db_file.type,
        size=db_file.size,
        content="",  # 列表中不返回content
        uploadedAt=db_file.uploaded_at
    )

    return ApiResponse(
        success=True,
        data=source_file,
        message="文件上传成功"
    )

@router.get("", response_model=ApiResponse[List[SourceFile]])
async def get_files(db: Session = Depends(get_db)):
    """获取文件列表（不包含content以避免JSON序列化问题）"""
    db_files = db.query(SourceFileDB).all()
    files_list = [
        SourceFile(
            id=f.id,
            name=f.name,
            type=f.type,
            size=f.size,
            content="",  # 列表中不返回content
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
    """获取文件详情（包含content）"""
    db_file = db.query(SourceFileDB).filter(SourceFileDB.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="文件不存在")

    source_file = SourceFile(
        id=db_file.id,
        name=db_file.name,
        type=db_file.type,
        size=db_file.size,
        content=db_file.content,  # 详情中返回content
        uploadedAt=db_file.uploaded_at
    )

    return ApiResponse(
        success=True,
        data=source_file
    )

@router.delete("/{file_id}", response_model=ApiResponse)
async def delete_file(file_id: str, db: Session = Depends(get_db)):
    """删除文件"""
    db_file = db.query(SourceFileDB).filter(SourceFileDB.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        # 先删除关联记录
        db.query(TreeSourceFileDB).filter(TreeSourceFileDB.file_id == file_id).delete()

        # 再删除文件
        db.delete(db_file)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"删除失败: {str(e)}"
        )

    return ApiResponse(
        success=True,
        message="文件删除成功"
    )
