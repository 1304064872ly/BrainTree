/**
 * 生成唯一 ID
 * 使用时间戳 + 随机数确保唯一性
 */
export const generateId = (): string => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}
