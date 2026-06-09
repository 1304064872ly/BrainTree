import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.schemas import AnalyzeRequest, RefineRequest, MindTree, MindNode, MindEdge, ApiResponse
from app.models.db_models import MindTreeDB, MindNodeDB, MindEdgeDB, SourceFileDB, TreeSourceFileDB
from app.core.database import get_db
from app.services.ai_analyzer import AIAnalyzer
from app.services.file_converter import FileConverter
from app.services.relation_detector import RelationDetector

router = APIRouter()


async def convert_file_to_markdown(converter: FileConverter, file: SourceFileDB) -> str:
    """将文件转换为 Markdown 格式"""
    if not file.content:
        return ""

    try:
        content_bytes = file.content.encode('utf-8') if isinstance(file.content, str) else file.content
        return await converter.convert_to_markdown(file.name, content_bytes)
    except Exception as e:
        print(f"警告: 文件 {file.name} 转换失败: {e}")
        return file.content or ""


def create_tree_in_db(db: Session, tree_data: dict, file_ids: List[str],
                      group_name: str = None) -> MindTreeDB:
    """在数据库中创建思维树及其节点和边"""
    tree_id = str(uuid.uuid4())

    # 使用分组名称或分析结果的标题
    tree_name = group_name or tree_data.get("title", "未命名思维树")

    db_tree = MindTreeDB(
        id=tree_id,
        name=tree_name,
        description=tree_data.get("summary", ""),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.add(db_tree)
    db.flush()

    # 关联文件
    for file_id in file_ids:
        db_tree_file = TreeSourceFileDB(tree_id=tree_id, file_id=file_id)
        db.add(db_tree_file)

    # 创建节点
    nodes_map = {}
    for concept in tree_data.get("concepts", []):
        node_id = str(uuid.uuid4())
        db_node = MindNodeDB(
            id=node_id,
            tree_id=tree_id,
            label=concept["name"],
            description=concept.get("description", ""),
            type=concept.get("type", "concept"),
            level=concept.get("level", 1),
            position_x=len(nodes_map) * 100,
            position_y=0,
            metadata_json={"source_file": concept.get("source_file", "")}
        )
        db.add(db_node)
        nodes_map[concept["name"]] = node_id

    # 创建连接关系
    for relation in tree_data.get("relations", []):
        source_id = nodes_map.get(relation.get("source"))
        target_id = nodes_map.get(relation.get("target"))

        if source_id and target_id:
            db_edge = MindEdgeDB(
                id=str(uuid.uuid4()),
                tree_id=tree_id,
                source_node_id=source_id,
                target_node_id=target_id,
                label=relation.get("label", "相关"),
                type=relation.get("type", "relates")
            )
            db.add(db_edge)

    return db_tree


def build_tree_response(db_tree: MindTreeDB) -> MindTree:
    """构建思维树响应"""
    return MindTree(
        id=db_tree.id,
        name=db_tree.name,
        description=db_tree.description or "",
        sourceFiles=[sf.file_id for sf in db_tree.source_files],
        nodes=[
            {
                "id": n.id,
                "label": n.label,
                "description": n.description or "",
                "type": n.type,
                "level": n.level,
                "position": {"x": n.position_x, "y": n.position_y},
                "metadata": n.metadata_json or {}
            }
            for n in db_tree.nodes
        ],
        edges=[
            {
                "id": e.id,
                "source": e.source_node_id,
                "target": e.target_node_id,
                "label": e.label or "",
                "type": e.type
            }
            for e in db_tree.edges
        ],
        createdAt=db_tree.created_at,
        updatedAt=db_tree.updated_at
    )


@router.post("", response_model=ApiResponse[MindTree])
async def analyze_files(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    分析文件生成思维树

    - 单文件：直接分析
    - 多文件：智能分组分析
    """
    # 验证文件是否存在
    files = []
    for file_id in request.fileIds:
        db_file = db.query(SourceFileDB).filter(SourceFileDB.id == file_id).first()
        if not db_file:
            raise HTTPException(status_code=404, detail=f"文件 {file_id} 不存在")
        files.append(db_file)

    # 获取文件内容并转换为 Markdown
    converter = FileConverter()
    markdown_contents = []

    for f in files:
        md_content = await convert_file_to_markdown(converter, f)
        if md_content:
            markdown_contents.append(md_content)

    if not markdown_contents:
        raise HTTPException(status_code=400, detail="文件内容为空")

    analyzer = AIAnalyzer()

    # 单文件分析：直接分析
    if len(files) == 1:
        try:
            analysis_result = await analyzer.analyze(markdown_contents[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI分析失败: {str(e)}")

        # 创建思维树
        db_tree = create_tree_in_db(db, analysis_result, request.fileIds)
        db.commit()
        db.refresh(db_tree)

        return ApiResponse(
            success=True,
            data=build_tree_response(db_tree),
            message="思维树生成成功"
        )

    # 多文件分析：智能分组分析
    try:
        # 第1步：单文件独立分析，提取关键词
        print(f"开始多文件分析，共 {len(files)} 个文件")
        file_analyses = []
        for i, (md_content, file) in enumerate(zip(markdown_contents, files)):
            print(f"分析文件 {i+1}/{len(files)}: {file.name}")
            result = await analyzer.analyze_single_file(md_content, file.name)
            result["file_id"] = file.id
            result["file_name"] = file.name
            file_analyses.append(result)

        # 第2步：检测相关性，进行分组
        print("检测文件相关性...")
        detector = RelationDetector(similarity_threshold=0.3)
        detection_result = detector.detect_relations(file_analyses)
        groups = detection_result["groups"]
        print(f"分组完成：{len(groups)} 组")

        # 第3步：对每个分组进行综合分析
        created_trees = []
        for group in groups:
            group_file_indices = group["file_indices"]
            group_file_analyses = [file_analyses[i] for i in group_file_indices]
            group_file_ids = group["file_ids"]

            # 生成分组名称
            group_name = detector.generate_group_name(group, file_analyses)
            print(f"分析分组: {group_name} ({len(group_file_analyses)} 个文件)")

            # 综合分析
            group_result = await analyzer.analyze_group(group_file_analyses, group)

            # 创建思维树
            db_tree = create_tree_in_db(db, group_result, group_file_ids, group_name)
            created_trees.append(db_tree)

        db.commit()

        # 刷新所有创建的树
        for tree in created_trees:
            db.refresh(tree)

        # 返回所有生成的树
        tree_responses = [build_tree_response(tree) for tree in created_trees]

        # 如果只有一个分组，直接返回该树（保持向后兼容）
        if len(tree_responses) == 1:
            return ApiResponse(
                success=True,
                data=tree_responses[0],
                message="思维树生成成功"
            )

        # 多个分组，返回第一棵树，但消息中提示有多棵树
        # 前端需要调用 /api/trees 获取所有树
        return ApiResponse(
            success=True,
            data=tree_responses[0],
            message=f"多文件分析完成，共生成 {len(tree_responses)} 棵思维树，请刷新页面查看所有树"
        )

    except Exception as e:
        print(f"多文件分析失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI分析失败: {str(e)}")


@router.post("/refine", response_model=ApiResponse[MindTree])
async def refine_tree(request: RefineRequest, db: Session = Depends(get_db)):
    """优化现有思维树"""
    db_tree = db.query(MindTreeDB).filter(MindTreeDB.id == request.treeId).first()
    if not db_tree:
        raise HTTPException(status_code=404, detail="思维树不存在")

    # 使用AI优化思维树
    analyzer = AIAnalyzer()
    try:
        refined_result = await analyzer.refine(db_tree, request.feedback)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI优化失败: {str(e)}")

    # 更新节点
    existing_nodes = {n.label: n for n in db_tree.nodes}
    new_nodes_map = {}

    for concept in refined_result.get("concepts", []):
        if concept["name"] in existing_nodes:
            # 更新现有节点
            node = existing_nodes[concept["name"]]
            node.description = concept.get("description", node.description)
            node.type = concept.get("type", node.type)
            node.level = concept.get("level", node.level)
            new_nodes_map[concept["name"]] = node.id
        else:
            # 创建新节点
            node_id = str(uuid.uuid4())
            db_node = MindNodeDB(
                id=node_id,
                tree_id=request.treeId,
                label=concept["name"],
                description=concept.get("description", ""),
                type=concept.get("type", "concept"),
                level=concept.get("level", 1),
                position_x=len(new_nodes_map) * 100,
                position_y=0
            )
            db.add(db_node)
            new_nodes_map[concept["name"]] = node_id

    # 更新连接
    # 先删除旧连接
    db.query(MindEdgeDB).filter(MindEdgeDB.tree_id == request.treeId).delete()

    for relation in refined_result.get("relations", []):
        source_id = new_nodes_map.get(relation["source"])
        target_id = new_nodes_map.get(relation["target"])

        if source_id and target_id:
            db_edge = MindEdgeDB(
                id=str(uuid.uuid4()),
                tree_id=request.treeId,
                source_node_id=source_id,
                target_node_id=target_id,
                label=relation.get("label", "相关"),
                type=relation.get("type", "relates")
            )
            db.add(db_edge)

    db_tree.updated_at = datetime.now()
    db.commit()
    db.refresh(db_tree)

    return ApiResponse(
        success=True,
        data=build_tree_response(db_tree),
        message="思维树优化成功"
    )
