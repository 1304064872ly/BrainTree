/**
 * API 服务模块
 * ============
 *
 * 本模块封装了所有与后端 API 的交互。
 * 使用 Axios 作为 HTTP 客户端，提供统一的 API 调用接口。
 *
 * API 模块分类：
 * 1. fileApi - 文件管理（上传、列表、详情、删除）
 * 2. treeApi - 思维树管理（CRUD 操作）
 * 3. analyzeApi - AI 分析（分析文件、优化思维树）
 * 4. exportApi - 导出功能（JSON、Markdown、CSV、图片、PDF）
 * 5. configApi - 配置管理（获取、更新、测试连接）
 *
 * 技术特点：
 * - 统一的请求拦截和响应处理
 * - 5分钟超时（AI 分析需要较长时间）
 * - 支持文件上传（multipart/form-data）
 * - 支持 Blob 响应（图片、PDF 导出）
 * - /api 前缀自动代理到后端
 */

// ============================================================
// 第一部分：导入依赖
// ============================================================
import axios from 'axios'  // HTTP 客户端
import { MindTree, SourceFile, ApiResponse } from '../types'  // 类型定义

// ============================================================
// 第二部分：创建 Axios 实例
// ============================================================

/**
 * Axios 实例
 *
 * 配置说明：
 * - baseURL: API 基础路径，所有请求都会加上这个前缀
 *   开发环境通过 Vite 代理转发到后端 localhost:8000
 * - timeout: 请求超时时间（5分钟）
 *   AI 分析可能需要较长时间，所以设置较长的超时
 */
const api = axios.create({
  baseURL: '/api',           // API 基础路径
  timeout: 300000,           // 5分钟超时（AI 分析需要较长时间）
})

// ============================================================
// 第三部分：文件管理 API
// ============================================================

/**
 * 文件管理 API
 *
 * 提供文件的上传、列表、详情、删除功能。
 */
export const fileApi = {
  /**
   * 上传文件
   *
   * @param file - 要上传的文件对象
   * @returns 上传成功后的文件信息
   *
   * 使用示例：
   *   const response = await fileApi.upload(file)
   *   console.log(response.data.id)  // 文件 ID
   */
  upload: async (file: File): Promise<ApiResponse<SourceFile>> => {
    // 创建 FormData 对象（multipart/form-data 格式）
    const formData = new FormData()
    formData.append('file', file)

    // 发送上传请求
    const response = await api.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',  // 文件上传必须使用此格式
      },
    })
    return response.data
  },

  /**
   * 获取文件列表
   *
   * @returns 文件列表（不包含 content 字段）
   *
   * 注意：列表接口不返回 content 字段（避免响应过大）
   */
  getList: async (): Promise<ApiResponse<SourceFile[]>> => {
    const response = await api.get('/files')
    return response.data
  },

  /**
   * 获取文件详情
   *
   * @param id - 文件 ID
   * @returns 文件详情（包含 content 字段）
   */
  getById: async (id: string): Promise<ApiResponse<SourceFile>> => {
    const response = await api.get(`/files/${id}`)
    return response.data
  },

  /**
   * 删除文件
   *
   * @param id - 文件 ID
   * @returns 删除结果
   */
  delete: async (id: string): Promise<ApiResponse<void>> => {
    const response = await api.delete(`/files/${id}`)
    return response.data
  },
}

// ============================================================
// 第四部分：思维树管理 API
// ============================================================

/**
 * 思维树管理 API
 *
 * 提供思维树的 CRUD 操作。
 */
export const treeApi = {
  /**
   * 创建思维树
   *
   * @param data - 思维树数据
   * @returns 创建的思维树
   */
  create: async (data: Partial<MindTree>): Promise<ApiResponse<MindTree>> => {
    const response = await api.post('/trees', data)
    return response.data
  },

  /**
   * 获取思维树列表
   *
   * @returns 思维树列表
   */
  getList: async (): Promise<ApiResponse<MindTree[]>> => {
    const response = await api.get('/trees')
    return response.data
  },

  /**
   * 获取思维树详情
   *
   * @param id - 思维树 ID
   * @returns 思维树详情（包含节点和边）
   */
  getById: async (id: string): Promise<ApiResponse<MindTree>> => {
    const response = await api.get(`/trees/${id}`)
    return response.data
  },

  /**
   * 更新思维树
   *
   * @param id - 思维树 ID
   * @param data - 更新数据
   * @returns 更新后的思维树
   */
  update: async (id: string, data: Partial<MindTree>): Promise<ApiResponse<MindTree>> => {
    const response = await api.put(`/trees/${id}`, data)
    return response.data
  },

  /**
   * 删除思维树
   *
   * @param id - 思维树 ID
   * @returns 删除结果
   */
  delete: async (id: string): Promise<ApiResponse<void>> => {
    const response = await api.delete(`/trees/${id}`)
    return response.data
  },
}

// ============================================================
// 第五部分：AI 分析 API
// ============================================================

/**
 * AI 分析 API
 *
 * 提供文件分析和思维树优化功能。
 */
export const analyzeApi = {
  /**
   * 分析文件生成思维树
   *
   * @param fileIds - 文件 ID 列表
   * @returns 生成的思维树
   *
   * 分析流程：
   * - 单文件：直接分析
   * - 多文件：智能分组分析
   */
  analyze: async (fileIds: string[]): Promise<ApiResponse<MindTree>> => {
    const response = await api.post('/analyze', { fileIds })
    return response.data
  },

  /**
   * 优化思维树
   *
   * @param treeId - 思维树 ID
   * @param feedback - 用户反馈
   * @returns 优化后的思维树
   */
  refine: async (treeId: string, feedback: string): Promise<ApiResponse<MindTree>> => {
    const response = await api.post('/analyze/refine', { treeId, feedback })
    return response.data
  },
}

// ============================================================
// 第六部分：导出 API
// ============================================================

/**
 * 导出 API
 *
 * 提供思维树的多种格式导出功能。
 */
export const exportApi = {
  /**
   * 导出为 JSON 格式
   *
   * @param treeId - 思维树 ID
   * @returns JSON 格式的思维树数据
   */
  toJson: async (treeId: string): Promise<ApiResponse<MindTree>> => {
    const response = await api.get(`/trees/${treeId}/export/json`)
    return response.data
  },

  /**
   * 导出为 Markdown 格式
   *
   * @param treeId - 思维树 ID
   * @returns Markdown 格式的文本
   */
  toMarkdown: async (treeId: string): Promise<ApiResponse<string>> => {
    const response = await api.get(`/trees/${treeId}/export/markdown`)
    return response.data
  },

  /**
   * 导出为 CSV 格式
   *
   * @param treeId - 思维树 ID
   * @returns CSV 格式的文本
   */
  toCsv: async (treeId: string): Promise<ApiResponse<string>> => {
    const response = await api.get(`/trees/${treeId}/export/csv`)
    return response.data
  },

  /**
   * 导出为图片格式
   *
   * @param treeId - 思维树 ID
   * @param format - 图片格式（png 或 svg）
   * @returns 图片 Blob 数据
   */
  toImage: async (treeId: string, format: 'png' | 'svg'): Promise<ApiResponse<Blob>> => {
    const response = await api.post(`/trees/${treeId}/export/image`, { format }, {
      responseType: 'blob',  // 指定响应类型为 Blob
    })
    return response.data
  },

  /**
   * 导出为 PDF 格式
   *
   * @param treeId - 思维树 ID
   * @returns PDF Blob 数据
   */
  toPdf: async (treeId: string): Promise<ApiResponse<Blob>> => {
    const response = await api.post(`/trees/${treeId}/export/pdf`, {}, {
      responseType: 'blob',  // 指定响应类型为 Blob
    })
    return response.data
  },
}

// ============================================================
// 第七部分：配置管理 API
// ============================================================

/**
 * AI 配置接口
 *
 * 定义 AI 模型配置的数据结构。
 */
export interface AIConfig {
  id: number        // 配置记录 ID
  provider: string  // AI 服务商名称
  apiKey: string    // API Key（脱敏后）
  apiBase: string   // 自定义 API 地址
  model: string     // 模型名称
  updatedAt: string | null  // 更新时间
}

/**
 * AI 配置更新接口
 *
 * 所有字段都是可选的，只更新提供的字段。
 */
export interface AIConfigUpdate {
  provider?: string  // AI 服务商名称
  apiKey?: string    // API Key
  apiBase?: string   // 自定义 API 地址
  model?: string     // 模型名称
}

/**
 * AI 配置测试接口
 *
 * 测试连接时需要提供完整的配置信息。
 */
export interface AIConfigTest {
  provider: string   // AI 服务商名称
  apiKey: string     // API Key
  apiBase?: string   // 自定义 API 地址
  model: string      // 模型名称
}

/**
 * 配置管理 API
 *
 * 提供 AI 配置的获取、更新、测试连接功能。
 */
export const configApi = {
  /**
   * 获取当前配置
   *
   * @returns AI 配置（API Key 已脱敏）
   */
  getConfig: async (): Promise<ApiResponse<AIConfig>> => {
    const response = await api.get('/config')
    return response.data
  },

  /**
   * 更新配置
   *
   * @param data - 配置更新数据
   * @returns 更新后的配置
   */
  updateConfig: async (data: AIConfigUpdate): Promise<ApiResponse<AIConfig>> => {
    const response = await api.put('/config', data)
    return response.data
  },

  /**
   * 测试连接
   *
   * @param data - 测试配置数据
   * @returns 测试结果（valid 和 message）
   */
  testConfig: async (data: AIConfigTest): Promise<ApiResponse<{ valid: boolean; message: string }>> => {
    const response = await api.post('/config/test', data)
    return response.data
  },
}

// ============================================================
// 第八部分：导出默认实例
// ============================================================

/**
 * 导出 Axios 实例
 *
 * 可以直接使用 api 实例进行自定义请求。
 */
export default api
