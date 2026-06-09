/**
 * TypeScript 类型定义
 * ===================
 *
 * 本模块定义了 BrainTree 项目前端的所有核心类型。
 * 使用 TypeScript 接口定义数据结构，确保类型安全。
 *
 * 类型分类：
 * 1. 核心数据类型：MindTree, MindNode, MindEdge
 * 2. 文件相关类型：SourceFile
 * 3. 扩展类型：MindForest, FileGroup
 * 4. API 响应类型：ApiResponse
 *
 * 使用示例：
 *   import { MindTree, SourceFile } from '../types'
 *
 *   const tree: MindTree = {
 *     id: 'uuid',
 *     name: '思维树',
 *     // ...
 *   }
 */

// ============================================================
// 第一部分：核心数据类型
// ============================================================

/**
 * 思维树接口
 *
 * 表示一个完整的思维树，包含节点和关系。
 * 这是项目的核心数据结构。
 *
 * @property id - 思维树唯一标识（UUID 格式）
 * @property name - 思维树名称
 * @property description - 描述信息
 * @property sourceFiles - 关联的源文件（ID 数组或文件对象数组）
 * @property nodes - 节点列表
 * @property edges - 关系列表
 * @property createdAt - 创建时间
 * @property updatedAt - 更新时间
 *
 * 使用场景：
 * - 思维树列表展示
 * - 思维图谱渲染
 * - 节点编辑
 */
export interface MindTree {
  id: string                    // 思维树唯一标识
  name: string                  // 思维树名称
  description: string           // 描述信息
  sourceFiles: string[] | SourceFile[]  // 关联的源文件
  nodes: MindNode[]             // 节点列表
  edges: MindEdge[]             // 关系列表
  createdAt: Date               // 创建时间
  updatedAt: Date               // 更新时间
}

/**
 * 源文件接口
 *
 * 表示用户上传的文件信息。
 *
 * @property id - 文件唯一标识
 * @property name - 文件名
 * @property type - 文件类型
 * @property size - 文件大小（字节）
 * @property uploadedAt - 上传时间
 * @property content - 提取的文本内容（可选）
 *
 * 使用场景：
 * - 文件列表展示
 * - 文件选择
 * - AI 分析
 */
export interface SourceFile {
  id: string                        // 文件唯一标识
  name: string                      // 文件名
  type: 'pdf' | 'docx' | 'txt'     // 文件类型
  size: number                      // 文件大小（字节）
  uploadedAt: Date                  // 上传时间
  content?: string                  // 文本内容（可选）
}

/**
 * 思维树节点接口
 *
 * 表示思维树中的一个节点（概念、主题、知识点）。
 *
 * @property id - 节点唯一标识
 * @property label - 节点标签（显示名称）
 * @property description - 节点描述
 * @property type - 节点类型
 * @property level - 节点层级（1-4）
 * @property position - 节点位置坐标
 * @property metadata - 元数据
 * @property sourceFile - 来源文件名（可选）
 *
 * 节点类型说明：
 * - concept: 核心概念/主题（level 1）
 * - topic: 分类/子主题（level 2）
 * - detail: 具体知识点（level 3）
 * - example: 示例/代码（level 4）
 */
export interface MindNode {
  id: string                                    // 节点唯一标识
  label: string                                 // 节点标签
  description: string                           // 节点描述
  type: 'concept' | 'topic' | 'detail' | 'example'  // 节点类型
  level: number                                 // 节点层级（1-4）
  position: { x: number; y: number }            // 节点位置坐标
  metadata: Record<string, any>                 // 元数据
  sourceFile?: string                           // 来源文件名（可选）
}

/**
 * 思维树边接口
 *
 * 表示思维树中两个节点之间的关系。
 *
 * @property id - 边唯一标识
 * @property source - 源节点 ID
 * @property target - 目标节点 ID
 * @property label - 关系标签
 * @property type - 关系类型
 *
 * 关系类型说明：
 * - contains: 包含关系（父节点包含子节点）
 * - relates: 关联关系（节点之间有相关性）
 * - depends: 依赖关系（一个节点依赖另一个节点）
 * - examples: 示例关系（一个节点是另一个节点的示例）
 */
export interface MindEdge {
  id: string                                                    // 边唯一标识
  source: string                                                // 源节点 ID
  target: string                                                // 目标节点 ID
  label: string                                                 // 关系标签
  type: 'contains' | 'relates' | 'depends' | 'examples'        // 关系类型
}

// ============================================================
// 第二部分：扩展类型
// ============================================================

/**
 * 思维森林接口
 *
 * 表示多个思维树的集合，用于多文件分析场景。
 *
 * @property id - 森林唯一标识
 * @property name - 森林名称
 * @property description - 描述信息
 * @property trees - 思维树列表
 * @property metadata - 元数据（文件数、树数、分组信息）
 *
 * 使用场景：
 * - 多文件分析结果展示
 * - 分组管理
 */
export interface MindForest {
  id: string                        // 森林唯一标识
  name: string                      // 森林名称
  description: string               // 描述信息
  trees: MindTree[]                 // 思维树列表
  metadata: {
    totalFiles: number              // 总文件数
    totalTrees: number              // 总树数
    groups: FileGroup[]             // 分组信息
  }
}

/**
 * 文件分组接口
 *
 * 表示多文件分析时的分组信息。
 *
 * @property groupIndex - 分组索引
 * @property fileIds - 文件 ID 列表
 * @property fileNames - 文件名列表
 * @property commonKeywords - 共同关键词
 * @property avgSimilarity - 平均相似度
 * @property treeId - 生成的思维树 ID
 *
 * 使用场景：
 * - 多文件分析的分组展示
 * - 分组详情查看
 */
export interface FileGroup {
  groupIndex: number                // 分组索引
  fileIds: string[]                 // 文件 ID 列表
  fileNames: string[]               // 文件名列表
  commonKeywords: string[]          // 共同关键词
  avgSimilarity: number             // 平均相似度
  treeId: string                    // 生成的思维树 ID
}

// ============================================================
// 第三部分：API 响应类型
// ============================================================

/**
 * API 响应接口
 *
 * 所有 API 接口都使用这个统一的响应格式。
 * 使用泛型支持不同类型的 data 字段。
 *
 * @property success - 请求是否成功
 * @property data - 响应数据（类型由泛型参数决定）
 * @property message - 成功消息（可选）
 * @property error - 错误信息（可选）
 *
 * 使用示例：
 *   const response: ApiResponse<MindTree> = await treeApi.getById(id)
 *   if (response.success) {
 *     console.log(response.data.name)
 *   } else {
 *     console.error(response.error)
 *   }
 */
export interface ApiResponse<T> {
  success: boolean                  // 请求是否成功
  data?: T                          // 响应数据
  message?: string                  // 成功消息
  error?: string                    // 错误信息
}
