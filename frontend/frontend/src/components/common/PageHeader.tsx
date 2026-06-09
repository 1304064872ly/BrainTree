import { Space, Button, Typography } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const { Title } = Typography

interface PageHeaderProps {
  title: string
}

/**
 * 页面头部组件
 * 包含返回按钮和标题
 */
const PageHeader = ({ title }: PageHeaderProps) => {
  const navigate = useNavigate()

  return (
    <div style={{ padding: '24px' }}>
      <Space style={{ marginBottom: '24px' }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
          返回
        </Button>
        <Title level={3} style={{ margin: 0 }}>
          {title}
        </Title>
      </Space>
    </div>
  )
}

export default PageHeader
