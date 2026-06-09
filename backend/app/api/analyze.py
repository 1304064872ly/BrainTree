"""
AI 分析 API 路由模块
===================

本模块提供 AI 分析相关的 API 接口，负责：
1. 分析文件生成思维树
2. 根据用户反馈优化思维树

API 接口：
- POST /api/analyze - 分析文件生成思维树
- POST /api/analyze/refine - 优化现有思维树

分析流程：
1. 单文件分析：直接调用 AI 分析
2. 多文件分析：
   a. 单文件独立分析，提取关键词
   b. 检测文件相关性，进行分组
   c. 对每个分组进行综合分析
   d. 为每个分组创建思维树

技术细节：
- 使用 FileConverter 将文件转换为 Markdown 格式
- 使用 AIAnalyzer 调用 LLM 进行分析
- 使用 RelationDetector 检测文件相关性
- 使用 SQLAlchemy 进行数据库操作
"""

# ============================================================
# 第一部分：导入依赖
# ============================================================
import uuid                           # UUID 生成
from datetime import datetime         # 日期时间处理
from typing import List               # 类型注解
from fastapi import (                 # FastAPI 核心组件
    APIRouter,    # 路由定义
    HTTPException, # HTTP 异常
    Depends       # 依赖注入
)
from sqlalchemy.orm import Session    # 数据库会话

# 导入数据模型
from app.models.schemas import (
    AnalyzeRequest,   # 分析请求
    RefineRequest,    # 优化请求
    MindTree,         # 思维树响应
    MindNode,         # 节点
    MindEdge,         # 边
    ApiResponse       # 通用响应
)
from app.models.db_models import (
    MindTreeDB,          # 思维树数据库模型
    MindNodeDB,          # 节点数据库模型
    MindEdgeDB,          # 边数据库模型
    SourceFileDB,        # 文件数据库模型
    TreeSourceFileDB     # 思维树-文件关联数据库模型
)

# 导入核心组件
from app.core.database import get_db  # 数据库会话依赖注入

# 导入服务层
from app.services.ai_analyzer import AIAnalyzer          # AI 分析器
from app.services.file_converter import FileConverter    # 文件转换器
from app.services.relation_detector import RelationDetector  # 相关性检测器

# ============================================================
# 第二部分：创建路由实例
# ============================================================
router = APIRouter()


# ============================================================
# 第三部分：辅助函数
# ============================================================

async def convert_file_to_markdown(converter: FileConverter, file: SourceFileDB) -> str:
    """
    将文件转换为 Markdown 格式

    使用 FileConverter 将文件内容转换为结构化的 Markdown 格式，
    以便 AI 更好地理解文档结构。

    Args:
        converter: 文件转换器实例
        file: 文件数据库对象

    Returns:
        str: Markdown 格式的内容

    注意：
    - 如果文件内容为空，返回空字符串
    - 如果转换失败，返回原始文本内容
    """
    # 检查文件内容是否为空
    if not file.content:
        return ""

    try:
        # 将内容编码为字节流（转换器需要字节流输入）
        content_bytes = file.content.encode('utf-8') if isinstance(file.content, str) else file.content
        # 调用转换器进行转换
        return await converter.convert_to_markdown(file.name, content_bytes)
    except Exception as e:
        # 转换失败时，返回原始文本内容
        print(f"警告: 文件 {file.name} 转换失败: {e}")
        return file.content or ""


def create_tree_in_db(db: Session, tree_data: dict, file_ids: List[str],
                      group_name: str = None) -> MindTreeDB:
    """
    在数据库中创建思维树及其节点和边

    将 AI 分析结果持久化到数据库，包括：
    1. 创建思维树记录
    2. 关联源文件
    3. 创建节点记录
    4. 创建边（关系）记录

    Args:
        db: 数据库会话
        tree_data: AI 分析结果数据
            - title: 思维树标题
            - summary: 内容摘要
            - concepts: 概念节点列表
            - relations: 关系列表
        file_ids: 关联的源文件 ID 列表
        group_name: 分组名称（多文件分析时使用）

    Returns:
        MindTreeDB: 创建的思维树数据库对象
    """
    # 生成思维树唯一 ID
    tree_id = str(uuid.uuid4())

    # 使用分组名称或分析结果的标题
    tree_name = group_name or tree_data.get("title", "未命名思维树")

    # 创建思维树记录
    db_tree = MindTreeDB(
        id=tree_id,
        name=tree_name,
        description=tree_data.get("summary", ""),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.add(db_tree)
    db.flush()  # 刷新以获取 ID

    # 关联源文件
    for file_id in file_ids:
        db_tree_file = TreeSourceFileDB(tree_id=tree_id, file_id=file_id)
        db.add(db_tree_file)

    # 创建节点
    nodes_map = {}  # 节点名称 -> 节点 ID 的映射
    for concept in tree_data.get("concepts", []):
        node_id = str(uuid.uuid4())
        db_node = MindNodeDB(
            id=node_id,
            tree_id=tree_id,
            label=concept["name"],
            description=concept.get("description", ""),
            type=concept.get("type", "concept"),
            level=concept.get("level", 1),
            position_x=len(nodes_map) * 100,  # 简单的位置计算
            position_y=0,
            metadata_json={"source_file": concept.get("source_file", "")}  # 记录来源文件
        )
        db.add(db_node)
        nodes_map[concept["name"]] = node_id  # 记录映射关系

    # 创建连接关系
    for relation in tree_data.get("relations", []):
        # 根据节点名称查找节点 ID
        source_id = nodes_map.get(relation.get("source"))
        target_id = nodes_map.get(relation.get("target"))

        # 只有源节点和目标节点都存在时才创建关系
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
    """
    构建思维树响应对象

    将数据库对象转换为 API 响应对象。

    Args:
        db_tree: 思维树数据库对象

    Returns:
        MindTree: 思维树响应对象
    """
    return MindTree(
        id=db_tree.id,
        name=db_tree.name,
        description=db_tree.description or "",
        sourceFiles=[sf.file_id for sf in db_tree.source_files],  # 源文件 ID 列表
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
            for n in db_tree.nodes  # 遍历所有节点
        ],
        edges=[
            {
                "id": e.id,
                "source": e.source_node_id,
                "target": e.target_node_id,
                "label": e.label or "",
                "type": e.type
            }
            for e in db_tree.edges  # 遍历所有边
        ],
        createdAt=db_tree.created_at,
        updatedAt=db_tree.updated_at
    )


# ============================================================
# 第四部分：API 路由
# ============================================================

@router.post("", response_model=ApiResponse[MindTree])
async def analyze_files(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    分析文件生成思维树

    根据文件数量采用不同的分析策略：
    - 单文件：直接分析
    - 多文件：智能分组分析

    Args:
        request: 分析请求，包含文件 ID 列表
        db: 数据库会话（依赖注入）

    Returns:
        ApiResponse[MindTree]: 包含生成的思维树的响应

    Raises:
        HTTPException: 文件不存在或分析失败

    多文件分析流程：
    1. 单文件独立分析，提取关键词和概念
    2. 检测文件相关性，进行智能分组
    3. 对每个分组进行综合分析
    4. 为每个分组创建思维树
    """
    # ============================================================
    # 步骤1：验证文件是否存在
    # ============================================================
    files = []
    for file_id in request.fileIds:
        db_file = db.query(SourceFileDB).filter(SourceFileDB.id == file_id).first()
        if not db_file:
            raise HTTPException(status_code=404, detail=f"文件 {file_id} 不存在")
        files.append(db_file)

    # ============================================================
    # 步骤2：获取文件内容并转换为 Markdown
    # ============================================================
    converter = FileConverter()
    markdown_contents = []

    for f in files:
        md_content = await convert_file_to_markdown(converter, f)
        if md_content:
            markdown_contents.append(md_content)

    # 检查是否有有效内容
    if not markdown_contents:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 创建 AI 分析器
    analyzer = AIAnalyzer()

    # ============================================================
    # 步骤3：单文件分析
    # ============================================================
    if len(files) == 1:
        try:
            # 直接调用 AI 分析
            analysis_result = await analyzer.analyze(markdown_contents[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI分析失败: {str(e)}")

        # 在数据库中创建思维树
        db_tree = create_tree_in_db(db, analysis_result, request.fileIds)
        db.commit()  # 提交事务
        db.refresh(db_tree)  # 刷新对象以获取最新数据

        return ApiResponse(
            success=True,
            data=build_tree_response(db_tree),
            message="思维树生成成功"
        )

    # ============================================================
    # 步骤4：多文件分析
    # ============================================================
    try:
        # 第1步：单文件独立分析，提取关键词
        print(f"开始多文件分析，共 {len(files)} 个文件")
        file_analyses = []
        for i, (md_content, file) in enumerate(zip(markdown_contents, files)):
            print(f"分析文件 {i+1}/{len(files)}: {file.name}")
            # 分析单个文件
            result = await analyzer.analyze_single_file(md_content, file.name)
            # 记录文件信息
            result["file_id"] = file.id
            result["file_name"] = file.name
            file_analyses.append(result)

        # 第2步：检测相关性，进行分组
        print("检测文件相关性...")
        detector = RelationDetector(similarity_threshold=0.3)  # 相似度阈值
        detection_result = detector.detect_relations(file_analyses)
        groups = detection_result["groups"]
        print(f"分组完成：{len(groups)} 组")

        # 第3步：对每个分组进行综合分析
        created_trees = []
        for group in groups:
            # 获取分组内的文件信息
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

        # 提交事务
        db.commit()

        # 刷新所有创建的树
        for tree in created_trees:
            db.refresh(tree)

        # 构建响应
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
        # 多文件分析失败
        print(f"多文件分析失败: {e}")
        import traceback
        traceback.print_exc()  # 打印详细错误堆栈
        raise HTTPException(status_code=500, detail=f"AI分析失败: {str(e)}")


@router.post("/refine", response_model=ApiResponse[MindTree])
async def refine_tree(request: RefineRequest, db: Session = Depends(get_db)):
    """
    优化现有思维树

    根据用户反馈优化思维树结构。
    支持的操作：
    - 添加新概念
    - 修改现有概念
    - 删除概念
    - 调整关系

    Args:
        request: 优化请求，包含思维树 ID 和用户反馈
        db: 数据库会话（依赖注入）

    Returns:
        ApiResponse[MindTree]: 优化后的思维树

    Raises:
        HTTPException: 思维树不存在或优化失败

    优化流程：
    1. 获取当前思维树
    2. 调用 AI 进行优化
    3. 更新节点（保留现有节点，添加新节点）
    4. 更新关系（删除旧关系，创建新关系）
    5. 保存到数据库
    """
    # ============================================================
    # 步骤1：获取思维树
    # ============================================================
    db_tree = db.query(MindTreeDB).filter(MindTreeDB.id == request.treeId).first()
    if not db_tree:
        raise HTTPException(status_code=404, detail="思维树不存在")

    # ============================================================
    # 步骤2：使用 AI 优化思维树
    # ============================================================
    analyzer = AIAnalyzer()
    try:
        refined_result = await analyzer.refine(db_tree, request.feedback)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI优化失败: {str(e)}")

    # ============================================================
    # 步骤3：更新节点
    # ============================================================
    # 获取现有节点（按标签名称索引）
    existing_nodes = {n.label: n for n in db_tree.nodes}
    new_nodes_map = {}  # 节点名称 -> 节点 ID 的映射

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

    # ============================================================
    # 步骤4：更新连接
    # ============================================================
    # 先删除旧连接
    db.query(MindEdgeDB).filter(MindEdgeDB.tree_id == request.treeId).delete()

    # 创建新连接
    for relation in refined_result.get("relations", []):
        # 根据节点名称查找节点 ID
        source_id = new_nodes_map.get(relation["source"])
        target_id = new_nodes_map.get(relation["target"])

        # 只有源节点和目标节点都存在时才创建关系
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

    # ============================================================
    # 步骤5：保存到数据库
    # ============================================================
    db_tree.updated_at = datetime.now()  # 更新时间
    db.commit()  # 提交事务
    db.refresh(db_tree)  # 刷新对象

    return ApiResponse(
        success=True,
        data=build_tree_response(db_tree),
        message="思维树优化成功"
    )
