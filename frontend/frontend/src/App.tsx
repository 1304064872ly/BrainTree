import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Layout, message } from 'antd'
import Sidebar from './components/Sidebar'
import MindMap from './components/MindMap'
import FileUpload from './components/FileUpload'
import NodeEditor from './components/NodeEditor'
import Export from './components/Export'
import Settings from './components/Settings'
import { useStore } from './stores'
import { treeApi, fileApi } from './services/api'

const { Content } = Layout

function App() {
  const { setTrees, setFiles, setLoading, setError } = useStore()

  useEffect(() => {
    // 应用启动时加载数据
    const loadData = async () => {
      setLoading(true)
      try {
        // 加载思维树列表
        const treesResponse = await treeApi.getList()
        if (treesResponse.success && treesResponse.data) {
          setTrees(treesResponse.data)
        }

        // 加载文件列表
        const filesResponse = await fileApi.getList()
        if (filesResponse.success && filesResponse.data) {
          setFiles(filesResponse.data)
        }
      } catch (error: any) {
        setError(error.message)
        console.error('加载数据失败:', error)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sidebar />
      <Layout>
        <Content style={{ padding: '24px', background: '#fff' }}>
          <Routes>
            <Route path="/" element={<MindMap />} />
            <Route path="/upload" element={<FileUpload />} />
            <Route path="/edit/:id" element={<NodeEditor />} />
            <Route path="/export/:id" element={<Export />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}

export default App
