from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import relationship
from app.core.database import Base

class SourceFileDB(Base):
    """文件表"""
    __tablename__ = "source_files"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(10), nullable=False)  # pdf, docx, txt
    size = Column(Integer, nullable=False)
    content = Column(MEDIUMTEXT, nullable=True)  # 提取的文本内容（使用 MEDIUMTEXT 支持更大内容）
    uploaded_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "size": self.size,
            "content": self.content,
            "uploadedAt": self.uploaded_at.isoformat() if self.uploaded_at else None
        }

class MindTreeDB(Base):
    """思维树表"""
    __tablename__ = "mind_trees"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联的节点和边
    nodes = relationship("MindNodeDB", back_populates="tree", cascade="all, delete-orphan")
    edges = relationship("MindEdgeDB", back_populates="tree", cascade="all, delete-orphan")
    source_files = relationship("TreeSourceFileDB", back_populates="tree", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "sourceFiles": [sf.file_id for sf in self.source_files],
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None
        }

class MindNodeDB(Base):
    """节点表"""
    __tablename__ = "mind_nodes"

    id = Column(String(36), primary_key=True, index=True)
    tree_id = Column(String(36), ForeignKey("mind_trees.id"), nullable=False)
    label = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(20), default="concept")  # concept, topic, detail, example
    level = Column(Integer, default=1)
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    metadata_json = Column(JSON, nullable=True)

    tree = relationship("MindTreeDB", back_populates="nodes")

    def to_dict(self):
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description or "",
            "type": self.type,
            "level": self.level,
            "position": {"x": self.position_x, "y": self.position_y},
            "metadata": self.metadata_json or {}
        }

class MindEdgeDB(Base):
    """边表（节点关系）"""
    __tablename__ = "mind_edges"

    id = Column(String(36), primary_key=True, index=True)
    tree_id = Column(String(36), ForeignKey("mind_trees.id"), nullable=False)
    source_node_id = Column(String(36), ForeignKey("mind_nodes.id"), nullable=False)
    target_node_id = Column(String(36), ForeignKey("mind_nodes.id"), nullable=False)
    label = Column(String(255), nullable=True)
    type = Column(String(20), default="relates")  # contains, relates, depends, examples

    tree = relationship("MindTreeDB", back_populates="edges")
    source_node = relationship("MindNodeDB", foreign_keys=[source_node_id])
    target_node = relationship("MindNodeDB", foreign_keys=[target_node_id])

    def to_dict(self):
        return {
            "id": self.id,
            "source": self.source_node_id,
            "target": self.target_node_id,
            "label": self.label or "",
            "type": self.type
        }

class TreeSourceFileDB(Base):
    """思维树与文件的关联表"""
    __tablename__ = "tree_source_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tree_id = Column(String(36), ForeignKey("mind_trees.id"), nullable=False)
    file_id = Column(String(36), ForeignKey("source_files.id"), nullable=False)

    tree = relationship("MindTreeDB", back_populates="source_files")
    file = relationship("SourceFileDB")


class AIConfigDB(Base):
    """AI 模型配置表"""
    __tablename__ = "ai_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False, default="deepseek")
    api_key = Column(String(255), nullable=False, default="")
    api_base = Column(String(255), nullable=True, default="")
    model = Column(String(100), nullable=False, default="deepseek-chat")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self, mask_key: bool = True):
        """转为字典，mask_key=True 时对 API Key 脱敏"""
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
        """脱敏 API Key：保留前3位和后4位，中间用 **** 替代"""
        if not key or len(key) <= 7:
            return "****"
        return f"{key[:3]}****{key[-4:]}"
