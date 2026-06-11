import { useState, useEffect, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  Typography,
  message,
  Divider,
  List,
  Modal,
  Tag,
} from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  SaveOutlined,
  LinkOutlined,
} from '@ant-design/icons'
import { useStore } from '../../stores'
import { MindNode, MindEdge } from '../../types'
import { generateId, NODE_TYPE_CONFIG, NODE_TYPE_OPTIONS, NODE_LEVEL_OPTIONS } from '../../utils'
import { TreeNotFound, PageHeader } from '../common'

const { Text } = Typography
const { TextArea } = Input
const { Option } = Select

const NodeEditor = () => {
  const { id } = useParams<{ id: string }>()
  const { trees, updateTree } = useStore()
  const [form] = Form.useForm()
  const [edgeForm] = Form.useForm()
  const [selectedNode, setSelectedNode] = useState<MindNode | null>(null)
  const [isEdgeModalOpen, setIsEdgeModalOpen] = useState(false)
  const [editingEdge, setEditingEdge] = useState<MindEdge | null>(null)

  const tree = useMemo(() => trees.find((t) => t.id === id), [trees, id])
  const nodeMap = useMemo(
    () => new Map(tree?.nodes.map((n) => [n.id, n]) || []),
    [tree?.nodes]
  )

  useEffect(() => {
    if (tree && tree.nodes.length > 0 && !selectedNode) {
      setSelectedNode(tree.nodes[0])
      form.setFieldsValue(tree.nodes[0])
    }
  }, [tree?.id, tree?.nodes.length])

  if (!tree) {
    return <TreeNotFound />
  }

  const handleNodeSelect = (node: MindNode) => {
    setSelectedNode(node)
    form.setFieldsValue(node)
  }

  const handleAddNode = () => {
    const newNode: MindNode = {
      id: generateId(),
      label: '新节点',
      description: '',
      type: 'concept',
      level: 1,
      position: { x: 0, y: 0 },
      metadata: {},
    }

    updateTree(tree.id, { nodes: [...tree.nodes, newNode] })
    setSelectedNode(newNode)
    form.setFieldsValue(newNode)
    message.success('节点添加成功')
  }

  const handleDeleteNode = () => {
    if (!selectedNode) return

    Modal.confirm({
      title: '确认删除',
      content: `确定要删除节点"${selectedNode.label}"吗？相关的连接也会被删除。`,
      onOk: () => {
        updateTree(tree.id, {
          nodes: tree.nodes.filter((n) => n.id !== selectedNode.id),
          edges: tree.edges.filter(
            (e) => e.source !== selectedNode.id && e.target !== selectedNode.id
          ),
        })
        setSelectedNode(null)
        form.resetFields()
        message.success('节点删除成功')
      },
    })
  }

  const handleSaveNode = (values: any) => {
    if (!selectedNode) return

    const updatedNodes = tree.nodes.map((n) =>
      n.id === selectedNode.id ? { ...n, ...values } : n
    )

    updateTree(tree.id, { nodes: updatedNodes })
    setSelectedNode({ ...selectedNode, ...values })
    message.success('节点保存成功')
  }

  const handleAddEdge = () => {
    setEditingEdge(null)
    edgeForm.resetFields()
    setIsEdgeModalOpen(true)
  }

  const handleEditEdge = (edge: MindEdge) => {
    setEditingEdge(edge)
    edgeForm.setFieldsValue(edge)
    setIsEdgeModalOpen(true)
  }

  const handleDeleteEdge = (edgeId: string) => {
    updateTree(tree.id, { edges: tree.edges.filter((e) => e.id !== edgeId) })
    message.success('连接删除成功')
  }

  const handleSaveEdge = (values: any) => {
    let updatedEdges: MindEdge[]

    if (editingEdge) {
      updatedEdges = tree.edges.map((e) =>
        e.id === editingEdge.id ? { ...e, ...values } : e
      )
    } else {
      const newEdge: MindEdge = {
        id: generateId(),
        ...values,
      }
      updatedEdges = [...tree.edges, newEdge]
    }

    updateTree(tree.id, { edges: updatedEdges })
    setIsEdgeModalOpen(false)
    message.success(editingEdge ? '连接更新成功' : '连接添加成功')
  }

  const nodeEdges = selectedNode
    ? tree.edges.filter(
        (e) => e.source === selectedNode.id || e.target === selectedNode.id
      )
    : []

  return (
    <div style={{ padding: '24px' }}>
      <PageHeader title={`编辑思维树: ${tree.name}`} />

      <div style={{ display: 'flex', gap: '24px' }}>
        {/* 左侧节点列表 */}
        <Card
          title="节点列表"
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddNode}>
              添加节点
            </Button>
          }
          style={{ width: '300px' }}
        >
          <List
            dataSource={tree.nodes}
            renderItem={(node) => (
              <List.Item
                style={{
                  cursor: 'pointer',
                  background: selectedNode?.id === node.id ? '#e6f7ff' : 'transparent',
                  padding: '8px',
                  borderRadius: '4px',
                }}
                onClick={() => handleNodeSelect(node)}
              >
                <Space>
                  <Tag color={NODE_TYPE_CONFIG[node.type]?.color ?? 'purple'}>
                    {NODE_TYPE_CONFIG[node.type]?.label ?? node.type}
                  </Tag>
                  <Text>{node.label}</Text>
                </Space>
              </List.Item>
            )}
          />
        </Card>

        {/* 右侧编辑区域 */}
        <Card title="节点编辑" style={{ flex: 1 }}>
          {selectedNode ? (
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSaveNode}
              initialValues={selectedNode}
            >
              <Form.Item
                name="label"
                label="节点名称"
                rules={[{ required: true, message: '请输入节点名称' }]}
              >
                <Input placeholder="请输入节点名称" />
              </Form.Item>

              <Form.Item name="description" label="节点描述">
                <TextArea rows={4} placeholder="请输入节点描述" />
              </Form.Item>

              <Form.Item name="type" label="节点类型">
                <Select>
                  {NODE_TYPE_OPTIONS.map(({ value, label }) => (
                    <Option key={value} value={value}>{label}</Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item name="level" label="层级">
                <Select>
                  {NODE_LEVEL_OPTIONS.map(({ value, label }) => (
                    <Option key={value} value={value}>{label}</Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" icon={<SaveOutlined />}>
                    保存
                  </Button>
                  <Button danger icon={<DeleteOutlined />} onClick={handleDeleteNode}>
                    删除节点
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          ) : (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <Text type="secondary">请选择一个节点进行编辑</Text>
            </div>
          )}

          <Divider />

          <Card
            title="节点连接"
            extra={
              <Button icon={<PlusOutlined />} onClick={handleAddEdge}>
                添加连接
              </Button>
            }
          >
            <List
              dataSource={nodeEdges}
              renderItem={(edge) => {
                const sourceNode = nodeMap.get(edge.source)
                const targetNode = nodeMap.get(edge.target)
                return (
                  <List.Item
                    actions={[
                      <Button
                        type="link"
                        onClick={() => handleEditEdge(edge)}
                      >
                        编辑
                      </Button>,
                      <Button
                        type="link"
                        danger
                        onClick={() => handleDeleteEdge(edge.id)}
                      >
                        删除
                      </Button>,
                    ]}
                  >
                    <Space>
                      <LinkOutlined />
                      <Text>
                        {sourceNode?.label} → {targetNode?.label}
                      </Text>
                      <Tag>{edge.label}</Tag>
                    </Space>
                  </List.Item>
                )
              }}
            />
          </Card>
        </Card>
      </div>

      <Modal
        title={editingEdge ? '编辑连接' : '添加连接'}
        open={isEdgeModalOpen}
        onOk={() => edgeForm.submit()}
        onCancel={() => setIsEdgeModalOpen(false)}
        okText="保存"
        cancelText="取消"
      >
        <Form form={edgeForm} layout="vertical" onFinish={handleSaveEdge}>
          <Form.Item
            name="source"
            label="起始节点"
            rules={[{ required: true, message: '请选择起始节点' }]}
          >
            <Select placeholder="请选择起始节点">
              {tree.nodes.map((node) => (
                <Option key={node.id} value={node.id}>
                  {node.label}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="target"
            label="目标节点"
            rules={[{ required: true, message: '请选择目标节点' }]}
          >
            <Select placeholder="请选择目标节点">
              {tree.nodes.map((node) => (
                <Option key={node.id} value={node.id}>
                  {node.label}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="label"
            label="连接标签"
            rules={[{ required: true, message: '请输入连接标签' }]}
          >
            <Input placeholder="请输入连接标签" />
          </Form.Item>

          <Form.Item name="type" label="连接类型">
            <Select>
              <Option value="contains">包含</Option>
              <Option value="relates">相关</Option>
              <Option value="depends">依赖</Option>
              <Option value="examples">示例</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default NodeEditor
