"""
AI 模型配置 API 路由模块
========================

本模块提供 AI 模型配置的管理接口，负责：
1. 获取当前 AI 配置（API Key 脱敏返回）
2. 更新 AI 配置（支持热更新）
3. 测试 AI 配置连接

API 接口：
- GET /api/config - 获取当前配置
- PUT /api/config - 更新配置
- POST /api/config/test - 测试连接

安全特性：
- API Key 在返回时进行脱敏处理（sk-****xxxx）
- 只有用户主动更新时才会修改 API Key
- 测试连接时使用真实 Key，但不返回给前端

配置存储：
- 配置信息存储在 ai_config 表中
- 系统只保留一条配置记录（最新的配置）
- 支持运行时热更新，无需重启服务
"""

# ============================================================
# 第一部分：导入依赖
# ============================================================
from fastapi import (                 # FastAPI 核心组件
    APIRouter,    # 路由定义
    Depends,      # 依赖注入
    HTTPException # HTTP 异常
)
from sqlalchemy.orm import Session    # 数据库会话

# 导入核心组件
from app.core.database import get_db  # 数据库会话依赖注入
from app.core.security import (       # 安全工具
    mask_api_key,      # API Key 脱敏
    validate_api_key   # API 连接验证
)

# 导入数据模型
from app.models.db_models import AIConfigDB  # AI 配置数据库模型
from app.models.schemas import (
    AIConfigResponse,  # 配置响应模型
    AIConfigUpdate,    # 配置更新请求模型
    AIConfigTest,      # 配置测试请求模型
    ApiResponse        # 通用响应模型
)

# ============================================================
# 第二部分：创建路由实例
# ============================================================
router = APIRouter()


# ============================================================
# 第三部分：API 路由
# ============================================================

@router.get("", response_model=ApiResponse[AIConfigResponse])
async def get_config(db: Session = Depends(get_db)):
    """
    获取当前 AI 配置（API Key 脱敏）

    从数据库读取当前的 AI 模型配置。
    API Key 会进行脱敏处理，只显示前3位和后4位。

    Args:
        db: 数据库会话（依赖注入）

    Returns:
        ApiResponse[AIConfigResponse]: 包含配置信息的响应
            - id: 配置记录 ID
            - provider: AI 服务商名称
            - apiKey: 脱敏后的 API Key（如 sk-****a398）
            - apiBase: 自定义 API 地址
            - model: 模型名称
            - updatedAt: 更新时间

    使用场景：
        - 前端设置页面加载时获取当前配置
        - 显示当前使用的 AI 模型信息

    注意：
    - 如果数据库中没有配置，返回默认值
    - API Key 已脱敏，不会泄露完整密钥
    """
    # 从数据库查询配置（只有一条记录）
    config = db.query(AIConfigDB).first()

    if not config:
        # 数据库中没有配置，返回默认值
        return ApiResponse(
            success=True,
            data=AIConfigResponse(
                id=0,
                provider="deepseek",      # 默认服务商
                apiKey="****",            # 脱敏显示
                apiBase="",               # 空表示使用默认地址
                model="deepseek-chat",    # 默认模型
                updatedAt=None
            )
        )

    # 返回配置（API Key 已脱敏）
    return ApiResponse(
        success=True,
        data=AIConfigResponse(**config.to_dict(mask_key=True))
    )


@router.put("", response_model=ApiResponse[AIConfigResponse])
async def update_config(
    update: AIConfigUpdate,
    db: Session = Depends(get_db)
):
    """
    更新 AI 配置

    更新 AI 模型的配置信息，支持：
    - 切换服务商（deepseek/openai/claude/zhipu）
    - 更新 API Key
    - 更新自定义 API 地址
    - 更新模型名称

    Args:
        update: 配置更新请求
            - provider: AI 服务商名称（可选）
            - apiKey: API Key（可选，空值表示不更新）
            - apiBase: 自定义 API 地址（可选）
            - model: 模型名称（可选）
        db: 数据库会话（依赖注入）

    Returns:
        ApiResponse[AIConfigResponse]: 更新后的配置（API Key 脱敏）

    使用场景：
        - 前端设置页面保存配置
        - 切换 AI 服务商
        - 更新 API Key

    注意：
    - 所有字段都是可选的，只更新提供的字段
    - apiKey 为空时不会更新已有的 Key（保护已有配置）
    - 更新后会自动热更新 AIAnalyzer 配置
    - 配置立即生效，无需重启服务
    """
    # 查询现有配置
    config = db.query(AIConfigDB).first()

    if not config:
        # 首次创建配置
        config = AIConfigDB(
            provider=update.provider or "deepseek",
            api_key=update.apiKey or "",
            api_base=update.apiBase or "",
            model=update.model or "deepseek-chat"
        )
        db.add(config)
    else:
        # 更新已有配置
        # 只更新提供的字段（非 None 的字段）
        if update.provider is not None:
            config.provider = update.provider
        if update.apiKey is not None:
            config.api_key = update.apiKey
        if update.apiBase is not None:
            config.api_base = update.apiBase
        if update.model is not None:
            config.model = update.model

    # 保存到数据库
    db.commit()
    db.refresh(config)

    # 热更新 AIAnalyzer 配置
    # 使新配置立即生效，无需重启服务
    try:
        from app.services.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer()
        analyzer.reload_config_from_db(db)
    except Exception as e:
        # 热更新失败不影响配置保存
        print(f"[WARNING] 热更新 AIAnalyzer 失败: {e}")

    # 返回更新后的配置（API Key 已脱敏）
    return ApiResponse(
        success=True,
        data=AIConfigResponse(**config.to_dict(mask_key=True)),
        message="配置已保存"
    )


@router.post("/test", response_model=ApiResponse[dict])
async def test_config(test: AIConfigTest):
    """
    测试 AI 配置连接

    通过发送一个最小化的请求来验证 API 配置是否有效。
    支持测试所有服务商的 API。

    Args:
        test: 配置测试请求
            - provider: AI 服务商名称
            - apiKey: API Key
            - apiBase: 自定义 API 地址（可选）
            - model: 模型名称

    Returns:
        ApiResponse[dict]: 测试结果
            - valid (bool): 是否有效
            - message (str): 描述信息

    使用场景：
        - 前端设置页面的"测试连接"按钮
        - 保存配置前验证 API Key 是否有效

    注意：
    - 测试时会发送一个真实的 API 请求
    - 不会返回完整的 API Key
    - 测试结果包含详细的错误信息（如果失败）
    """
    # 调用验证函数
    result = await validate_api_key(
        provider=test.provider,
        api_key=test.apiKey,
        api_base=test.apiBase,
        model=test.model
    )

    # 根据验证结果返回响应
    if result["valid"]:
        return ApiResponse(success=True, data=result, message=result["message"])
    else:
        return ApiResponse(success=False, error=result["message"])
