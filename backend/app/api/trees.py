import uuid
from typing import List, Dict
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.schemas import MindTree, MindTreeCreate, ApiResponse
from app.models.db_models import MindTreeDB, MindNodeDB, MindEdgeDB, TreeSourceFileDB
from app.core.database import get_db

router = APIRouter()

def build_tree_response(db_tree: MindTreeDB) -> MindTree:
    """从数据库对象构建响应对象"""
    return MindTree(
        id=db_tree.id,
        name=db_tree.name,
        description=db_tree.description or "",
        sourceFiles=[sf.file_id for sf in db_tree.source_files],
        nodes=[
            MindNodeDB.to_dict(node) if hasattr(node, 'to_dict') else {
                "id": node.id,
                "label": node.label,
                "description": node.description or "",
                "type": node.type,
                "level": node.level,
                "position": {"x": node.position_x, "y": node.position_y},
                "metadata": node.metadata_json or {}
            }
            for node in db_tree.nodes
        ],
        edges=[
            MindEdgeDB.to_dict(edge) if hasattr(edge, 'to_dict') else {
                "id": edge.id,
                "source": edge.source_node_id,
                "target": edge.target_node_id,
                "label": edge.label or "",
                "type": edge.type
            }
            for edge in db_tree.edges
        ],
        createdAt=db_tree.created_at,
        updatedAt=db_tree.updated_at
    )

@router.post("", response_model=ApiResponse[MindTree])
async def create_tree(tree_data: MindTreeCreate, db: Session = Depends(get_db)):
    """创建思维树"""
    tree_id = str(uuid.uuid4())

    db_tree = MindTreeDB(
        id=tree_id,
        name=tree_data.name,
        description=tree_data.description or "",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.add(db_tree)
    db.commit()
    db.refresh(db_tree)

    tree = build_tree_response(db_tree)

    return ApiResponse(
        success=True,
        data=tree,
        message="思维树创建成功"
    )

@router.get("", response_model=ApiResponse[List[MindTree]])
async def get_trees(db: Session = Depends(get_db)):
    """获取思维树列表"""
    db_trees = db.query(MindTreeDB).all()
    trees_list = [build_tree_response(t) for t in db_trees]

    return ApiResponse(
        success=True,
        data=trees_list
    )

@router.get("/{tree_id}", response_model=ApiResponse[MindTree])
async def get_tree(tree_id: str, db: Session = Depends(get_db)):
    """获取思维树详情"""
    db_tree = db.query(MindTreeDB).filter(MindTreeDB.id == tree_id).first()
    if not db_tree:
        raise HTTPException(status_code=404, detail="思维树不存在")

    tree = build_tree_response(db_tree)

    return ApiResponse(
        success=True,
        data=tree
    )

@router.put("/{tree_id}", response_model=ApiResponse[MindTree])
async def update_tree(tree_id: str, tree_data: MindTreeCreate, db: Session = Depends(get_db)):
    """更新思维树"""
    db_tree = db.query(MindTreeDB).filter(MindTreeDB.id == tree_id).first()
    if not db_tree:
        raise HTTPException(status_code=404, detail="思维树不存在")

    db_tree.name = tree_data.name
    db_tree.description = tree_data.description or db_tree.description
    db_tree.updated_at = datetime.now()

    db.commit()
    db.refresh(db_tree)

    tree = build_tree_response(db_tree)

    return ApiResponse(
        success=True,
        data=tree,
        message="思维树更新成功"
    )

@router.delete("/{tree_id}", response_model=ApiResponse)
async def delete_tree(tree_id: str, db: Session = Depends(get_db)):
    """删除思维树"""
    db_tree = db.query(MindTreeDB).filter(MindTreeDB.id == tree_id).first()
    if not db_tree:
        raise HTTPException(status_code=404, detail="思维树不存在")

    try:
        # 先删除关联的边
        db.query(MindEdgeDB).filter(MindEdgeDB.tree_id == tree_id).delete()

        # 再删除关联的节点
        db.query(MindNodeDB).filter(MindNodeDB.tree_id == tree_id).delete()

        # 删除文件关联
        db.query(TreeSourceFileDB).filter(TreeSourceFileDB.tree_id == tree_id).delete()

        # 最后删除思维树
        db.delete(db_tree)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"删除失败: {str(e)}"
        )

    return ApiResponse(
        success=True,
        message="思维树删除成功"
    )

@router.post("/{tree_id}/nodes", response_model=ApiResponse)
async def add_node(tree_id: str, node_data: dict, db: Session = Depends(get_db)):
    """添加节点"""
    db_tree = db.query(MindTreeDB).filter(MindTreeDB.id == tree_id).first()
    if not db_tree:
        raise HTTPException(status_code=404, detail="思维树不存在")

    node_id = str(uuid.uuid4())
    db_node = MindNodeDB(
        id=node_id,
        tree_id=tree_id,
        label=node_data.get("label", "新节点"),
        description=node_data.get("description", ""),
        type=node_data.get("type", "concept"),
        level=node_data.get("level", 1),
        position_x=node_data.get("position", {}).get("x", 0),
        position_y=node_data.get("position", {}).get("y", 0),
        metadata_json=node_data.get("metadata", {})
    )
    db.add(db_node)
    db.commit()

    return ApiResponse(success=True, message="节点添加成功", data={"id": node_id})

@router.put("/{tree_id}/nodes/{node_id}", response_model=ApiResponse)
async def update_node(tree_id: str, node_id: str, node_data: dict, db: Session = Depends(get_db)):
    """更新节点"""
    db_node = db.query(MindNodeDB).filter(
        MindNodeDB.id == node_id,
        MindNodeDB.tree_id == tree_id
    ).first()
    if not db_node:
        raise HTTPException(status_code=404, detail="节点不存在")

    if "label" in node_data:
        db_node.label = node_data["label"]
    if "description" in node_data:
        db_node.description = node_data["description"]
    if "type" in node_data:
        db_node.type = node_data["type"]
    if "level" in node_data:
        db_node.level = node_data["level"]
    if "position" in node_data:
        db_node.position_x = node_data["position"].get("x", db_node.position_x)
        db_node.position_y = node_data["position"].get("y", db_node.position_y)

    db.commit()

    return ApiResponse(success=True, message="节点更新成功")

@router.delete("/{tree_id}/nodes/{node_id}", response_model=ApiResponse)
async def delete_node(tree_id: str, node_id: str, db: Session = Depends(get_db)):
    """删除节点"""
    db_node = db.query(MindNodeDB).filter(
        MindNodeDB.id == node_id,
        MindNodeDB.tree_id == tree_id
    ).first()
    if not db_node:
        raise HTTPException(status_code=404, detail="节点不存在")

    # 同时删除相关的边
    db.query(MindEdgeDB).filter(
        (MindEdgeDB.source_node_id == node_id) | (MindEdgeDB.target_node_id == node_id)
    ).delete()

    db.delete(db_node)
    db.commit()

    return ApiResponse(success=True, message="节点删除成功")

@router.post("/{tree_id}/edges", response_model=ApiResponse)
async def add_edge(tree_id: str, edge_data: dict, db: Session = Depends(get_db)):
    """添加连接"""
    db_tree = db.query(MindTreeDB).filter(MindTreeDB.id == tree_id).first()
    if not db_tree:
        raise HTTPException(status_code=404, detail="思维树不存在")

    edge_id = str(uuid.uuid4())
    db_edge = MindEdgeDB(
        id=edge_id,
        tree_id=tree_id,
        source_node_id=edge_data.get("source"),
        target_node_id=edge_data.get("target"),
        label=edge_data.get("label", ""),
        type=edge_data.get("type", "relates")
    )
    db.add(db_edge)
    db.commit()

    return ApiResponse(success=True, message="连接添加成功", data={"id": edge_id})

@router.delete("/{tree_id}/edges/{edge_id}", response_model=ApiResponse)
async def delete_edge(tree_id: str, edge_id: str, db: Session = Depends(get_db)):
    """删除连接"""
    db_edge = db.query(MindEdgeDB).filter(
        MindEdgeDB.id == edge_id,
        MindEdgeDB.tree_id == tree_id
    ).first()
    if not db_edge:
        raise HTTPException(status_code=404, detail="连接不存在")

    db.delete(db_edge)
    db.commit()

    return ApiResponse(success=True, message="连接删除成功")
