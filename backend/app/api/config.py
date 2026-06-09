"""AI 模型配置 API"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import mask_api_key, validate_api_key
from app.models.db_models import AIConfigDB
from app.models.schemas import (
    AIConfigResponse, AIConfigUpdate, AIConfigTest, ApiResponse
)

router = APIRouter()


@router.get("", response_model=ApiResponse[AIConfigResponse])
async def get_config(db: Session = Depends(get_db)):
    """获取当前 AI 配置（API Key 脱敏）"""
    config = db.query(AIConfigDB).first()

    if not config:
        # 如果数据库中没有配置，返回默认值
        return ApiResponse(
            success=True,
            data=AIConfigResponse(
                id=0,
                provider="deepseek",
                apiKey="****",
                apiBase="",
                model="deepseek-chat",
                updatedAt=None
            )
        )

    return ApiResponse(
        success=True,
        data=AIConfigResponse(**config.to_dict(mask_key=True))
    )


@router.put("", response_model=ApiResponse[AIConfigResponse])
async def update_config(
    update: AIConfigUpdate,
    db: Session = Depends(get_db)
):
    """更新 AI 配置"""
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
        if update.provider is not None:
            config.provider = update.provider
        if update.apiKey is not None:
            config.api_key = update.apiKey
        if update.apiBase is not None:
            config.api_base = update.apiBase
        if update.model is not None:
            config.model = update.model

    db.commit()
    db.refresh(config)

    # 热更新 AIAnalyzer 配置
    try:
        from app.services.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer()
        analyzer.reload_config_from_db(db)
    except Exception as e:
        print(f"[WARNING] 热更新 AIAnalyzer 失败: {e}")

    return ApiResponse(
        success=True,
        data=AIConfigResponse(**config.to_dict(mask_key=True)),
        message="配置已保存"
    )


@router.post("/test", response_model=ApiResponse[dict])
async def test_config(test: AIConfigTest):
    """测试 AI 配置连接"""
    result = await validate_api_key(
        provider=test.provider,
        api_key=test.apiKey,
        api_base=test.apiBase,
        model=test.model
    )

    if result["valid"]:
        return ApiResponse(success=True, data=result, message=result["message"])
    else:
        return ApiResponse(success=False, error=result["message"])
