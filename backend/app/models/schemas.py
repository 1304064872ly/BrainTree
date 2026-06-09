from datetime import datetime
from typing import List, Optional, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

class SourceFile(BaseModel):
    id: str
    name: str
    type: str  # pdf, docx, txt
    size: int
    uploadedAt: datetime = Field(default_factory=datetime.now)
    content: Optional[str] = None

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }

class MindNode(BaseModel):
    id: str
    label: str
    description: str = ""
    type: str = "concept"  # concept, topic, detail, example
    level: int = 1
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MindEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str = ""
    type: str = "relates"  # contains, relates, depends, examples

class MindTree(BaseModel):
    id: str
    name: str
    description: str = ""
    sourceFiles: List[str] = Field(default_factory=list)
    nodes: List[MindNode] = Field(default_factory=list)
    edges: List[MindEdge] = Field(default_factory=list)
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }

class MindTreeCreate(BaseModel):
    name: str
    description: Optional[str] = None

class AnalyzeRequest(BaseModel):
    fileIds: List[str]

class RefineRequest(BaseModel):
    treeId: str
    feedback: str


class AIConfigResponse(BaseModel):
    """AI 配置响应（API Key 已脱敏）"""
    id: int
    provider: str
    apiKey: str  # 脱敏后的 key
    apiBase: str = ""
    model: str
    updatedAt: Optional[str] = None


class AIConfigUpdate(BaseModel):
    """AI 配置更新请求"""
    provider: str = "deepseek"
    apiKey: Optional[str] = None  # 空值表示不更新
    apiBase: Optional[str] = None
    model: Optional[str] = None


class AIConfigTest(BaseModel):
    """AI 配置测试请求"""
    provider: str
    apiKey: str
    apiBase: Optional[str] = ""
    model: str


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[str] = None
