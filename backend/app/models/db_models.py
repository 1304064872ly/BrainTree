"""
数据库模型定义模块
=================

本模块定义了 BrainTree 项目的所有数据库表结构。
使用 SQLAlchemy ORM 框架，将 Python 类映射到数据库表。

数据表结构：
1. source_files - 文件表：存储上传的文件信息和提取的文本内容
2. mind_trees - 思维树表：存储思维树的基本信息
3. mind_nodes - 节点表：存储思维树的节点（概念、主题等）
4. mind_edges - 边表：存储节点之间的关系
5. tree_source_files - 关联表：思维树与源文件的多对多关系
6. ai_config - 配置表：存储 AI 模型配置信息

表关系：
- mind_trees 1:N mind_nodes（一个思维树有多个节点）
- mind_trees 1:N mind_edges（一个思维树有多个关系）
- mind_trees N:N source_files（通过 tree_source_files 关联）
- mind_nodes 1:N mind_edges（节点作为关系的起点或终点）

技术细节：
- 使用 UUID 作为主键（String(36)）
- 使用 MEDIUMTEXT 支持大文本内容
- 使用 JSON 类型存储元数据
- 使用 relationship 定义表关系
"""

# ============================================================
# 第一部分：导入依赖
# ============================================================
from datetime import datetime                    # 日期时间处理
from sqlalchemy import (                          # SQLAlchemy 核心组件
    Column,      # 列定义
    String,      # 字符串类型
    Integer,     # 整数类型
    Text,        # 长文本类型
    DateTime,    # 日期时间类型
    ForeignKey,  # 外键约束
    JSON         # JSON 类型
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT  # MySQL 特有的中等文本类型
from sqlalchemy.orm import relationship           # 表关系定义
from app.core.database import Base                # ORM 基类


# ============================================================
# 第二部分：文件表
# ============================================================

class SourceFileDB(Base):
    """
    文件表 - 存储上传的文件信息

    记录用户上传的文件的基本信息和提取的文本内容。
    文本内容会被提取出来用于 AI 分析。

    字段说明：
    - id: 文件唯一标识（UUID 格式）
    - name: 原始文件名
    - type: 文件类型（pdf/docx/txt/md）
    - size: 文件大小（字节）
    - content: 提取的文本内容（使用 MEDIUMTEXT 支持大内容）
    - uploaded_at: 上传时间

    关联关系：
    - 与 mind_trees 通过 tree_source_files 关联（多对多）
    """
    __tablename__ = "source_files"  # 数据库表名

    # 主键：UUID 格式的唯一标识
    id = Column(String(36), primary_key=True, index=True)

    # 文件名：原始上传的文件名
    name = Column(String(255), nullable=False)

    # 文件类型：pdf, docx, txt, md, markdown
    type = Column(String(10), nullable=False)

    # 文件大小：字节数
    size = Column(Integer, nullable=False)

    # 提取的文本内容
    # 使用 MEDIUMTEXT 而不是 TEXT，因为大文件可能超过 TEXT 的限制
    # MEDIUMTEXT 最大支持 16MB 文本
    content = Column(MEDIUMTEXT, nullable=True)

    # 上传时间：默认为当前时间
    uploaded_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        """
        转换为字典格式

        Returns:
            dict: 包含所有字段的字典，时间格式为 ISO 8601
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "size": self.size,
            "content": self.content,
            "uploadedAt": self.uploaded_at.isoformat() if self.uploaded_at else None
        }


# ============================================================
# 第三部分：思维树表
# ============================================================

class MindTreeDB(Base):
    """
    思维树表 - 存储思维树的基本信息

    思维树是项目的核心数据结构，包含多个节点和关系。
    每个思维树对应一个知识主题。

    字段说明：
    - id: 思维树唯一标识（UUID 格式）
    - name: 思维树名称
    - description: 描述信息
    - created_at: 创建时间
    - updated_at: 更新时间（自动更新）

    关联关系：
    - 1:N mind_nodes（一个思维树有多个节点）
    - 1:N mind_edges（一个思维树有多个关系）
    - N:N source_files（通过 tree_source_files 关联）
    """
    __tablename__ = "mind_trees"  # 数据库表名

    # 主键：UUID 格式的唯一标识
    id = Column(String(36), primary_key=True, index=True)

    # 思维树名称
    name = Column(String(255), nullable=False)

    # 描述信息（可选）
    description = Column(Text, nullable=True)

    # 创建时间：默认为当前时间
    created_at = Column(DateTime, default=datetime.now)

    # 更新时间：默认为当前时间，更新时自动更新
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # ============================================================
    # 关联关系定义
    # ============================================================

    # 与节点的关系（1:N）
    # cascade="all, delete-orphan" 表示删除思维树时，同时删除所有节点
    nodes = relationship("MindNodeDB", back_populates="tree", cascade="all, delete-orphan")

    # 与边的关系（1:N）
    edges = relationship("MindEdgeDB", back_populates="tree", cascade="all, delete-orphan")

    # 与源文件的关系（N:N，通过关联表）
    source_files = relationship("TreeSourceFileDB", back_populates="tree", cascade="all, delete-orphan")

    def to_dict(self):
        """
        转换为字典格式

        Returns:
            dict: 包含所有字段的字典，包括关联的节点、边和源文件
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "sourceFiles": [sf.file_id for sf in self.source_files],  # 源文件 ID 列表
            "nodes": [node.to_dict() for node in self.nodes],         # 节点列表
            "edges": [edge.to_dict() for edge in self.edges],         # 边列表
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None
        }


# ============================================================
# 第四部分：节点表
# ============================================================

class MindNodeDB(Base):
    """
    节点表 - 存储思维树的节点

    节点是思维树的基本单元，代表一个概念、主题或知识点。
    每个节点有类型和层级属性，用于构建树状结构。

    字段说明：
    - id: 节点唯一标识（UUID 格式）
    - tree_id: 所属思维树 ID（外键）
    - label: 节点标签（显示名称）
    - description: 节点描述（详细说明）
    - type: 节点类型（concept/topic/detail/example）
    - level: 节点层级（1=核心概念，2=主要主题，3=细节，4=示例）
    - position_x, position_y: 节点在图谱中的位置坐标
    - metadata_json: 元数据（JSON 格式，存储额外信息）

    节点类型说明：
    - concept: 核心概念/主题（level 1）
    - topic: 分类/子主题（level 2）
    - detail: 具体知识点（level 3）
    - example: 示例/代码（level 4）
    """
    __tablename__ = "mind_nodes"  # 数据库表名

    # 主键：UUID 格式的唯一标识
    id = Column(String(36), primary_key=True, index=True)

    # 外键：所属思维树 ID
    tree_id = Column(String(36), ForeignKey("mind_trees.id"), nullable=False)

    # 节点标签（显示名称）
    label = Column(String(255), nullable=False)

    # 节点描述（详细说明）
    description = Column(Text, nullable=True)

    # 节点类型
    # concept: 核心概念
    # topic: 主题
    # detail: 细节
    # example: 示例
    type = Column(String(20), default="concept")

    # 节点层级（1-4）
    # 1: 核心概念
    # 2: 主要主题
    # 3: 细节
    # 4: 示例
    level = Column(Integer, default=1)

    # 节点在图谱中的位置坐标
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)

    # 元数据（JSON 格式）
    # 可以存储额外信息，如颜色、图标、来源文件等
    metadata_json = Column(JSON, nullable=True)

    # 与思维树的关系（N:1）
    tree = relationship("MindTreeDB", back_populates="nodes")

    def to_dict(self):
        """
        转换为字典格式

        Returns:
            dict: 包含所有字段的字典
        """
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description or "",
            "type": self.type,
            "level": self.level,
            "position": {"x": self.position_x, "y": self.position_y},
            "metadata": self.metadata_json or {}
        }


# ============================================================
# 第五部分：边表（节点关系）
# ============================================================

class MindEdgeDB(Base):
    """
    边表 - 存储节点之间的关系

    边表示两个节点之间的关系，如"包含"、"关联"、"依赖"等。
    每条边连接一个源节点和一个目标节点。

    字段说明：
    - id: 边唯一标识（UUID 格式）
    - tree_id: 所属思维树 ID（外键）
    - source_node_id: 源节点 ID（外键）
    - target_node_id: 目标节点 ID（外键）
    - label: 关系标签（如"包含"、"关联"）
    - type: 关系类型（contains/relates/depends/examples）

    关系类型说明：
    - contains: 包含关系（父节点包含子节点）
    - relates: 关联关系（节点之间有相关性）
    - depends: 依赖关系（一个节点依赖另一个节点）
    - examples: 示例关系（一个节点是另一个节点的示例）
    """
    __tablename__ = "mind_edges"  # 数据库表名

    # 主键：UUID 格式的唯一标识
    id = Column(String(36), primary_key=True, index=True)

    # 外键：所属思维树 ID
    tree_id = Column(String(36), ForeignKey("mind_trees.id"), nullable=False)

    # 外键：源节点 ID
    source_node_id = Column(String(36), ForeignKey("mind_nodes.id"), nullable=False)

    # 外键：目标节点 ID
    target_node_id = Column(String(36), ForeignKey("mind_nodes.id"), nullable=False)

    # 关系标签（如"包含"、"关联"）
    label = Column(String(255), nullable=True)

    # 关系类型
    # contains: 包含关系
    # relates: 关联关系
    # depends: 依赖关系
    # examples: 示例关系
    type = Column(String(20), default="relates")

    # ============================================================
    # 关联关系定义
    # ============================================================

    # 与思维树的关系（N:1）
    tree = relationship("MindTreeDB", back_populates="edges")

    # 与源节点的关系（N:1）
    source_node = relationship("MindNodeDB", foreign_keys=[source_node_id])

    # 与目标节点的关系（N:1）
    target_node = relationship("MindNodeDB", foreign_keys=[target_node_id])

    def to_dict(self):
        """
        转换为字典格式

        Returns:
            dict: 包含所有字段的字典
        """
        return {
            "id": self.id,
            "source": self.source_node_id,  # 源节点 ID
            "target": self.target_node_id,  # 目标节点 ID
            "label": self.label or "",       # 关系标签
            "type": self.type                # 关系类型
        }


# ============================================================
# 第六部分：思维树与文件的关联表
# ============================================================

class TreeSourceFileDB(Base):
    """
    思维树与文件的关联表

    实现思维树和源文件的多对多关系。
    一个思维树可以关联多个源文件，一个源文件也可以被多个思维树引用。

    字段说明：
    - id: 关联记录 ID（自增）
    - tree_id: 思维树 ID（外键）
    - file_id: 源文件 ID（外键）
    """
    __tablename__ = "tree_source_files"  # 数据库表名

    # 主键：自增整数
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 外键：思维树 ID
    tree_id = Column(String(36), ForeignKey("mind_trees.id"), nullable=False)

    # 外键：源文件 ID
    file_id = Column(String(36), ForeignKey("source_files.id"), nullable=False)

    # 关联关系
    tree = relationship("MindTreeDB", back_populates="source_files")
    file = relationship("SourceFileDB")


# ============================================================
# 第七部分：AI 模型配置表
# ============================================================

class AIConfigDB(Base):
    """
    AI 模型配置表

    存储用户在前端设置页面配置的 AI 模型参数。
    系统只保留一条配置记录（最新的配置）。

    字段说明：
    - id: 配置记录 ID（自增）
    - provider: AI 服务商名称（deepseek/openai/claude/zhipu）
    - api_key: API 密钥（加密存储或明文存储）
    - api_base: 自定义 API 地址（可选）
    - model: 模型名称
    - updated_at: 更新时间（自动更新）

    安全说明：
    - API Key 在返回给前端时会进行脱敏处理
    - to_dict(mask_key=True) 返回脱敏后的 Key
    - to_dict(mask_key=False) 返回原始 Key（仅内部使用）
    """
    __tablename__ = "ai_config"  # 数据库表名

    # 主键：自增整数
    id = Column(Integer, primary_key=True, autoincrement=True)

    # AI 服务商名称
    # 支持：deepseek, openai, claude, zhipu
    provider = Column(String(50), nullable=False, default="deepseek")

    # API 密钥
    api_key = Column(String(255), nullable=False, default="")

    # 自定义 API 地址（可选）
    # 留空使用服务商的默认地址
    api_base = Column(String(255), nullable=True, default="")

    # 模型名称
    model = Column(String(100), nullable=False, default="deepseek-chat")

    # 更新时间：默认为当前时间，更新时自动更新
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self, mask_key: bool = True):
        """
        转换为字典格式

        Args:
            mask_key: 是否对 API Key 进行脱敏处理
                - True: 返回脱敏后的 Key（默认，用于前端显示）
                - False: 返回原始 Key（仅内部使用）

        Returns:
            dict: 包含所有字段的字典
        """
        return {
            "id": self.id,
            "provider": self.provider,
            "apiKey": self._mask_key(self.api_key) if mask_key else self.api_key,
            "apiBase": self.api_base or "",
            "model": self.model,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def _mask_key(key: str) -> str:
        """
        脱敏 API Key

        保留前3位和后4位，中间用 **** 替代。
        这样用户可以识别是哪个 Key，但不会泄露完整信息。

        Args:
            key: 原始 API Key

        Returns:
            str: 脱敏后的 API Key

        示例：
            "sk-1234567890abcdef1234" -> "sk-****1234"
        """
        if not key or len(key) <= 7:
            return "****"
        return f"{key[:3]}****{key[-4:]}"
