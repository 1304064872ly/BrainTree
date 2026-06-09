/**
 * Zustand 全局状态管理
 * ===================
 *
 * 本模块使用 Zustand 库管理应用的全局状态。
 * Zustand 是一个轻量级的状态管理库，比 Redux 更简洁。
 *
 * 状态分类：
 * 1. 文件相关状态（files, currentFile）
 * 2. 思维树相关状态（trees, currentTree）
 * 3. UI 相关状态（loading, error）
 *
 * 主要导出：
 * - useStore: 自定义 Hook，用于在组件中访问和修改状态
 *
 * 使用示例：
 *   const { files, setFiles, loading } = useStore()
 */

// ============================================================
// 第一部分：导入依赖
// ============================================================
import { create } from 'zustand'  // Zustand 状态管理库
import { MindTree, SourceFile } from '../types'  // 类型定义

// ============================================================
// 第二部分：状态接口定义
// ============================================================

/**
 * 应用状态接口
 *
 * 定义应用的所有状态和操作函数。
 * 所有状态都是响应式的，修改后会自动触发组件重新渲染。
 */
interface AppState {
  // ============================================================
  // 文件相关状态
  // ============================================================

  /** 已上传的文件列表 */
  files: SourceFile[]

  /** 当前选中的文件 */
  currentFile: SourceFile | null

  /** 设置文件列表 */
  setFiles: (files: SourceFile[]) => void

  /** 设置当前文件 */
  setCurrentFile: (file: SourceFile | null) => void

  /** 添加文件到列表 */
  addFile: (file: SourceFile) => void

  /** 从列表中移除文件 */
  removeFile: (id: string) => void

  // ============================================================
  // 思维树相关状态
  // ============================================================

  /** 思维树列表 */
  trees: MindTree[]

  /** 当前编辑的思维树 */
  currentTree: MindTree | null

  /** 设置思维树列表 */
  setTrees: (trees: MindTree[]) => void

  /** 设置当前思维树 */
  setCurrentTree: (tree: MindTree | null) => void

  /** 添加思维树 */
  addTree: (tree: MindTree) => void

  /** 批量添加思维树 */
  addTrees: (trees: MindTree[]) => void

  /** 更新思维树 */
  updateTree: (id: string, data: Partial<MindTree>) => void

  /** 删除思维树 */
  removeTree: (id: string) => void

  // ============================================================
  // 多棵树选择相关状态
  // ============================================================

  /** 当前选中的思维树索引 */
  selectedTreeIndex: number

  /** 设置选中的思维树索引 */
  setSelectedTreeIndex: (index: number) => void

  // ============================================================
  // UI 相关状态
  // ============================================================

  /** 全局加载状态 */
  loading: boolean

  /** 全局错误信息 */
  error: string | null

  /** 设置加载状态 */
  setLoading: (loading: boolean) => void

  /** 设置错误信息 */
  setError: (error: string | null) => void
}

// ============================================================
// 第三部分：创建 Zustand Store
// ============================================================

/**
 * 创建 Zustand Store
 *
 * 使用 create 函数创建全局状态存储。
 * 泛型参数 AppState 定义了状态的类型。
 *
 * @returns useStore Hook
 */
export const useStore = create<AppState>((set) => ({
  // ============================================================
  // 文件相关状态和操作
  // ============================================================

  // 初始状态
  files: [],              // 空文件列表
  currentFile: null,      // 未选中文件

  /**
   * 设置文件列表
   *
   * @param files - 新的文件列表
   */
  setFiles: (files) => set({ files }),

  /**
   * 设置当前文件
   *
   * @param file - 要选中的文件，null 表示取消选中
   */
  setCurrentFile: (file) => set({ currentFile: file }),

  /**
   * 添加文件到列表
   *
   * @param file - 要添加的文件
   */
  addFile: (file) => set((state) => ({
    files: [...state.files, file]  // 展开现有文件，添加新文件
  })),

  /**
   * 从列表中移除文件
   *
   * @param id - 要移除的文件 ID
   *
   * 注意：如果移除的是当前选中的文件，会取消选中
   */
  removeFile: (id) => set((state) => ({
    files: state.files.filter((f) => f.id !== id),  // 过滤掉指定 ID 的文件
    currentFile: state.currentFile?.id === id ? null : state.currentFile,  // 如果是当前文件则取消选中
  })),

  // ============================================================
  // 思维树相关状态和操作
  // ============================================================

  // 初始状态
  trees: [],              // 空思维树列表
  currentTree: null,      // 未选中思维树

  /**
   * 设置思维树列表
   *
   * @param trees - 新的思维树列表
   */
  setTrees: (trees) => set({ trees }),

  /**
   * 设置当前思维树
   *
   * @param tree - 要选中的思维树，null 表示取消选中
   */
  setCurrentTree: (tree) => set({ currentTree: tree }),

  /**
   * 添加思维树
   *
   * @param tree - 要添加的思维树
   */
  addTree: (tree) => set((state) => ({
    trees: [...state.trees, tree]  // 展开现有树，添加新树
  })),

  /**
   * 批量添加思维树
   *
   * @param newTrees - 要添加的思维树数组
   *
   * 注意：如果当前没有选中树，会自动选中第一棵新树
   */
  addTrees: (newTrees) => set((state) => ({
    trees: [...state.trees, ...newTrees],  // 合并现有树和新树
    // 如果当前没有选中树，选中第一棵新树
    currentTree: state.currentTree || (newTrees.length > 0 ? newTrees[0] : null),
  })),

  /**
   * 更新思维树
   *
   * @param id - 要更新的思维树 ID
   * @param data - 更新数据
   *
   * 注意：会同时更新 trees 列表和 currentTree
   */
  updateTree: (id, data) => set((state) => ({
    // 更新 trees 列表中对应的树
    trees: state.trees.map((t) =>
      t.id === id ? { ...t, ...data, updatedAt: new Date() } : t
    ),
    // 如果更新的是当前树，也更新 currentTree
    currentTree: state.currentTree?.id === id
      ? { ...state.currentTree, ...data, updatedAt: new Date() }
      : state.currentTree,
  })),

  /**
   * 删除思维树
   *
   * @param id - 要删除的思维树 ID
   *
   * 注意：如果删除的是当前树，会取消选中
   */
  removeTree: (id) => set((state) => ({
    trees: state.trees.filter((t) => t.id !== id),  // 过滤掉指定 ID 的树
    currentTree: state.currentTree?.id === id ? null : state.currentTree,  // 如果是当前树则取消选中
  })),

  // ============================================================
  // 多棵树选择相关状态和操作
  // ============================================================

  selectedTreeIndex: 0,  // 默认选中第一棵树

  /**
   * 设置选中的思维树索引
   *
   * @param index - 新的索引值
   */
  setSelectedTreeIndex: (index) => set({ selectedTreeIndex: index }),

  // ============================================================
  // UI 相关状态和操作
  // ============================================================

  loading: false,  // 初始不加载
  error: null,     // 初始无错误

  /**
   * 设置加载状态
   *
   * @param loading - 是否正在加载
   */
  setLoading: (loading) => set({ loading }),

  /**
   * 设置错误信息
   *
   * @param error - 错误信息，null 表示清除错误
   */
  setError: (error) => set({ error }),
}))
