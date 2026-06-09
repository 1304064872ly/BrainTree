"""安全工具函数 - API Key 脱敏和验证"""

import httpx
from typing import Optional


def mask_api_key(key: str) -> str:
    """对 API Key 进行脱敏处理

    示例:
        sk-1234567890abcdef1234 -> sk-1234
    """
    if not key or len(key) <= 7:
        return "****"
    return f"{key[:3]}****{key[-4:]}"


async def validate_api_key(
    provider: str,
    api_key: str,
    api_base: Optional[str] = None,
    model: Optional[str] = None
) -> dict:
    """测试 API 连接是否有效

    Returns:
        {"valid": True/False, "message": "描述"}
    """
    if not api_key:
        return {"valid": False, "message": "API Key 不能为空"}

    try:
        if provider == "deepseek":
            return await _test_openai_compatible(
                api_base or "https://api.deepseek.com",
                api_key,
                model or "deepseek-chat"
            )
        elif provider == "openai":
            return await _test_openai_compatible(
                api_base or "https://api.openai.com/v1",
                api_key,
                model or "gpt-3.5-turbo"
            )
        elif provider == "claude":
            return await _test_claude(
                api_base or "https://api.anthropic.com/v1",
                api_key,
                model or "claude-3-sonnet-20240229"
            )
        elif provider == "zhipu":
            return await _test_openai_compatible(
                api_base or "https://open.bigmodel.cn/api/paas/v4",
                api_key,
                model or "glm-4"
            )
        else:
            return {"valid": False, "message": f"不支持的服务商: {provider}"}
    except Exception as e:
        return {"valid": False, "message": f"连接失败: {str(e)}"}


async def _test_openai_compatible(api_base: str, api_key: str, model: str) -> dict:
    """测试 OpenAI 兼容接口（DeepSeek/OpenAI/智谱）"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            }
        )

        if response.status_code == 200:
            return {"valid": True, "message": "连接成功"}
        else:
            error_text = response.text[:200]
            return {"valid": False, "message": f"API 返回 {response.status_code}: {error_text}"}


async def _test_claude(api_base: str, api_key: str, model: str) -> dict:
    """测试 Claude API"""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_base}/messages",
            headers=headers,
            json={
                "model": model,
                "max_tokens": 5,
                "messages": [{"role": "user", "content": "Hi"}]
            }
        )

        if response.status_code == 200:
            return {"valid": True, "message": "连接成功"}
        else:
            error_text = response.text[:200]
            return {"valid": False, "message": f"API 返回 {response.status_code}: {error_text}"}
