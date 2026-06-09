/**
 * 节点类型配置
 * 统一管理节点类型的颜色和标签
 */
export const NODE_TYPE_CONFIG: Record<string, { color: string; label: string }> = {
  concept: { color: 'blue', label: '概念' },
  topic: { color: 'green', label: '主题' },
  detail: { color: 'orange', label: '细节' },
  example: { color: 'purple', label: '示例' },
}

/**
 * 节点类型选项（用于 Select 组件）
 */
export const NODE_TYPE_OPTIONS = Object.entries(NODE_TYPE_CONFIG).map(([value, { label }]) => ({
  value,
  label,
}))

/**
 * 节点层级配置
 */
export const NODE_LEVEL_CONFIG: Record<number, { label: string }> = {
  1: { label: '1 - 核心概念' },
  2: { label: '2 - 主要主题' },
  3: { label: '3 - 细节' },
  4: { label: '4 - 示例' },
}

/**
 * 节点层级选项（用于 Select 组件）
 */
export const NODE_LEVEL_OPTIONS = Object.entries(NODE_LEVEL_CONFIG).map(([value, { label }]) => ({
  value: Number(value),
  label,
}))
