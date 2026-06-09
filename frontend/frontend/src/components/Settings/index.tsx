import React, { useState, useEffect } from 'react'
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  message,
  Spin,
  Typography,
  Divider,
} from 'antd'
import {
  SaveOutlined,
  ApiOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { configApi, AIConfig, AIConfigUpdate } from '../../services/api'
import {
  getProviderOptions,
  getModelOptions,
  getDefaultApiBase,
} from '../../utils/modelConfig'

const { Title, Text } = Typography
const { Option } = Select

const Settings: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [config, setConfig] = useState<AIConfig | null>(null)
  const [currentProvider, setCurrentProvider] = useState<string>('deepseek')

  // 加载配置
  const loadConfig = async () => {
    setLoading(true)
    try {
      const res = await configApi.getConfig()
      if (res.success && res.data) {
        setConfig(res.data)
        setCurrentProvider(res.data.provider)
        form.setFieldsValue({
          provider: res.data.provider,
          apiKey: '',  // 不回显真实 key，用户输入新 key 才会更新
          apiBase: res.data.apiBase,
          model: res.data.model,
        })
      }
    } catch (error) {
      message.error('加载配置失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadConfig()
  }, [])

  // 切换服务商时更新模型列表和默认 API Base
  const handleProviderChange = (provider: string) => {
    setCurrentProvider(provider)
    const models = getModelOptions(provider)
    const defaultBase = getDefaultApiBase(provider)

    // 如果当前模型不在新服务商的列表中，选择第一个
    const currentModel = form.getFieldValue('model')
    const modelExists = models.some(m => m.value === currentModel)
    if (!modelExists && models.length > 0) {
      form.setFieldValue('model', models[0].value)
    }

    form.setFieldValue('apiBase', defaultBase)
  }

  // 保存配置
  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)

      const updateData: AIConfigUpdate = {
        provider: values.provider,
        apiBase: values.apiBase || '',
        model: values.model,
      }

      // 只有用户输入了新的 apiKey 才更新
      if (values.apiKey && values.apiKey !== '') {
        updateData.apiKey = values.apiKey
      }

      const res = await configApi.updateConfig(updateData)
      if (res.success) {
        message.success('配置保存成功')
        // 重新加载配置
        await loadConfig()
        // 清空 apiKey 输入框
        form.setFieldValue('apiKey', '')
      } else {
        message.error(res.error || '保存失败')
      }
    } catch (error) {
      message.error('表单验证失败')
    } finally {
      setSaving(false)
    }
  }

  // 测试连接
  const handleTest = async () => {
    try {
      const values = await form.validateFields()

      if (!values.apiKey) {
        message.warning('请输入 API Key 后再测试')
        return
      }

      setTesting(true)
      const res = await configApi.testConfig({
        provider: values.provider,
        apiKey: values.apiKey,
        apiBase: values.apiBase || '',
        model: values.model,
      })

      if (res.success && res.data?.valid) {
        message.success('连接测试成功！')
      } else {
        message.error(res.error || '连接测试失败')
      }
    } catch (error) {
      message.error('表单验证失败')
    } finally {
      setTesting(false)
    }
  }

  return (
    <div style={{ padding: '24px', maxWidth: 800, margin: '0 auto' }}>
      <Card
        title={
          <Space>
            <SettingOutlined />
            <span>AI 模型配置</span>
          </Space>
        }
      >
        <Spin spinning={loading}>
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              provider: 'deepseek',
              model: 'deepseek-chat',
            }}
          >
            {/* 服务商选择 */}
            <Form.Item
              label="AI 服务商"
              name="provider"
              rules={[{ required: true, message: '请选择服务商' }]}
            >
              <Select onChange={handleProviderChange}>
                {getProviderOptions().map(option => (
                  <Option key={option.value} value={option.value}>
                    {option.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            {/* API Key */}
            <Form.Item
              label={
                <Space>
                  <span>API Key</span>
                  {config?.apiKey && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      当前: {config.apiKey}
                    </Text>
                  )}
                </Space>
              }
              name="apiKey"
            >
              <Input.Password
                placeholder="输入新的 API Key（留空则不更新）"
                allowClear
              />
            </Form.Item>

            {/* API Base URL */}
            <Form.Item
              label="API Base URL（可选）"
              name="apiBase"
              extra="留空使用默认地址"
            >
              <Input placeholder="https://api.example.com/v1" allowClear />
            </Form.Item>

            {/* 模型选择 */}
            <Form.Item
              label="模型"
              name="model"
              rules={[{ required: true, message: '请选择模型' }]}
            >
              <Select>
                {getModelOptions(currentProvider).map(model => (
                  <Option key={model.value} value={model.value}>
                    {model.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Divider />

            {/* 按钮区域 */}
            <Form.Item>
              <Space>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={handleSave}
                  loading={saving}
                >
                  保存配置
                </Button>
                <Button
                  icon={<ApiOutlined />}
                  onClick={handleTest}
                  loading={testing}
                >
                  测试连接
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Spin>
      </Card>
    </div>
  )
}

export default Settings
