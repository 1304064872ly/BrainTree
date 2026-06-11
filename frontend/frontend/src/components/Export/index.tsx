import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import {
  Card,
  Button,
  Typography,
  Select,
  message,
  Divider,
  Radio,
  Checkbox,
  Form,
} from 'antd'
import {
  DownloadOutlined,
  FileImageOutlined,
  FilePdfOutlined,
  FileTextOutlined,
} from '@ant-design/icons'
import { useStore } from '../../stores'
import { exportApi } from '../../services/api'
import { downloadBlob } from '../../utils'
import { TreeNotFound, PageHeader } from '../common'

const { Title, Text } = Typography
const { Option } = Select

// 导出格式配置表
const EXPORT_FORMAT_CONFIG: Record<string, {
  label: string
  icon: React.ReactNode
  description: string
  ext: string
  mime: string
  api: (treeId: string, opts?: any) => Promise<any>
  toBlob: (data: any) => Blob
}> = {
  json: {
    label: 'JSON 数据格式',
    icon: <FileTextOutlined />,
    description: '导出完整的思维树数据结构，可用于备份或导入其他系统',
    ext: 'json',
    mime: 'application/json',
    api: (treeId) => exportApi.toJson(treeId),
    toBlob: (data) => new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }),
  },
  markdown: {
    label: 'Markdown 文档',
    icon: <FileTextOutlined />,
    description: '导出为 Markdown 格式的文档，便于阅读和分享',
    ext: 'md',
    mime: 'text/markdown',
    api: (treeId) => exportApi.toMarkdown(treeId),
    toBlob: (data) => new Blob([data], { type: 'text/markdown' }),
  },
  csv: {
    label: 'CSV 表格',
    icon: <FileTextOutlined />,
    description: '导出为 CSV 格式，可在 Excel 等表格软件中打开',
    ext: 'csv',
    mime: 'text/csv',
    api: (treeId) => exportApi.toCsv(treeId),
    toBlob: (data) => new Blob([data], { type: 'text/csv' }),
  },
  image: {
    label: '图片格式',
    icon: <FileImageOutlined />,
    description: '导出为图片格式，可用于插入文档或演示',
    ext: 'png',
    mime: 'image/png',
    api: (treeId, opts) => exportApi.toImage(treeId, opts?.imageFormat || 'png'),
    toBlob: (data) => data,
  },
  pdf: {
    label: 'PDF 文档',
    icon: <FilePdfOutlined />,
    description: '导出为 PDF 文档，便于打印和正式分享',
    ext: 'pdf',
    mime: 'application/pdf',
    api: (treeId) => exportApi.toPdf(treeId),
    toBlob: (data) => data,
  },
}

const Export = () => {
  const { id } = useParams<{ id: string }>()
  const { trees } = useStore()
  const [exportFormat, setExportFormat] = useState<string>('json')
  const [imageFormat, setImageFormat] = useState<'png' | 'svg'>('png')
  const [includeMetadata, setIncludeMetadata] = useState(true)
  const [loading, setLoading] = useState(false)

  const tree = useMemo(() => trees.find((t) => t.id === id), [trees, id])

  if (!tree) {
    return <TreeNotFound />
  }

  const handleExport = async () => {
    const config = EXPORT_FORMAT_CONFIG[exportFormat]
    if (!config) {
      message.error('不支持的导出格式')
      return
    }

    setLoading(true)
    try {
      const response = await config.api(tree.id, { imageFormat })
      if (response.success) {
        const blob = config.toBlob(response.data)
        const ext = exportFormat === 'image' ? imageFormat : config.ext
        downloadBlob(blob, `${tree.name}.${ext}`)
        message.success('导出成功')
      } else {
        throw new Error(response.error || '导出失败')
      }
    } catch (error: any) {
      message.error(`导出失败: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const formatConfig = EXPORT_FORMAT_CONFIG[exportFormat]

  return (
    <div style={{ padding: '24px' }}>
      <PageHeader title={`导出思维树: ${tree.name}`} />

      <Card>
        <div style={{ display: 'flex', gap: '24px' }}>
          {/* 左侧导出选项 */}
          <Card title="导出设置" style={{ width: '400px' }}>
            <Form layout="vertical">
              <Form.Item label="导出格式">
                <Select
                  value={exportFormat}
                  onChange={setExportFormat}
                  style={{ width: '100%' }}
                >
                  {Object.entries(EXPORT_FORMAT_CONFIG).map(([key, { label }]) => (
                    <Option key={key} value={key}>{label}</Option>
                  ))}
                </Select>
              </Form.Item>

              {exportFormat === 'image' && (
                <Form.Item label="图片格式">
                  <Radio.Group
                    value={imageFormat}
                    onChange={(e) => setImageFormat(e.target.value)}
                  >
                    <Radio value="png">PNG</Radio>
                    <Radio value="svg">SVG</Radio>
                  </Radio.Group>
                </Form.Item>
              )}

              <Form.Item>
                <Checkbox
                  checked={includeMetadata}
                  onChange={(e) => setIncludeMetadata(e.target.checked)}
                >
                  包含元数据（创建时间、更新时间等）
                </Checkbox>
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  icon={<DownloadOutlined />}
                  onClick={handleExport}
                  loading={loading}
                  block
                  size="large"
                >
                  导出
                </Button>
              </Form.Item>
            </Form>
          </Card>

          {/* 右侧预览区域 */}
          <Card title="导出预览" style={{ flex: 1 }}>
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>
                {formatConfig?.icon}
              </div>
              <Title level={4}>
                {formatConfig?.label}
                {exportFormat === 'image' && ` (${imageFormat.toUpperCase()})`}
              </Title>
              <Text type="secondary">
                {formatConfig?.description}
              </Text>

              <Divider />

              <div style={{ textAlign: 'left' }}>
                <Title level={5}>导出内容预览:</Title>
                <ul>
                  <li>思维树名称: {tree.name}</li>
                  <li>节点数量: {tree.nodes.length} 个</li>
                  <li>连接数量: {tree.edges.length} 条</li>
                  {includeMetadata && (
                    <>
                      <li>创建时间: {new Date(tree.createdAt).toLocaleString()}</li>
                      <li>更新时间: {new Date(tree.updatedAt).toLocaleString()}</li>
                    </>
                  )}
                </ul>
              </div>
            </div>
          </Card>
        </div>
      </Card>
    </div>
  )
}

export default Export
