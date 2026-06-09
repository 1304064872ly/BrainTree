import { create } from 'zustand'
import { MindTree, SourceFile } from '../types'

interface AppState {
  // 文件相关
  files: SourceFile[]
  currentFile: SourceFile | null
  setFiles: (files: SourceFile[]) => void
  setCurrentFile: (file: SourceFile | null) => void
  addFile: (file: SourceFile) => void
  removeFile: (id: string) => void

  // 思维树相关
  trees: MindTree[]
  currentTree: MindTree | null
  setTrees: (trees: MindTree[]) => void
  setCurrentTree: (tree: MindTree | null) => void
  addTree: (tree: MindTree) => void
  addTrees: (trees: MindTree[]) => void
  updateTree: (id: string, data: Partial<MindTree>) => void
  removeTree: (id: string) => void

  // 多棵树选择相关
  selectedTreeIndex: number
  setSelectedTreeIndex: (index: number) => void

  // UI相关
  loading: boolean
  error: string | null
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useStore = create<AppState>((set) => ({
  // 文件相关
  files: [],
  currentFile: null,
  setFiles: (files) => set({ files }),
  setCurrentFile: (file) => set({ currentFile: file }),
  addFile: (file) => set((state) => ({ files: [...state.files, file] })),
  removeFile: (id) => set((state) => ({
    files: state.files.filter((f) => f.id !== id),
    currentFile: state.currentFile?.id === id ? null : state.currentFile,
  })),

  // 思维树相关
  trees: [],
  currentTree: null,
  setTrees: (trees) => set({ trees }),
  setCurrentTree: (tree) => set({ currentTree: tree }),
  addTree: (tree) => set((state) => ({ trees: [...state.trees, tree] })),
  addTrees: (newTrees) => set((state) => ({
    trees: [...state.trees, ...newTrees],
    // 如果当前没有选中树，选中第一棵新树
    currentTree: state.currentTree || (newTrees.length > 0 ? newTrees[0] : null),
  })),
  updateTree: (id, data) => set((state) => ({
    trees: state.trees.map((t) =>
      t.id === id ? { ...t, ...data, updatedAt: new Date() } : t
    ),
    currentTree: state.currentTree?.id === id
      ? { ...state.currentTree, ...data, updatedAt: new Date() }
      : state.currentTree,
  })),
  removeTree: (id) => set((state) => ({
    trees: state.trees.filter((t) => t.id !== id),
    currentTree: state.currentTree?.id === id ? null : state.currentTree,
  })),

  // 多棵树选择相关
  selectedTreeIndex: 0,
  setSelectedTreeIndex: (index) => set({ selectedTreeIndex: index }),

  // UI相关
  loading: false,
  error: null,
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}))
