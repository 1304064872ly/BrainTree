/**
 * TopNav 顶部导航栏组件
 * ====================
 *
 * 现代化的顶部导航栏，替代传统侧边栏
 *
 * 功能：
 * 1. Logo + 应用名称
 * 2. 导航链接（思维图谱、上传文件、设置）
 * 3. 思维树抽屉按钮
 */

import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Button, Space, Typography } from 'antd'
import {
  NodeIndexOutlined,
  UploadOutlined,
  SettingOutlined,
  FolderOutlined,
} from '@ant-design/icons'
import { useStore } from '../../stores'
import TreeDrawer from '../TreeDrawer'

const { Header } = Layout
const { Text } = Typography

const TopNav = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { trees } = useStore()
  const [drawerOpen, setDrawerOpen] = useState(false)

  // 导航菜单项
  const navItems = [
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
      key: '/settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
  ]

  // 当前选中的菜单项
  const selectedKey = navItems.find(item => location.pathname === item.key)?.key || '/'

  return (
    <>
      <Header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          background: 'rgba(255, 255, 255, 0.85)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.4)',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
          height: '64px',
        }}
      >
        {/* Logo 区域 */}
        <Space
          style={{ cursor: 'pointer' }}
          onClick={() => navigate('/')}
        >
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontWeight: 'bold',
              fontSize: '18px',
            }}
          >
            BT
          </div>
          <Text
            strong
            style={{
              fontSize: '20px',
              background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            思维树
          </Text>
        </Space>

        {/* 导航菜单 */}
        <Menu
          mode="horizontal"
          selectedKeys={[selectedKey]}
          items={navItems}
          onClick={({ key }) => navigate(key)}
          style={{
            flex: 1,
            justifyContent: 'center',
            background: 'transparent',
            borderBottom: 'none',
            minWidth: '300px',
          }}
        />

        {/* 右侧操作 */}
        <Space>
          <Button
            type="primary"
            icon={<FolderOutlined />}
            onClick={() => setDrawerOpen(true)}
            style={{
              background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
              border: 'none',
              borderRadius: '8px',
              boxShadow: '0 2px 4px rgba(99, 102, 241, 0.3)',
            }}
          >
            我的思维树 ({trees.length})
          </Button>
        </Space>
      </Header>

      {/* 思维树抽屉 */}
      <TreeDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </>
  )
}

export default TopNav
