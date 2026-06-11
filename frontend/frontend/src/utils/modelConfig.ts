/** AI 模型配置常量 */

export interface ModelOption {
  value: string
  label: string
}

export interface ProviderConfig {
  name: string
  label: string
  defaultApiBase: string
  models: ModelOption[]
}

/** 支持的 AI 服务商及其模型列表 */
export const PROVIDER_CONFIGS: Record<string, ProviderConfig> = {
  deepseek: {
    name: 'deepseek',
    label: 'DeepSeek',
    defaultApiBase: 'https://api.deepseek.com',
    models: [
      { value: 'deepseek-chat', label: 'DeepSeek-V3 通用模型' },
      { value: 'deepseek-coder', label: 'DeepSeek 代码专用模型' },
      { value: 'deepseek-reasoner', label: 'DeepSeek-R1 推理模型' },
      { value: 'deepseek-v3', label: 'DeepSeek-V3 最新版' },
      { value: 'deepseek-r1', label: 'DeepSeek-R1' },
      { value: 'deepseek-v4-flash', label: 'DeepSeek-V4 Flash 快速模型' },
    ],
  },
  openai: {
    name: 'openai',
    label: 'OpenAI',
    defaultApiBase: 'https://api.openai.com/v1',
    models: [
      { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
      { value: 'gpt-4', label: 'GPT-4' },
      { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
      { value: 'gpt-4o', label: 'GPT-4o' },
    ],
  },
  claude: {
    name: 'claude',
    label: 'Claude',
    defaultApiBase: 'https://api.anthropic.com/v1',
    models: [
      { value: 'claude-3-sonnet-20240229', label: 'Claude 3 Sonnet' },
      { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
      { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku' },
    ],
  },
  zhipu: {
    name: 'zhipu',
    label: '智谱 AI',
    defaultApiBase: 'https://open.bigmodel.cn/api/paas/v4',
    models: [
      { value: 'glm-4', label: 'GLM-4' },
      { value: 'glm-4-flash', label: 'GLM-4 Flash' },
      { value: 'glm-4v', label: 'GLM-4V (多模态)' },
    ],
  },
  xiaomi: {
    name: 'xiaomi',
    label: '小米 MiMo',
    defaultApiBase: 'https://token-plan-cn.xiaomimimo.com',
    models: [
      { value: 'mimo-v2.5-pro', label: 'MiMo V2.5 Pro (高性能)' },
      { value: 'mimo-v2.5', label: 'MiMo V2.5 (标准版)' },
    ],
  },
}

/** 获取服务商列表（用于下拉选择） */
export const getProviderOptions = (): ModelOption[] => {
  return Object.values(PROVIDER_CONFIGS).map(config => ({
    value: config.name,
    label: config.label,
  }))
}

/** 获取指定服务商的模型列表 */
export const getModelOptions = (provider: string): ModelOption[] => {
  return PROVIDER_CONFIGS[provider]?.models || []
}

/** 获取服务商的默认 API Base */
export const getDefaultApiBase = (provider: string): string => {
  return PROVIDER_CONFIGS[provider]?.defaultApiBase || ''
}
