"""
Pydantic 数据模型定义模块
========================

本模块定义了 BrainTree 项目的 API 请求和响应数据模型。
使用 Pydantic 库进行数据验证和序列化。

模型分类：
1. 数据模型：SourceFile, MindNode, MindEdge, MindTree
2. 请求模型：MindTreeCreate, AnalyzeRequest, RefineRequest
3. 配置模型：AIConfigResponse, AIConfigUpdate, AIConfigTest
4. 响应模型：ApiResponse（泛型）

Pydantic 特点：
- 自动数据验证
- 自动类型转换
- JSON 序列化/反序列化
- 支持默认值和可选字段
- 支持嵌套模型

使用示例：
    # 创建请求模型
    request = AnalyzeRequest(fileIds=["file1", "file2"])

    # 创建响应模型
    response = ApiResponse(success=True, data=mind_tree)
"""

# ============================================================
# 第一部分：导入依赖
# ============================================================
from datetime import datetime                          # 日期时间处理
from typing import List, Optional, Dict, Any, Generic, TypeVar  # 类型注解
from pydantic import BaseModel, Field                  # Pydantic 基础组件

# 泛型类型变量（用于 ApiResponse）
T = TypeVar("T")


# ============================================================
# 第二部分：数据模型
# ============================================================

class SourceFile(BaseModel):
    """
    源文件数据模型

    表示用户上传的文件信息。

    字段说明：
    - id: 文件唯一标识（UUID 格式）
    - name: 原始文件名
    - type: 文件类型（pdf/docx/txt/md）
    - size: 文件大小（字节）
    - uploadedAt: 上传时间
    - content: 提取的文本内容（可选，列表接口不返回）

    使用场景：
    - 文件上传接口的响应
    - 文件列表接口的响应
    - 文件详情接口的响应
    """
    id: str                        # 文件唯一标识
    name: str                      # 文件名
    type: str                      # 文件类型：pdf, docx, txt
    size: int                      # 文件大小（字节）
    uploadedAt: datetime = Field(default_factory=datetime.now)  # 上传时间
    content: Optional[str] = None  # 文本内容（可选）

    # Pydantic 配置
    model_config = {
        "json_encoders": {
            # 将 datetime 类型序列化为 ISO 8601 格式
            datetime: lambda v: v.isoformat()
        }
    }


class MindNode(BaseModel):
    """
    思维树节点数据模型

    表示思维树中的一个节点（概念、主题、知识点）。

    字段说明：
    - id: 节点唯一标识（UUID 格式）
    - label: 节点标签（显示名称）
    - description: 节点描述（详细说明）
    - type: 节点类型（concept/topic/detail/example）
    - level: 节点层级（1=核心概念，4=示例）
    - position: 节点在图谱中的位置坐标
    - metadata: 元数据（存储额外信息）

    节点类型说明：
    - concept: 核心概念/主题（level 1）
    - topic: 分类/子主题（level 2）
    - detail: 具体知识点（level 3）
    - example: 示例/代码（level 4）
    """
    id: str                                                        # 节点唯一标识
    label: str                                                     # 节点标签
    description: str = ""                                          # 节点描述
    type: str = "concept"                                          # 节点类型
    level: int = 1                                                 # 节点层级
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})  # 位置坐标
    metadata: Dict[str, Any] = Field(default_factory=dict)         # 元数据


class MindEdge(BaseModel):
    """
    思维树边数据模型

    表示思维树中两个节点之间的关系。

    字段说明：
    - id: 边唯一标识（UUID 格式）
    - source: 源节点 ID
    - target: 目标节点 ID
    - label: 关系标签（如"包含"、"关联"）
    - type: 关系类型（contains/relates/depends/examples）

    关系类型说明：
    - contains: 包含关系（父节点包含子节点）
    - relates: 关联关系（节点之间有相关性）
    - depends: 依赖关系（一个节点依赖另一个节点）
    - examples: 示例关系（一个节点是另一个节点的示例）
    """
    id: str                        # 边唯一标识
    source: str                    # 源节点 ID
    target: str                    # 目标节点 ID
    label: str = ""                # 关系标签
    type: str = "relates"          # 关系类型


class MindTree(BaseModel):
    """
    思维树数据模型

    表示一个完整的思维树，包含节点和关系。

    字段说明：
    - id: 思维树唯一标识（UUID 格式）
    - name: 思维树名称
    - description: 描述信息
    - sourceFiles: 关联的源文件 ID 列表
    - nodes: 节点列表
    - edges: 关系列表
    - createdAt: 创建时间
    - updatedAt: 更新时间

    使用场景：
    - 思维树列表接口的响应
    - 思维树详情接口的响应
    - AI 分析接口的响应
    """
    id: str                                                        # 思维树唯一标识
    name: str                                                      # 思维树名称
    description: str = ""                                          # 描述信息
    sourceFiles: List[str] = Field(default_factory=list)           # 关联的源文件 ID
    nodes: List[MindNode] = Field(default_factory=list)            # 节点列表
    edges: List[MindEdge] = Field(default_factory=list)            # 关系列表
    createdAt: datetime = Field(default_factory=datetime.now)      # 创建时间
    updatedAt: datetime = Field(default_factory=datetime.now)      # 更新时间

    # Pydantic 配置
    model_config = {
        "json_encoders": {
            # 将 datetime 类型序列化为 ISO 8601 格式
            datetime: lambda v: v.isoformat()
        }
    }


# ============================================================
# 第三部分：请求模型
# ============================================================

class MindTreeCreate(BaseModel):
    """
    创建思维树请求模型

    用于 POST /api/trees 接口。

    字段说明：
    - name: 思维树名称（必填）
    - description: 描述信息（可选）
    """
    name: str                                # 思维树名称（必填）
    description: Optional[str] = None        # 描述信息（可选）


class AnalyzeRequest(BaseModel):
    """
    AI 分析请求模型

    用于 POST /api/analyze 接口。

    字段说明：
    - fileIds: 待分析的文件 ID 列表
    """
    fileIds: List[str]  # 文件 ID 列表


class RefineRequest(BaseModel):
    """
    思维树优化请求模型

    用于 POST /api/analyze/refine 接口。

    字段说明：
    - treeId: 待优化的思维树 ID
    - feedback: 用户反馈文本
    """
    treeId: str        # 思维树 ID
    feedback: str      # 用户反馈


# ============================================================
# 第四部分：配置相关模型
# ============================================================

class AIConfigResponse(BaseModel):
    """
    AI 配置响应模型

    用于 GET /api/config 接口的响应。
    API Key 已脱敏处理。

    字段说明：
    - id: 配置记录 ID
    - provider: AI 服务商名称
    - apiKey: 脱敏后的 API Key
    - apiBase: 自定义 API 地址
    - model: 模型名称
    - updatedAt: 更新时间
    """
    id: int                              # 配置记录 ID
    provider: str                        # AI 服务商名称
    apiKey: str                          # 脱敏后的 API Key
    apiBase: str = ""                    # 自定义 API 地址
    model: str                           # 模型名称
    updatedAt: Optional[str] = None      # 更新时间


class AIConfigUpdate(BaseModel):
    """
    AI 配置更新请求模型

    用于 PUT /api/config 接口。

    字段说明：
    - provider: AI 服务商名称（可选）
    - apiKey: API Key（可选，空值表示不更新）
    - apiBase: 自定义 API 地址（可选）
    - model: 模型名称（可选）

    注意：
    - 所有字段都是可选的
    - 只更新提供的字段
    - apiKey 为空时不会更新已有的 Key
    """
    provider: str = "deepseek"           # AI 服务商名称
    apiKey: Optional[str] = None         # API Key（空值表示不更新）
    apiBase: Optional[str] = None        # 自定义 API 地址
    model: Optional[str] = None          # 模型名称


class AIConfigTest(BaseModel):
    """
    AI 配置测试请求模型

    用于 POST /api/config/test 接口。

    字段说明：
    - provider: AI 服务商名称
    - apiKey: API Key
    - apiBase: 自定义 API 地址（可选）
    - model: 模型名称
    """
    provider: str                        # AI 服务商名称
    apiKey: str                          # API Key
    apiBase: Optional[str] = ""          # 自定义 API 地址
    model: str                           # 模型名称


# ============================================================
# 第五部分：通用响应模型
# ============================================================

class ApiResponse(BaseModel, Generic[T]):
    """
    通用 API 响应模型

    所有 API 接口都使用这个统一的响应格式。
    使用泛型支持不同类型的 data 字段。

    字段说明：
    - success: 请求是否成功
    - data: 响应数据（类型由泛型参数决定）
    - message: 成功消息（可选）
    - error: 错误信息（可选）

    使用示例：
        # 成功响应
        response = ApiResponse(success=True, data=mind_tree)

        # 错误响应
        response = ApiResponse(success=False, error="文件不存在")
    """
    success: bool                        # 请求是否成功
    data: Optional[T] = None             # 响应数据
    message: Optional[str] = None        # 成功消息
    error: Optional[str] = None          # 错误信息
