import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, Button, message, List, Typography, Space, Card, Modal, Checkbox } from 'antd'
import {
  FilePdfOutlined,
  FileTextOutlined,
  FileUnknownOutlined,
  DeleteOutlined,
  InboxOutlined,
  RobotOutlined,
} from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'
import { useStore } from '../../stores'
import { fileApi, analyzeApi } from '../../services/api'

const { Dragger } = Upload
const { Title, Text } = Typography

const FileUpload = () => {
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [selectedFiles, setSelectedFiles] = useState<string[]>([])
  const [analyzing, setAnalyzing] = useState(false)
  const { files, addFile, removeFile, addTree, setLoading, setError } = useStore()
  const navigate = useNavigate()

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'pdf':
        return <FilePdfOutlined style={{ color: '#ff4d4f' }} />
      case 'docx':
        return <FileTextOutlined style={{ color: '#1890ff' }} />
      case 'txt':
        return <FileTextOutlined style={{ color: '#52c41a' }} />
      default:
        return <FileUnknownOutlined />
    }
  }

  const uploadProps = {
    name: 'file',
    multiple: true,
    fileList,
    accept: '.pdf,.docx,.txt,.md,.markdown',
    beforeUpload: (file: File) => {
      const isValidType = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'text/markdown',
        'text/x-markdown',
        '',  // MD 文件可能没有正确的 MIME 类型
      ].includes(file.type) || file.name.endsWith('.md') || file.name.endsWith('.markdown')

      if (!isValidType) {
        message.error('只支持 PDF、DOCX、TXT、Markdown 格式的文件！')
        return false
      }

      const isLt50M = file.size / 1024 / 1024 < 50
      if (!isLt50M) {
        message.error('文件大小不能超过 50MB！')
        return false
      }

      return true
    },
    customRequest: async (options: any) => {
      const { file, onSuccess, onError } = options
      setLoading(true)
      try {
        const response = await fileApi.upload(file as File)
        if (response.success && response.data) {
          addFile(response.data)
          onSuccess(response.data)
          message.success(`${file.name} 上传成功`)
        } else {
          throw new Error(response.error || '上传失败')
        }
      } catch (error: any) {
        onError(error)
        setError(error.message)
        message.error(`${file.name} 上传失败: ${error.message}`)
      } finally {
        setLoading(false)
      }
    },
    onChange(info: any) {
      setFileList(info.fileList)
    },
    onDrop(e: React.DragEvent) {
      console.log('Dropped files', e.dataTransfer.files)
    },
  }

  const handleDelete = async (id: string) => {
    try {
      const response = await fileApi.delete(id)
      if (response.success) {
        removeFile(id)
        setSelectedFiles(selectedFiles.filter(fId => fId !== id))
        message.success('文件删除成功')
      }
    } catch (error: any) {
      message.error(`删除失败: ${error.message}`)
    }
  }

  const handleSelectFile = (fileId: string, checked: boolean) => {
    if (checked) {
      setSelectedFiles([...selectedFiles, fileId])
    } else {
      setSelectedFiles(selectedFiles.filter(id => id !== fileId))
    }
  }

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedFiles(files.map(f => f.id))
    } else {
      setSelectedFiles([])
    }
  }

  const handleAnalyze = async () => {
    if (selectedFiles.length === 0) {
      message.warning('请先选择要分析的文件')
      return
    }

    const fileCount = selectedFiles.length
    const confirmContent = fileCount === 1
      ? '确定要使用 AI 分析选中的文件吗？'
      : `确定要使用 AI 分析选中的 ${fileCount} 个文件吗？系统将自动检测文件相关性并进行智能分组分析。`

    Modal.confirm({
      title: 'AI 分析',
      content: confirmContent,
      okText: '开始分析',
      cancelText: '取消',
      onOk: async () => {
        setAnalyzing(true)
        setLoading(true)
        try {
          const response = await analyzeApi.analyze(selectedFiles)
          if (response.success && response.data) {
            // 单棵树响应
            addTree(response.data)
            // 成功弹窗，需要用户点击确认
            Modal.success({
              title: 'AI 分析成功',
              content: `思维树"${response.data.name}"已生成，包含 ${response.data.nodes.length} 个节点。`,
              okText: '查看思维树',
              onOk: () => {
                navigate(`/edit/${response.data.id}`)
              },
            })
          } else {
            throw new Error(response.error || '分析失败')
          }
        } catch (error: any) {
          // 解析错误信息
          let errorTitle = 'AI 分析失败'
          let errorContent = error.message || '未知错误'

          // 根据错误类型显示不同的提示
          if (error.message?.includes('401') || error.message?.includes('Unauthorized')) {
            errorTitle = 'API Key 无效'
            errorContent = '请检查 AI 配置中的 API Key 是否正确，或是否已过期。'
          } else if (error.message?.includes('402') || error.message?.includes('Payment')) {
            errorTitle = '账户欠费'
            errorContent = '您的 AI 服务账户余额不足，请先充值后再试。'
          } else if (error.message?.includes('404') || error.message?.includes('Not Found')) {
            errorTitle = 'API 地址错误'
            errorContent = 'AI 服务接口不存在，请检查 API 地址配置是否正确。'
          } else if (error.message?.includes('429') || error.message?.includes('Too Many')) {
            errorTitle = '请求过于频繁'
            errorContent = 'AI 服务请求频率超限，请稍后再试。'
          } else if (error.message?.includes('500') || error.message?.includes('Internal')) {
            errorTitle = 'AI 服务异常'
            errorContent = 'AI 服务内部错误，请稍后再试。'
          } else if (error.message?.includes('timeout') || error.message?.includes('超时')) {
            errorTitle = '请求超时'
            errorContent = 'AI 分析请求超时，可能是文档内容过长，请稍后再试。'
          }

          // 错误弹窗，需要用户点击确认
          Modal.error({
            title: errorTitle,
            content: errorContent,
            okText: '我知道了',
          })
        } finally {
          setAnalyzing(false)
          setLoading(false)
        }
      },
    })
  }

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>上传文件</Title>
      <Text type="secondary">
        支持 PDF、DOCX、TXT 格式的文件，文件大小不超过 50MB
      </Text>

      <Card style={{ marginTop: '24px', marginBottom: '24px' }}>
        <Dragger {...uploadProps}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">
            支持单个或批量上传，上传后可进行 AI 分析生成思维树
          </p>
        </Dragger>
      </Card>

      {files.length > 0 && (
        <Card
          title={
            <Space>
              <span>已上传文件</span>
              <Checkbox
                checked={selectedFiles.length === files.length}
                indeterminate={selectedFiles.length > 0 && selectedFiles.length < files.length}
                onChange={(e) => handleSelectAll(e.target.checked)}
              >
                全选
              </Checkbox>
            </Space>
          }
          extra={
            <Button
              type="primary"
              icon={<RobotOutlined />}
              loading={analyzing}
              disabled={selectedFiles.length === 0}
              onClick={handleAnalyze}
            >
              AI 分析 ({selectedFiles.length})
            </Button>
          }
        >
          <List
            dataSource={files}
            renderItem={(file) => (
              <List.Item
                actions={[
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => handleDelete(file.id)}
                  >
                    删除
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <Checkbox
                      checked={selectedFiles.includes(file.id)}
                      onChange={(e) => handleSelectFile(file.id, e.target.checked)}
                    >
                      {getFileIcon(file.type)}
                    </Checkbox>
                  }
                  title={file.name}
                  description={
                    <Space>
                      <Text type="secondary">
                        {file.type.toUpperCase()} 文件
                      </Text>
                      <Text type="secondary">
                        {(file.size / 1024).toFixed(2)} KB
                      </Text>
                      <Text type="secondary">
                        {new Date(file.uploadedAt).toLocaleString()}
                      </Text>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  )
}

export default FileUpload
