/**
 * App 根组件
 * ==========
 *
 * 这是 React 应用的根组件，负责：
 * 1. 定义应用的整体布局结构
 * 2. 配置路由系统
 * 3. 在应用启动时加载初始数据
 *
 * 布局结构：
 * - 左侧：Sidebar（可折叠侧边栏）
 * - 右侧：Content（主要内容区域）
 *
 * 路由配置：
 * - / → MindMap（思维图谱首页）
 * - /upload → FileUpload（文件上传）
 * - /edit/:id → NodeEditor（节点编辑）
 * - /export/:id → Export（导出功能）
 * - /settings → Settings（设置页面）
 *
 * 数据加载：
 * - 应用启动时自动加载思维树列表和文件列表
 * - 数据存储在 Zustand 全局状态中
 */

// ============================================================
// 第一部分：导入依赖
// ============================================================
import { useEffect } from 'react'                              // React Hook
import { Routes, Route } from 'react-router-dom'               // 路由组件
import { Layout, message } from 'antd'                         // Ant Design 组件

// 导入页面组件
import Sidebar from './components/Sidebar'                     // 侧边栏
import MindMap from './components/MindMap'                     // 思维图谱
import FileUpload from './components/FileUpload'               // 文件上传
import NodeEditor from './components/NodeEditor'               // 节点编辑
import Export from './components/Export'                       // 导出功能
import Settings from './components/Settings'                   // 设置页面

// 导入状态管理和 API
import { useStore } from './stores'                            // Zustand 状态管理
import { treeApi, fileApi } from './services/api'              // API 服务

// ============================================================
// 第二部分：解构 Ant Design 组件
// ============================================================
const { Content } = Layout  // 内容区域组件

// ============================================================
// 第三部分：App 组件
// ============================================================

/**
 * App 根组件
 *
 * 应用的入口组件，定义整体布局和路由。
 *
 * @returns {JSX.Element} 应用根组件
 */
function App() {
  // 从 Zustand 状态管理中获取状态和操作函数
  const { setTrees, setFiles, setLoading, setError } = useStore()

  // ============================================================
  // 第四部分：应用启动时加载数据
  // ============================================================

  /**
   * useEffect Hook - 应用启动时执行
   *
   * 空依赖数组 [] 表示只在组件挂载时执行一次。
   * 负责从后端加载初始数据：
   * 1. 思维树列表
   * 2. 文件列表
   */
  useEffect(() => {
    /**
     * 异步加载数据
     *
     * 使用 async/await 处理异步 API 调用。
     * 错误会被捕获并存储到全局状态中。
     */
    const loadData = async () => {
      setLoading(true)  // 设置加载状态
      try {
        // 加载思维树列表
        const treesResponse = await treeApi.getList()
        if (treesResponse.success && treesResponse.data) {
          setTrees(treesResponse.data)  // 更新状态
        }

        // 加载文件列表
        const filesResponse = await fileApi.getList()
        if (filesResponse.success && filesResponse.data) {
          setFiles(filesResponse.data)  // 更新状态
        }
      } catch (error: any) {
        // 错误处理
        setError(error.message)
        console.error('加载数据失败:', error)
      } finally {
        setLoading(false)  // 无论成功失败都取消加载状态
      }
    }

    loadData()  // 执行数据加载
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
  // ↑ 空依赖数组：只在组件挂载时执行一次
  // ↑ eslint-disable-line：禁用 exhaustive-deps 规则

  // ============================================================
  // 第五部分：渲染组件
  // ============================================================

  return (
    /**
     * Layout 布局组件
     *
     * 使用 Ant Design 的 Layout 组件实现整体布局。
     * minHeight: '100vh' 确保布局占满整个视口高度。
     */
    <Layout style={{ minHeight: '100vh' }}>
      {/* 左侧边栏 */}
      <Sidebar />

      {/* 右侧内容区域 */}
      <Layout>
        {/*
         * Content 内容区域
         *
         * padding: '24px' 添加内边距
         * background: '#fff' 设置白色背景
         */}
        <Content style={{ padding: '24px', background: '#fff' }}>
          {/*
           * Routes 路由容器
           *
           * 定义应用的所有路由规则。
           * 当 URL 匹配时，渲染对应的组件。
           */}
          <Routes>
            {/* 首页：思维图谱 */}
            <Route path="/" element={<MindMap />} />

            {/* 文件上传页面 */}
            <Route path="/upload" element={<FileUpload />} />

            {/* 节点编辑页面（动态路由，:id 是思维树 ID） */}
            <Route path="/edit/:id" element={<NodeEditor />} />

            {/* 导出页面（动态路由，:id 是思维树 ID） */}
            <Route path="/export/:id" element={<Export />} />

            {/* 设置页面 */}
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}

// 导出 App 组件
export default App
