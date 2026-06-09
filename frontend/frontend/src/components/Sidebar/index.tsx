import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Button, Typography, Space, Modal, Input, message } from 'antd'
import {
  FileOutlined,
  NodeIndexOutlined,
  UploadOutlined,
  ExportOutlined,
  PlusOutlined,
  DeleteOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { useStore } from '../../stores'
import { treeApi } from '../../services/api'

const { Sider } = Layout
const { Text } = Typography

const Sidebar = () => {
  const [collapsed, setCollapsed] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [newTreeName, setNewTreeName] = useState('')
  const navigate = useNavigate()
  const location = useLocation()
  const { trees, addTree, removeTree } = useStore()

  const menuItems = [
    {
      key: '/',
      icon: <NodeIndexOutlined />,
      label: '思维图谱',
    },
    {
      key: '/upload',
      icon: <UploadOutlined />,
      label: '上传文件',
    },
    {
      key: 'trees',
      icon: <FileOutlined />,
      label: '我的思维树',
      children: trees.map((tree) => ({
        key: `/edit/${tree.id}`,
        label: (
          <Space>
            <Button
              type="text"
              size="small"
              icon={<DeleteOutlined />}
              onClick={(e) => {
                e.stopPropagation()
                Modal.confirm({
                  title: '确认删除',
                  content: `确定要删除思维树"${tree.name}"吗？`,
                  onOk: async () => {
                    try {
                      const response = await treeApi.delete(tree.id)
                      if (response.success) {
                        removeTree(tree.id)
                        message.success('删除成功')
                        if (location.pathname === `/edit/${tree.id}`) {
                          navigate('/')
                        }
                      } else {
                        message.error(response.error || '删除失败')
                      }
                    } catch (error: any) {
                      message.error(error.message || '删除失败')
                    }
                  },
                })
              }}
            />
            <span>{tree.name}</span>
          </Space>
        ),
      })),
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
  ]

  const handleCreateTree = () => {
    if (newTreeName.trim()) {
      const newTree = {
        id: Date.now().toString(),
        name: newTreeName.trim(),
        description: '',
        sourceFiles: [],
        nodes: [],
        edges: [],
        createdAt: new Date(),
        updatedAt: new Date(),
      }
      addTree(newTree)
      setNewTreeName('')
      setIsModalOpen(false)
      navigate(`/edit/${newTree.id}`)
    }
  }

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={setCollapsed}
      style={{ background: '#001529' }}
    >
      <div style={{ padding: '16px', textAlign: 'center' }}>
        <Text strong style={{ color: '#fff', fontSize: collapsed ? '16px' : '20px' }}>
          {collapsed ? 'BT' : '思维树'}
        </Text>
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
      />
      {!collapsed && (
        <div style={{ padding: '16px' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            block
            onClick={() => setIsModalOpen(true)}
          >
            新建思维树
          </Button>
        </div>
      )}
      <Modal
        title="新建思维树"
        open={isModalOpen}
        onOk={handleCreateTree}
        onCancel={() => {
          setIsModalOpen(false)
          setNewTreeName('')
        }}
        okText="创建"
        cancelText="取消"
      >
        <Input
          placeholder="请输入思维树名称"
          value={newTreeName}
          onChange={(e) => setNewTreeName(e.target.value)}
          onPressEnter={handleCreateTree}
        />
      </Modal>
    </Sider>
  )
}

export default Sidebar
