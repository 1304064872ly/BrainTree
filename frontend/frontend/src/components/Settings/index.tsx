/**
 * Settings 设置组件
 * ================
 *
 * 这是 AI 模型配置的设置页面组件，负责：
 * 1. 显示当前 AI 配置
 * 2. 允许用户修改配置（服务商、API Key、模型等）
 * 3. 测试 API 连接是否有效
 * 4. 保存配置到后端
 *
 * 功能特点：
 * - 服务商联动：切换服务商时自动更新模型列表和默认 API Base
 * - API Key 安全：显示脱敏值，留空不更新
 * - 连接测试：保存前可测试 API 是否有效
 * - 热更新：保存后立即生效，无需重启服务
 *
 * 使用路由：/settings
 */

// ============================================================
// 第一部分：导入依赖
// ============================================================
import React, { useState, useEffect } from 'react'  // React Hook

// Ant Design 组件
import {
  Card,        // 卡片容器
  Form,        // 表单
  Input,       // 输入框
  Select,      // 下拉选择
  Button,      // 按钮
  Space,       // 间距
  message,     // 消息提示
  Spin,        // 加载动画
  Typography,  // 排版
  Divider,     // 分割线
} from 'antd'

// Ant Design 图标
import {
  SaveOutlined,    // 保存图标
  ApiOutlined,     // API 图标
  SettingOutlined, // 设置图标
} from '@ant-design/icons'

// 导入 API 服务和类型
import { configApi, AIConfig, AIConfigUpdate } from '../../services/api'

// 导入模型配置工具函数
import {
  getProviderOptions,  // 获取服务商选项
  getModelOptions,     // 获取模型选项
  getDefaultApiBase,   // 获取默认 API Base
} from '../../utils/modelConfig'

// ============================================================
// 第二部分：解构组件
// ============================================================
const { Text } = Typography  // 排版组件
const { Option } = Select           // 下拉选项组件

// ============================================================
// 第三部分：Settings 组件
// ============================================================

/**
 * Settings 设置组件
 *
 * AI 模型配置的设置页面。
 *
 * @returns {JSX.Element} 设置页面组件
 */
const Settings: React.FC = () => {
  // ============================================================
  // 第四部分：状态定义
  // ============================================================

  // 表单实例
  const [form] = Form.useForm()

  // 加载状态
  const [loading, setLoading] = useState(false)

  // 保存状态
  const [saving, setSaving] = useState(false)

  // 测试状态
  const [testing, setTesting] = useState(false)

  // 当前配置
  const [config, setConfig] = useState<AIConfig | null>(null)

  // 当前选中的服务商
  const [currentProvider, setCurrentProvider] = useState<string>('deepseek')

  // ============================================================
  // 第五部分：数据加载
  // ============================================================

  /**
   * 加载配置
   *
   * 从后端获取当前的 AI 配置，并填充到表单中。
   * API Key 不会回显真实值，而是显示为空。
   */
  const loadConfig = async () => {
    setLoading(true)
    try {
      const res = await configApi.getConfig()
      if (res.success && res.data) {
        setConfig(res.data)  // 保存配置（包含脱敏的 API Key）
        setCurrentProvider(res.data.provider)  // 更新当前服务商

        // 填充表单（API Key 留空）
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

  /**
   * 组件挂载时加载配置
   *
   * useEffect 空依赖数组表示只在组件挂载时执行一次
   */
  useEffect(() => {
    loadConfig()
  }, [])

  // ============================================================
  // 第六部分：事件处理
  // ============================================================

  /**
   * 切换服务商
   *
   * 当用户选择不同的服务商时：
   * 1. 更新当前服务商状态
   * 2. 更新模型列表
   * 3. 更新默认 API Base
   * 4. 如果当前模型不在新服务商的列表中，选择第一个
   *
   * @param provider - 新的服务商名称
   */
  const handleProviderChange = (provider: string) => {
    setCurrentProvider(provider)

    // 获取新服务商的模型列表
    const models = getModelOptions(provider)
    // 获取新服务商的默认 API Base
    const defaultBase = getDefaultApiBase(provider)

    // 如果当前模型不在新服务商的列表中，选择第一个
    const currentModel = form.getFieldValue('model')
    const modelExists = models.some(m => m.value === currentModel)
    if (!modelExists && models.length > 0) {
      form.setFieldValue('model', models[0].value)
    }

    // 更新 API Base
    form.setFieldValue('apiBase', defaultBase)
  }

  /**
   * 保存配置
   *
   * 验证表单并保存配置到后端。
   * API Key 只有用户输入了新值才会更新。
   */
  const handleSave = async () => {
    try {
      // 验证表单
      const values = await form.validateFields()
      setSaving(true)

      // 构建更新数据
      const updateData: AIConfigUpdate = {
        provider: values.provider,
        apiBase: values.apiBase || '',
        model: values.model,
      }

      // 只有用户输入了新的 apiKey 才更新
      if (values.apiKey && values.apiKey !== '') {
        updateData.apiKey = values.apiKey
      }

      // 调用 API 保存配置
      const res = await configApi.updateConfig(updateData)
      if (res.success) {
        message.success('配置保存成功')
        // 重新加载配置（获取最新的脱敏 API Key）
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

  /**
   * 测试连接
   *
   * 测试当前配置的 API 是否有效。
   * 需要用户输入 API Key 才能测试。
   */
  const handleTest = async () => {
    try {
      // 验证表单
      const values = await form.validateFields()

      // 检查是否输入了 API Key
      if (!values.apiKey) {
        message.warning('请输入 API Key 后再测试')
        return
      }

      setTesting(true)

      // 调用测试 API
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

  // ============================================================
  // 第七部分：渲染组件
  // ============================================================

  return (
    /**
     * 设置页面布局
     *
     * - 居中显示，最大宽度 800px
     * - 卡片容器，带标题和图标
     * - 加载动画
     */
    <div style={{ padding: '24px', maxWidth: 800, margin: '0 auto' }}>
      <Card
        title={
          <Space>
            <SettingOutlined />  {/* 设置图标 */}
            <span>AI 模型配置</span>
          </Space>
        }
      >
        {/*
         * Spin 加载动画
         *
         * loading=true 时显示加载动画
         */}
        <Spin spinning={loading}>
          {/*
           * Form 表单
           *
           * layout="vertical": 垂直布局
           * initialValues: 默认值
           */}
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              provider: 'deepseek',
              model: 'deepseek-chat',
            }}
          >
            {/* ============================================================ */}
            {/* 服务商选择 */}
            {/* ============================================================ */}
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

            {/* ============================================================ */}
            {/* API Key */}
            {/* ============================================================ */}
            <Form.Item
              label={
                <Space>
                  <span>API Key</span>
                  {/* 显示当前脱敏的 API Key */}
                  {config?.apiKey && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      当前: {config.apiKey}
                    </Text>
                  )}
                </Space>
              }
              name="apiKey"
            >
              {/*
               * Input.Password 密码输入框
               *
               * placeholder: 提示文本
               * allowClear: 允许清空
               */}
              <Input.Password
                placeholder="输入新的 API Key（留空则不更新）"
                allowClear
              />
            </Form.Item>

            {/* ============================================================ */}
            {/* API Base URL */}
            {/* ============================================================ */}
            <Form.Item
              label="API Base URL（可选）"
              name="apiBase"
              extra="留空使用默认地址"
            >
              <Input placeholder="https://api.example.com/v1" allowClear />
            </Form.Item>

            {/* ============================================================ */}
            {/* 模型选择 */}
            {/* ============================================================ */}
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

            {/* ============================================================ */}
            {/* 分割线 */}
            {/* ============================================================ */}
            <Divider />

            {/* ============================================================ */}
            {/* 按钮区域 */}
            {/* ============================================================ */}
            <Form.Item>
              <Space>
                {/*
                 * 保存按钮
                 *
                 * type="primary": 主要按钮样式
                 * icon: 按钮图标
                 * loading: 加载状态
                 */}
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={handleSave}
                  loading={saving}
                >
                  保存配置
                </Button>

                {/*
                 * 测试连接按钮
                 *
                 * 默认样式
                 * icon: 按钮图标
                 * loading: 加载状态
                 */}
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

// 导出组件
export default Settings
