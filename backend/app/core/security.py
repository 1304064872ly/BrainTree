"""
安全工具模块
===========

本模块提供与安全相关的工具函数，包括：
1. API Key 脱敏处理（保护敏感信息）
2. API 连接验证（测试配置是否有效）

使用场景：
- 前端显示 API Key 时进行脱敏，避免泄露
- 用户在设置页面配置 API Key 后，测试连接是否有效

支持的 AI 服务商：
- DeepSeek（OpenAI 兼容格式）
- OpenAI
- Claude
- 智谱 AI（OpenAI 兼容格式）

主要函数：
- mask_api_key(): API Key 脱敏
- validate_api_key(): 测试 API 连接
"""

# ============================================================
# 第一部分：导入依赖
# ============================================================
import httpx                # 异步 HTTP 客户端
from typing import Optional  # 类型注解


def mask_api_key(key: str) -> str:
    """
    对 API Key 进行脱敏处理

    保留 API Key 的前3位和后4位，中间用 **** 替代。
    这样用户可以识别是哪个 Key，但不会泄露完整信息。

    Args:
        key: 原始 API Key

    Returns:
        str: 脱敏后的 API Key

    示例：
        mask_api_key("sk-1234567890abcdef1234")  # 返回 "sk-****1234"
        mask_api_key("abc")                       # 返回 "****"
        mask_api_key("")                          # 返回 "****"

    使用场景：
        - API 返回配置信息时脱敏
        - 日志输出时脱敏
        - 前端显示当前配置时脱敏
    """
    # 如果 Key 为空或太短，直接返回 ****
    if not key or len(key) <= 7:
        return "****"
    # 保留前3位和后4位，中间用 **** 替代
    return f"{key[:3]}****{key[-4:]}"


async def validate_api_key(
    provider: str,
    api_key: str,
    api_base: Optional[str] = None,
    model: Optional[str] = None
) -> dict:
    """
    测试 API 连接是否有效

    通过发送一个最小化的请求来验证 API Key 是否有效。
    支持四种 AI 服务商的 API 验证。

    Args:
        provider: AI 服务商名称（deepseek/openai/claude/zhipu/xiaomi）
        api_key: API 密钥
        api_base: API 基础 URL（可选，使用默认值）
        model: 模型名称（可选，使用默认值）

    Returns:
        dict: 验证结果
            - valid (bool): 是否有效
            - message (str): 描述信息

    示例：
        result = await validate_api_key("deepseek", "sk-xxx")
        # 返回: {"valid": True, "message": "连接成功"}

        result = await validate_api_key("deepseek", "invalid-key")
        # 返回: {"valid": False, "message": "API 返回 401: ..."}

    使用场景：
        - 设置页面的"测试连接"按钮
        - 保存配置前验证 API Key 是否有效
    """
    # 检查 API Key 是否为空
    if not api_key:
        return {"valid": False, "message": "API Key 不能为空"}

    try:
        # 根据服务商分发到对应的测试方法
        if provider == "deepseek":
            # DeepSeek 使用 OpenAI 兼容格式
            return await _test_openai_compatible(
                api_base or "https://api.deepseek.com",
                api_key,
                model or "deepseek-chat"
            )
        elif provider == "openai":
            # OpenAI 使用标准格式
            return await _test_openai_compatible(
                api_base or "https://api.openai.com/v1",
                api_key,
                model or "gpt-3.5-turbo"
            )
        elif provider == "claude":
            # Claude 使用不同的 API 格式
            return await _test_claude(
                api_base or "https://api.anthropic.com/v1",
                api_key,
                model or "claude-3-sonnet-20240229"
            )
        elif provider == "zhipu":
            # 智谱 AI 使用 OpenAI 兼容格式
            return await _test_openai_compatible(
                api_base or "https://open.bigmodel.cn/api/paas/v4",
                api_key,
                model or "glm-4"
            )
        elif provider == "xiaomi":
            # 小米 MiMo 使用 OpenAI 兼容格式，但端点需要 /v1 前缀
            return await _test_xiaomi(
                api_base or "https://token-plan-cn.xiaomimimo.com",
                api_key,
                model or "mimo-v2.5-pro"
            )
        else:
            return {"valid": False, "message": f"不支持的服务商: {provider}"}
    except Exception as e:
        # 网络错误或其他异常
        return {"valid": False, "message": f"连接失败: {str(e)}"}


async def _test_openai_compatible(api_base: str, api_key: str, model: str) -> dict:
    """
    测试 OpenAI 兼容接口

    适用于：DeepSeek、OpenAI、智谱 AI
    这些服务商使用相同的 API 格式（/chat/completions）

    Args:
        api_base: API 基础 URL
        api_key: API 密钥
        model: 模型名称

    Returns:
        dict: 验证结果

    测试方法：
        发送一个最小化的请求（max_tokens=5），检查返回状态码
        - 200: 连接成功
        - 401: 认证失败（API Key 无效）
        - 其他: 服务异常
    """
    # 构建请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"  # Bearer Token 认证
    }

    # 发送测试请求
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_base}/chat/completions",  # API 端点
            headers=headers,
            json={
                "model": model,                                    # 模型名称
                "messages": [{"role": "user", "content": "Hi"}],  # 最小化消息
                "max_tokens": 5                                    # 最小化输出
            }
        )

        # 根据状态码判断结果
        if response.status_code == 200:
            return {"valid": True, "message": "连接成功"}
        else:
            # 提取错误信息（最多200字符）
            error_text = response.text[:200]
            return {"valid": False, "message": f"API 返回 {response.status_code}: {error_text}"}


async def _test_claude(api_base: str, api_key: str, model: str) -> dict:
    """
    测试 Claude API

    Claude API 使用不同的格式：
    - 端点: /messages（不是 /chat/completions）
    - 认证: x-api-key 头部（不是 Authorization）
    - 需要: anthropic-version 头部

    Args:
        api_base: API 基础 URL
        api_key: API 密钥
        model: 模型名称

    Returns:
        dict: 验证结果
    """
    # 构建请求头（Claude 使用不同的认证方式）
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,                    # Claude 专用认证头部
        "anthropic-version": "2023-06-01"       # API 版本（必需）
    }

    # 发送测试请求
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_base}/messages",  # Claude API 端点（不是 /chat/completions）
            headers=headers,
            json={
                "model": model,                                    # 模型名称
                "max_tokens": 5,                                   # 最小化输出
                "messages": [{"role": "user", "content": "Hi"}]   # 消息列表
            }
        )

        # 根据状态码判断结果
        if response.status_code == 200:
            return {"valid": True, "message": "连接成功"}
        else:
            # 提取错误信息（最多200字符）
            error_text = response.text[:200]
            return {"valid": False, "message": f"API 返回 {response.status_code}: {error_text}"}


async def _test_xiaomi(api_base: str, api_key: str, model: str) -> dict:
    """
    测试小米 MiMo API

    小米 MiMo 使用 OpenAI 兼容格式，但端点需要 /v1 前缀。

    Args:
        api_base: API 基础 URL
        api_key: API 密钥
        model: 模型名称

    Returns:
        dict: 验证结果
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_base}/v1/chat/completions",
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
