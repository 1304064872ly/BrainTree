/**
 * Sidebar 侧边栏组件
 * ==================
 *
 * 这是应用的左侧导航栏组件，负责：
 * 1. 显示应用 Logo
 * 2. 提供导航菜单
 * 3. 显示思维树列表（支持多选删除）
 * 4. 新建思维树功能
 *
 * 功能特点：
 * - 可折叠：点击收起/展开
 * - 动态菜单：根据路由高亮当前页面
 * - 思维树列表：支持多选和批量删除
 * - 新建思维树：弹出 Modal 输入名称后创建
 *
 * 布局位置：应用最左侧
 */

// ============================================================
// 第一部分：导入依赖
// ============================================================
import { useState } from 'react'  // React Hook

// 路由相关
import { useNavigate, useLocation } from 'react-router-dom'

// Ant Design 组件
import {
  Layout,       // 布局
  Menu,         // 菜单
  Button,       // 按钮
  Typography,   // 排版
  Space,        // 间距
  Modal,        // 弹窗
  Input,        // 输入框
  message,      // 消息提示
  Checkbox,     // 复选框
  Divider,      // 分割线
} from 'antd'

// Ant Design 图标
import {
  FileOutlined,      // 文件图标
  NodeIndexOutlined, // 节点图标
  UploadOutlined,    // 上传图标
  PlusOutlined,      // 添加图标
  DeleteOutlined,    // 删除图标
  SettingOutlined,   // 设置图标
  CheckSquareOutlined,  // 全选图标
} from '@ant-design/icons'

// 导入状态管理和 API
import { useStore } from '../../stores'  // Zustand 状态管理
import { treeApi } from '../../services/api'  // 思维树 API

// ============================================================
// 第二部分：解构组件
// ============================================================
const { Sider } = Layout    // 侧边栏组件
const { Text } = Typography // 文本组件

// ============================================================
// 第三部分：Sidebar 组件
// ============================================================

/**
 * Sidebar 侧边栏组件
 *
 * 应用的左侧导航栏。
 *
 * @returns {JSX.Element} 侧边栏组件
 */
const Sidebar = () => {
  // ============================================================
  // 第四部分：状态定义
  // ============================================================

  // 侧边栏折叠状态
  const [collapsed, setCollapsed] = useState(false)

  // 新建思维树 Modal 显示状态
  const [isModalOpen, setIsModalOpen] = useState(false)

  // 新建思维树名称
  const [newTreeName, setNewTreeName] = useState('')

  // 多选状态：选中的思维树 ID 列表
  const [selectedTreeIds, setSelectedTreeIds] = useState<string[]>([])

  // ============================================================
  // 第五部分：路由和状态
  // ============================================================

  // 路由导航
  const navigate = useNavigate()

  // 当前路由位置
  const location = useLocation()

  // 从 Zustand 获取思维树列表和操作函数
  const { trees, addTree, removeTree } = useStore()

  // ============================================================
  // 第六部分：多选逻辑
  // ============================================================

  /**
   * 切换选中状态
   */
  const toggleSelect = (treeId: string) => {
    setSelectedTreeIds(prev =>
      prev.includes(treeId)
        ? prev.filter(id => id !== treeId)
        : [...prev, treeId]
    )
  }

  /**
   * 全选/取消全选
   */
  const toggleSelectAll = () => {
    if (selectedTreeIds.length === trees.length) {
      // 已全选，取消全选
      setSelectedTreeIds([])
    } else {
      // 全选
      setSelectedTreeIds(trees.map(t => t.id))
    }
  }

  /**
   * 批量删除
   */
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
          // 逐个删除
          let successCount = 0
          for (const treeId of selectedTreeIds) {
            const response = await treeApi.delete(treeId)
            if (response.success) {
              removeTree(treeId)
              successCount++
            }
          }

          // 清空选中状态
          setSelectedTreeIds([])

          // 如果当前页面被删除，跳转到首页
          if (selectedTreeIds.some(id => location.pathname === `/edit/${id}`)) {
            navigate('/')
          }

          message.success(`成功删除 ${successCount} 个思维树`)
        } catch (error: any) {
          message.error(error.message || '删除失败')
        }
      },
    })
  }

  // ============================================================
  // 第七部分：菜单配置
  // ============================================================

  /**
   * 菜单项配置
   *
   * 定义侧边栏的所有菜单项。
   * 包括固定菜单和动态的思维树列表。
   */
  const menuItems = [
    // 固定菜单项：思维图谱首页
    {
      key: '/',
      icon: <NodeIndexOutlined />,
      label: '思维图谱',
    },
    // 固定菜单项：文件上传
    {
      key: '/upload',
      icon: <UploadOutlined />,
      label: '上传文件',
    },
    // 动态菜单项：思维树列表（可展开）
    {
      key: 'trees',
      icon: <FileOutlined />,
      label: (
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <span>我的思维树</span>
          {!collapsed && trees.length > 0 && (
            <Button
              type="text"
              size="small"
              icon={<CheckSquareOutlined />}
              style={{ color: '#fff' }}
              onClick={(e) => {
                e.stopPropagation()
                toggleSelectAll()
              }}
            />
          )}
        </Space>
      ),
      // 动态生成子菜单：每个思维树作为一个子菜单项
      children: trees.map((tree) => ({
        key: `/edit/${tree.id}`,
        label: (
          <Space>
            {/* 复选框 */}
            <Checkbox
              checked={selectedTreeIds.includes(tree.id)}
              onClick={(e) => {
                e.stopPropagation()
                toggleSelect(tree.id)
              }}
            />
            {/* 思维树名称 */}
            <span
              style={{ cursor: 'pointer' }}
              onClick={() => navigate(`/edit/${tree.id}`)}
            >
              {tree.name}
            </span>
          </Space>
        ),
      })),
    },
    // 固定菜单项：设置
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
  ]

  // ============================================================
  // 第八部分：事件处理
  // ============================================================

  /**
   * 创建新思维树
   *
   * 验证输入并创建新的思维树。
   * 创建成功后跳转到编辑页面。
   */
  const handleCreateTree = () => {
    if (newTreeName.trim()) {
      // 创建新思维树对象
      const newTree = {
        id: Date.now().toString(),  // 使用时间戳作为临时 ID
        name: newTreeName.trim(),
        description: '',
        sourceFiles: [],
        nodes: [],
        edges: [],
        createdAt: new Date(),
        updatedAt: new Date(),
      }

      // 添加到状态
      addTree(newTree)

      // 重置表单
      setNewTreeName('')
      setIsModalOpen(false)

      // 跳转到编辑页面
      navigate(`/edit/${newTree.id}`)
    }
  }

  // ============================================================
  // 第九部分：渲染组件
  // ============================================================

  return (
    /**
     * Sider 侧边栏组件
     *
     * collapsible: 允许折叠
     * collapsed: 当前折叠状态
     * onCollapse: 折叠状态变化回调
     * style: 自定义样式（深色背景）
     */
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={setCollapsed}
      style={{ background: '#001529' }}
    >
      {/* ============================================================ */}
      {/* Logo 区域 */}
      {/* ============================================================ */}
      <div style={{ padding: '16px', textAlign: 'center' }}>
        {/*
         * 应用标题
         *
         * 折叠时显示 "BT"，展开时显示 "思维树"
         */}
        <Text strong style={{ color: '#fff', fontSize: collapsed ? '16px' : '20px' }}>
          {collapsed ? 'BT' : '思维树'}
        </Text>
      </div>

      {/* ============================================================ */}
      {/* 导航菜单 */}
      {/* ============================================================ */}
      {/*
       * Menu 导航菜单
       *
       * theme="dark": 深色主题
       * mode="inline": 内联模式
       * selectedKeys: 当前选中的菜单项（根据路由高亮）
       * items: 菜单项配置
       * onClick: 菜单点击事件（导航到对应路由）
       */}
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => {
          // 只有当点击的不是复选框区域时才导航
          if (!selectedTreeIds.includes(key.replace('/edit/', ''))) {
            navigate(key)
          }
        }}
      />

      {/* ============================================================ */}
      {/* 操作按钮区域 */}
      {/* ============================================================ */}
      {!collapsed && (
        <div style={{ padding: '16px' }}>
          {/* 新建思维树按钮 */}
          <Button
            type="primary"
            icon={<PlusOutlined />}
            block
            onClick={() => setIsModalOpen(true)}
            style={{ marginBottom: '8px' }}
          >
            新建思维树
          </Button>

          {/* 批量删除按钮（只有选中时显示） */}
          {selectedTreeIds.length > 0 && (
            <Button
              danger
              icon={<DeleteOutlined />}
              block
              onClick={handleBatchDelete}
            >
              删除选中 ({selectedTreeIds.length})
            </Button>
          )}
        </div>
      )}

      {/* ============================================================ */}
      {/* 新建思维树 Modal */}
      {/* ============================================================ */}
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

// 导出组件
export default Sidebar
