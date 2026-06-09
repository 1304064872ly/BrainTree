import axios from 'axios'
import { MindTree, SourceFile, ApiResponse } from '../types'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5分钟，多文件AI分析需要更长时间
})

// 文件相关API
export const fileApi = {
  upload: async (file: File): Promise<ApiResponse<SourceFile>> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  getList: async (): Promise<ApiResponse<SourceFile[]>> => {
    const response = await api.get('/files')
    return response.data
  },

  getById: async (id: string): Promise<ApiResponse<SourceFile>> => {
    const response = await api.get(`/files/${id}`)
    return response.data
  },

  delete: async (id: string): Promise<ApiResponse<void>> => {
    const response = await api.delete(`/files/${id}`)
    return response.data
  },
}

// 思维树相关API
export const treeApi = {
  create: async (data: Partial<MindTree>): Promise<ApiResponse<MindTree>> => {
    const response = await api.post('/trees', data)
    return response.data
  },

  getList: async (): Promise<ApiResponse<MindTree[]>> => {
    const response = await api.get('/trees')
    return response.data
  },

  getById: async (id: string): Promise<ApiResponse<MindTree>> => {
    const response = await api.get(`/trees/${id}`)
    return response.data
  },

  update: async (id: string, data: Partial<MindTree>): Promise<ApiResponse<MindTree>> => {
    const response = await api.put(`/trees/${id}`, data)
    return response.data
  },

  delete: async (id: string): Promise<ApiResponse<void>> => {
    const response = await api.delete(`/trees/${id}`)
    return response.data
  },
}

// AI分析相关API
export const analyzeApi = {
  analyze: async (fileIds: string[]): Promise<ApiResponse<MindTree>> => {
    const response = await api.post('/analyze', { fileIds })
    return response.data
  },

  refine: async (treeId: string, feedback: string): Promise<ApiResponse<MindTree>> => {
    const response = await api.post('/analyze/refine', { treeId, feedback })
    return response.data
  },
}

// 导出相关API
export const exportApi = {
  toJson: async (treeId: string): Promise<ApiResponse<MindTree>> => {
    const response = await api.get(`/trees/${treeId}/export/json`)
    return response.data
  },

  toMarkdown: async (treeId: string): Promise<ApiResponse<string>> => {
    const response = await api.get(`/trees/${treeId}/export/markdown`)
    return response.data
  },

  toCsv: async (treeId: string): Promise<ApiResponse<string>> => {
    const response = await api.get(`/trees/${treeId}/export/csv`)
    return response.data
  },

  toImage: async (treeId: string, format: 'png' | 'svg'): Promise<ApiResponse<Blob>> => {
    const response = await api.post(`/trees/${treeId}/export/image`, { format }, {
      responseType: 'blob',
    })
    return response.data
  },

  toPdf: async (treeId: string): Promise<ApiResponse<Blob>> => {
    const response = await api.post(`/trees/${treeId}/export/pdf`, {}, {
      responseType: 'blob',
    })
    return response.data
  },
}

// AI 配置相关 API
export interface AIConfig {
  id: number
  provider: string
  apiKey: string
  apiBase: string
  model: string
  updatedAt: string | null
}

export interface AIConfigUpdate {
  provider?: string
  apiKey?: string
  apiBase?: string
  model?: string
}

export interface AIConfigTest {
  provider: string
  apiKey: string
  apiBase?: string
  model: string
}

export const configApi = {
  getConfig: async (): Promise<ApiResponse<AIConfig>> => {
    const response = await api.get('/config')
    return response.data
  },

  updateConfig: async (data: AIConfigUpdate): Promise<ApiResponse<AIConfig>> => {
    const response = await api.put('/config', data)
    return response.data
  },

  testConfig: async (data: AIConfigTest): Promise<ApiResponse<{ valid: boolean; message: string }>> => {
    const response = await api.post('/config/test', data)
    return response.data
  },
}

export default api
