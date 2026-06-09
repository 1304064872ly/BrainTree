export interface MindTree {
  id: string
  name: string
  description: string
  sourceFiles: string[] | SourceFile[]
  nodes: MindNode[]
  edges: MindEdge[]
  createdAt: Date
  updatedAt: Date
}

export interface SourceFile {
  id: string
  name: string
  type: 'pdf' | 'docx' | 'txt'
  size: number
  uploadedAt: Date
  content?: string
}

export interface MindNode {
  id: string
  label: string
  description: string
  type: 'concept' | 'topic' | 'detail' | 'example'
  level: number
  position: { x: number; y: number }
  metadata: Record<string, any>
  sourceFile?: string  // 来源文件名
}

export interface MindEdge {
  id: string
  source: string
  target: string
  label: string
  type: 'contains' | 'relates' | 'depends' | 'examples'
}

// 森林结构 - 包含多棵树
export interface MindForest {
  id: string
  name: string
  description: string
  trees: MindTree[]
  metadata: {
    totalFiles: number
    totalTrees: number
    groups: FileGroup[]
  }
}

// 文件分组信息
export interface FileGroup {
  groupIndex: number
  fileIds: string[]
  fileNames: string[]
  commonKeywords: string[]
  avgSimilarity: number
  treeId: string
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  message?: string
  error?: string
}
