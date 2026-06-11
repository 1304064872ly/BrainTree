/**
 * TreeDrawer 思维树抽屉组件
 * ========================
 *
 * 侧边抽屉，显示思维树列表
 *
 * 功能：
 * 1. 显示所有思维树
 * 2. 支持多选
 * 3. 批量删除
 * 4. 点击进入思维树
 */

import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Drawer,
  List,
  Card,
  Button,
  Space,
  Typography,
  Tag,
  Checkbox,
  Modal,
  message,
  Empty,
} from 'antd'
import {
  FileOutlined,
  DeleteOutlined,
  CheckSquareOutlined,
  FolderOpenOutlined,
} from '@ant-design/icons'
import { useStore } from '../../stores'
import { treeApi } from '../../services/api'

const { Text } = Typography

interface TreeDrawerProps {
  open: boolean
  onClose: () => void
}

const TreeDrawer = ({ open, onClose }: TreeDrawerProps) => {
  const navigate = useNavigate()
  const location = useLocation()
  const { trees, removeTree } = useStore()
  const [selectedTreeIds, setSelectedTreeIds] = useState<string[]>([])

  // 切换选中状态
  const toggleSelect = (treeId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    setSelectedTreeIds(prev =>
      prev.includes(treeId)
        ? prev.filter(id => id !== treeId)
        : [...prev, treeId]
    )
  }

  // 全选/取消全选
  const toggleSelectAll = () => {
    if (selectedTreeIds.length === trees.length) {
      setSelectedTreeIds([])
    } else {
      setSelectedTreeIds(trees.map(t => t.id))
    }
  }

  // 批量删除
  const handleBatchDelete = () => {
    if (selectedTreeIds.length === 0) {
      message.warning('请先选择要删除的思维树')
      return
    }

    const count = selectedTreeIds.length
    const names = trees
      .filter(t => selectedTreeIds.includes(t.id))
      .map(t => t.name)
      .slice(0, 3)
      .join('、')

    Modal.confirm({
      title: '确认批量删除',
      content: `确定要删除选中的 ${count} 个思维树吗？\n${names}${count > 3 ? '...' : ''}`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          let successCount = 0
          for (const treeId of selectedTreeIds) {
            const response = await treeApi.delete(treeId)
            if (response.success) {
              removeTree(treeId)
              successCount++
            }
          }
          setSelectedTreeIds([])
          message.success(`成功删除 ${successCount} 个思维树`)

          // 如果当前页面被删除，跳转到首页
          if (selectedTreeIds.some(id => location.pathname === `/edit/${id}`)) {
            navigate('/')
            onClose()
          }
        } catch (error: any) {
          message.error(error.message || '删除失败')
        }
      },
    })
  }

  // 进入思维树
  const handleSelectTree = (treeId: string) => {
    if (selectedTreeIds.length === 0) {
      navigate(`/edit/${treeId}`)
      onClose()
    } else {
      toggleSelect(treeId)
    }
  }

  return (
    <Drawer
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <FolderOpenOutlined style={{ color: '#6366f1' }} />
            <span>我的思维树</span>
            <Tag color="blue">{trees.length}</Tag>
          </Space>
          {trees.length > 0 && (
            <Space>
              <Button
                size="small"
                icon={<CheckSquareOutlined />}
                onClick={toggleSelectAll}
              >
                {selectedTreeIds.length === trees.length ? '取消全选' : '全选'}
              </Button>
              {selectedTreeIds.length > 0 && (
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={handleBatchDelete}
                >
                  删除 ({selectedTreeIds.length})
                </Button>
              )}
            </Space>
          )}
        </div>
      }
      placement="right"
      width={400}
      open={open}
      onClose={() => {
        setSelectedTreeIds([])
        onClose()
      }}
      styles={{
        body: { padding: '16px' },
      }}
    >
      {trees.length === 0 ? (
        <Empty
          description={
            <span>
              暂无思维树
              <br />
              <Text type="secondary">请先上传文件并进行 AI 分析</Text>
            </span>
          }
        />
      ) : (
        <List
          dataSource={trees}
          renderItem={(tree) => (
            <Card
              hoverable
              size="small"
              onClick={() => handleSelectTree(tree.id)}
              style={{
                marginBottom: '12px',
                cursor: 'pointer',
                border: selectedTreeIds.includes(tree.id)
                  ? '2px solid #6366f1'
                  : '1px solid #f0f0f0',
                borderRadius: '12px',
                transition: 'all 0.2s ease',
              }}
              styles={{
                body: { padding: '16px' },
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <Checkbox
                  checked={selectedTreeIds.includes(tree.id)}
                  onClick={(e) => toggleSelect(tree.id, e)}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <FileOutlined style={{ color: '#6366f1' }} />
                    <Text strong style={{ fontSize: '15px' }}>{tree.name}</Text>
                  </div>
                  <Text type="secondary" style={{ fontSize: '13px', display: 'block', marginBottom: '8px' }}>
                    {tree.description || '暂无描述'}
                  </Text>
                  <Space size="small">
                    <Tag color="blue" style={{ borderRadius: '4px' }}>{tree.nodes.length} 节点</Tag>
                    <Tag color="green" style={{ borderRadius: '4px' }}>{tree.edges.length} 连接</Tag>
                  </Space>
                </div>
              </div>
            </Card>
          )}
        />
      )}
    </Drawer>
  )
}

export default TreeDrawer
