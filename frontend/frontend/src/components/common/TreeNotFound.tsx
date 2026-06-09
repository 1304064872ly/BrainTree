import { Button, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'

const { Title } = Typography

/**
 * 思维树未找到时的回退组件
 */
const TreeNotFound = () => {
  const navigate = useNavigate()

  return (
    <div style={{ padding: '24px' }}>
      <Title level={3}>思维树不存在</Title>
      <Button onClick={() => navigate('/')}>返回首页</Button>
    </div>
  )
}

export default TreeNotFound
