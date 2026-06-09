import os
from fastapi import APIRouter
from app.models.schemas import ApiResponse
from app.services.ai_analyzer import DEEPSEEK_MODELS
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# 支持的 LLM 服务及其模型
SUPPORTED_PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "models": DEEPSEEK_MODELS
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": {
            "gpt-3.5-turbo": "GPT-3.5 Turbo",
            "gpt-4": "GPT-4",
            "gpt-4-turbo": "GPT-4 Turbo",
            "gpt-4o": "GPT-4o"
        }
    },
    "claude": {
        "name": "Claude",
        "base_url": "https://api.anthropic.com/v1",
        "models": {
            "claude-3-sonnet-20240229": "Claude 3 Sonnet",
            "claude-3-opus-20240229": "Claude 3 Opus",
            "claude-3-haiku-20240307": "Claude 3 Haiku"
        }
    },
    "zhipu": {
        "name": "智谱 AI",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": {
            "glm-4": "GLM-4",
            "glm-4-flash": "GLM-4 Flash",
            "glm-4v": "GLM-4V (多模态)"
        }
    }
}

@router.get("/providers", response_model=ApiResponse)
async def get_providers():
    """获取支持的 LLM 服务商列表"""
    providers = [
        {"id": k, "name": v["name"], "base_url": v["base_url"]}
        for k, v in SUPPORTED_PROVIDERS.items()
    ]
    return ApiResponse(success=True, data=providers)

@router.get("/models/{provider}", response_model=ApiResponse)
async def get_models(provider: str):
    """获取指定服务商的模型列表"""
    if provider not in SUPPORTED_PROVIDERS:
        return ApiResponse(
            success=False,
            error=f"不支持的服务商: {provider}"
        )

    provider_info = SUPPORTED_PROVIDERS[provider]
    models = [
        {"id": k, "name": v}
        for k, v in provider_info["models"].items()
    ]

    return ApiResponse(
        success=True,
        data={
            "provider": provider,
            "provider_name": provider_info["name"],
            "models": models
        }
    )

@router.get("/models", response_model=ApiResponse)
async def get_all_models():
    """获取所有支持的模型"""
    current_provider = os.getenv("LLM_PROVIDER", "deepseek")
    current_model = os.getenv("LLM_MODEL", "deepseek-chat")

    all_models = []
    for provider_id, provider_info in SUPPORTED_PROVIDERS.items():
        for model_id, model_name in provider_info["models"].items():
            all_models.append({
                "provider": provider_id,
                "provider_name": provider_info["name"],
                "model_id": model_id,
                "model_name": model_name,
                "is_current": provider_id == current_provider and model_id == current_model
            })

    return ApiResponse(
        success=True,
        data={
            "current_provider": current_provider,
            "current_model": current_model,
            "models": all_models
        }
    )
