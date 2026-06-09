import json
import csv
import io
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.models.schemas import ApiResponse
from app.models.db_models import MindTreeDB
from app.core.database import get_db

router = APIRouter()

@router.get("/{tree_id}/export/json")
async def export_json(tree_id: str, db: Session = Depends(get_db)):
    """导出JSON格式"""
    db_tree = db.query(MindTreeDB).filter(MindTreeDB.id == tree_id).first()
    if not db_tree:
        raise HTTPException(status_code=404, detail="思维树不存在")

    tree_dict = {
        "id": db_tree.id,
        "name": db_tree.name,
        "description": db_tree.description,
        "nodes": [
            {
                "id": node.id,
                "label": node.label,
                "description": node.description,
                "type": node.type,
                "level": node.level,
                "position": {"x": node.position_x, "y": node.position_y},
                "metadata": node.metadata_json or {}
            }
            for node in db_tree.nodes
        ],
        "edges": [
            {
                "id": edge.id,
                "source": edge.source_node_id,
                "target": edge.target_node_id,
                "label": edge.label,
                "type": edge.type
            }
            for edge in db_tree.edges
        ],
        "createdAt": db_tree.created_at.isoformat() if db_tree.created_at else None,
        "updatedAt": db_tree.updated_at.isoformat() if db_tree.updated_at else None
    }

    return ApiResponse(
        success=True,
        data=tree_dict
    )

@router.get("/{tree_id}/export/markdown")
async def export_markdown(tree_id: str, db: Session = Depends(get_db)):
    """导出Markdown格式"""
    db_tree = db.query(MindTreeDB).filter(MindTreeDB.id == tree_id).first()
    if not db_tree:
        raise HTTPException(status_code=404, detail="思维树不存在")

    md_content = f"# {db_tree.name}\n\n"

    if db_tree.description:
        md_content += f"{db_tree.description}\n\n"

    md_content += "## 节点列表\n\n"

    nodes_by_level = {}
    for node in db_tree.nodes:
        level = node.level
        if level not in nodes_by_level:
            nodes_by_level[level] = []
        nodes_by_level[level].append(node)

    for level in sorted(nodes_by_level.keys()):
        nodes = nodes_by_level[level]
        indent = "  " * (level - 1)

        for node in nodes:
            type_label = {
                "concept": "概念",
                "topic": "主题",
                "detail": "细节",
                "example": "示例"
            }.get(node.type, node.type)

            md_content += f"{indent}- **{node.label}** [{type_label}]\n"

            if node.description:
                md_content += f"{indent}  {node.description}\n"

            related_edges = [edge for edge in db_tree.edges if edge.source_node_id == node.id]

            if related_edges:
                md_content += f"{indent}  关联:\n"
                for edge in related_edges:
                    target_node = next(
                        (n for n in db_tree.nodes if n.id == edge.target_node_id),
                        None
                    )
                    if target_node:
                        md_content += f"{indent}    - {edge.label} -> {target_node.label}\n"

            md_content += "\n"

    md_content += "## 连接关系\n\n"
    md_content += "| 起始节点 | 关系 | 目标节点 |\n"
    md_content += "|----------|------|----------|\n"

    for edge in db_tree.edges:
        source_node = next((n for n in db_tree.nodes if n.id == edge.source_node_id), None)
        target_node = next((n for n in db_tree.nodes if n.id == edge.target_node_id), None)

        if source_node and target_node:
            md_content += f"| {source_node.label} | {edge.label} | {target_node.label} |\n"

    return StreamingResponse(
        io.BytesIO(md_content.encode("utf-8")),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={db_tree.name}.md"}
    )

@router.get("/{tree_id}/export/csv")
async def export_csv(tree_id: str, db: Session = Depends(get_db)):
    """导出CSV格式"""
    db_tree = db.query(MindTreeDB).filter(MindTreeDB.id == tree_id).first()
    if not db_tree:
        raise HTTPException(status_code=404, detail="思维树不存在")

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["节点ID", "节点名称", "节点描述", "节点类型", "层级"])

    for node in db_tree.nodes:
        writer.writerow([
            node.id,
            node.label,
            node.description,
            node.type,
            node.level
        ])

    writer.writerow([])

    writer.writerow(["连接ID", "起始节点ID", "目标节点ID", "连接标签", "连接类型"])

    for edge in db_tree.edges:
        writer.writerow([
            edge.id,
            edge.source_node_id,
            edge.target_node_id,
            edge.label,
            edge.type
        ])

    csv_content = output.getvalue()
    output.close()

    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={db_tree.name}.csv"}
    )

@router.post("/{tree_id}/export/image")
async def export_image(tree_id: str, format: str = "png", db: Session = Depends(get_db)):
    """导出图片格式（占位实现）"""
    db_tree = db.query(MindTreeDB).filter(MindTreeDB.id == tree_id).first()
    if not db_tree:
        raise HTTPException(status_code=404, detail="思维树不存在")

    return ApiResponse(
        success=True,
        message="图片导出功能需要前端实现，请使用前端界面导出"
    )

@router.post("/{tree_id}/export/pdf")
async def export_pdf(tree_id: str, db: Session = Depends(get_db)):
    """导出PDF格式（占位实现）"""
    db_tree = db.query(MindTreeDB).filter(MindTreeDB.id == tree_id).first()
    if not db_tree:
        raise HTTPException(status_code=404, detail="思维树不存在")

    return ApiResponse(
        success=True,
        message="PDF导出功能需要额外配置，请使用Markdown导出后转换为PDF"
    )
