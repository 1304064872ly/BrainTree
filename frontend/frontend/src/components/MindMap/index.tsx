import { useRef, useState, useCallback, useEffect, useMemo } from 'react'
import { Card, Button, Space, Typography, Empty, Spin, List, Tag, Select, Tooltip } from 'antd'
import {
  ZoomInOutlined,
  ZoomOutOutlined,
  ReloadOutlined,
  FileOutlined,
  QuestionCircleOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
} from '@ant-design/icons'
import { useStore } from '../../stores'
import { MindNode, MindTree } from '../../types'
import MarkdownRenderer from '../MarkdownRenderer'
import './MindMap.css'

const { Title, Text } = Typography
const { Option } = Select

// 分支颜色配置
const BRANCH_COLORS = [
  '#1890ff', // 蓝
  '#52c41a', // 绿
  '#faad14', // 黄
  '#722ed1', // 紫
  '#eb2f96', // 粉
  '#fa541c', // 橙
  '#13c2c2', // 青
  '#2f54eb', // 靛
]

// 文字分行工具函数
const splitTextIntoLines = (text: string, maxChars: number): string[] => {
  if (!text || text.length <= maxChars) return [text || '']

  const lines: string[] = []
  let remaining = text

  while (remaining.length > 0) {
    if (remaining.length <= maxChars) {
      lines.push(remaining)
      break
    }

    // 找到合适的断点（空格、标点）
    let breakIndex = maxChars
    const breakPoints = ['，', '。', '、', ' ', '？', '！', '：', '；', '，', '。']

    for (const bp of breakPoints) {
      const idx = remaining.lastIndexOf(bp, maxChars)
      if (idx > maxChars * 0.5) {
        breakIndex = idx + 1
        break
      }
    }

    lines.push(remaining.substring(0, breakIndex))
    remaining = remaining.substring(breakIndex)
  }

  return lines
}

// 计算节点尺寸
const getNodeSize = (label: string) => {
  const maxCharsPerLine = 18
  const lines = splitTextIntoLines(label, maxCharsPerLine)
  const width = Math.max(180, maxCharsPerLine * 14 + 40)
  const height = 50 + (lines.length - 1) * 20
  return { width, height, radius: Math.max(width, height) / 2 + 20 }
}

// 径向布局算法 - 优化版本（支持多个顶级节点，防堆叠）
const calculateRadialLayout = (tree: MindTree) => {
  if (!tree || !tree.nodes.length) return { nodes: [], links: [] }

  const nodes = tree.nodes.map((node: MindNode) => ({
    ...node,
    x: 0,
    y: 0,
    branchIndex: 0,
    ...getNodeSize(node.label)
  }))

  const nodeMap = new Map(nodes.map(n => [n.id, n]))
  const childrenMap = new Map<string, string[]>()
  const parentMap = new Map<string, string>()

  // 构建父子关系
  tree.edges.forEach(edge => {
    if (!childrenMap.has(edge.source)) {
      childrenMap.set(edge.source, [])
    }
    childrenMap.get(edge.source)!.push(edge.target)
    parentMap.set(edge.target, edge.source)
  })

  // 找到所有顶级节点（没有父节点的节点，或 level=1 的节点）
  const topLevelNodes = nodes.filter(n =>
    n.level === 1 || !parentMap.has(n.id)
  )

  // 存储父子关系的边（用于绘制连接线）
  const parentChildLinks: Array<{ source: string; target: string }> = []

  // 递归布局函数
  const layoutBranch = (
    nodeId: string,
    startX: number,
    startY: number,
    angle: number,
    branchIndex: number,
    level: number
  ) => {
    const node = nodeMap.get(nodeId)
    if (!node) return

    node.x = startX
    node.y = startY
    node.branchIndex = branchIndex

    const children = childrenMap.get(nodeId) || []
    if (children.length === 0) return

    // 根据节点尺寸和子节点数量动态计算间距
    const baseDistance = level <= 1 ? 400 : 300
    const childCountFactor = Math.max(1, Math.log2(children.length + 1))
    const distance = baseDistance * childCountFactor

    // 根据子节点数量调整展开角度
    const spreadAngle = level <= 1
      ? Math.PI * 0.8
      : Math.min(Math.PI * 0.6, Math.PI * 0.3 * childCountFactor)

    // 子节点沿着父节点方向向外发散
    const startAngle = angle - spreadAngle / 2
    const angleStep = children.length === 1 ? 0 : spreadAngle / (children.length - 1)

    children.forEach((childId, index) => {
      const childAngle = children.length === 1 ? angle : startAngle + angleStep * index
      const childNode = nodeMap.get(childId)
      const childSize = childNode ? childNode.radius : 100
      const childDistance = distance + childSize + node.radius

      const childX = startX + Math.cos(childAngle) * childDistance
      const childY = startY + Math.sin(childAngle) * childDistance
      parentChildLinks.push({ source: nodeId, target: childId })
      layoutBranch(childId, childX, childY, childAngle, branchIndex, level + 1)
    })
  }

  // 根据顶级节点数量选择布局策略
  if (topLevelNodes.length === 0) {
    return { nodes: [], links: [] }
  } else if (topLevelNodes.length === 1) {
    // 单个顶级节点：以它为中心布局
    const rootNode = topLevelNodes[0]
    rootNode.x = 0
    rootNode.y = 0
    rootNode.branchIndex = 0
    layoutBranch(rootNode.id, 0, 0, 0, 0, 0)
  } else {
    // 多个顶级节点：将它们均匀分布在一个大圆上
    const maxRadius = topLevelNodes.reduce((max, n) => Math.max(max, n.radius), 0)
    const topDistance = Math.max(600, maxRadius * 3 + topLevelNodes.length * 50)
    const angleStep = (2 * Math.PI) / topLevelNodes.length

    topLevelNodes.forEach((node, index) => {
      const angle = angleStep * index - Math.PI / 2
      node.x = Math.cos(angle) * topDistance
      node.y = Math.sin(angle) * topDistance
      node.branchIndex = index % BRANCH_COLORS.length

      // 为每个顶级节点添加一个虚拟的"文档组"父节点连接（如果需要）
      // 或者直接布局子节点
      layoutBranch(node.id, node.x, node.y, angle, node.branchIndex, 1)
    })
  }

  // 多轮碰撞检测和调整（确保完全分离）
  for (let round = 0; round < 10; round++) {
    const hasCollision = resolveCollisions(nodes)
    if (!hasCollision) break
  }

  return { nodes, links: parentChildLinks }
}

// 碰撞检测函数 - 返回是否有碰撞
const resolveCollisions = (nodes: any[]): boolean => {
  let hasCollision = false
  const basePadding = 30 // 基础额外间距

  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const node1 = nodes[i]
      const node2 = nodes[j]

      // 顶级节点之间需要更大的间距
      const isBothTopLevel = node1.level === 1 && node2.level === 1
      const padding = isBothTopLevel ? basePadding * 2 : basePadding

      // 使用节点的实际尺寸计算最小距离
      const minDistance = (node1.radius || 100) + (node2.radius || 100) + padding

      const dx = node2.x - node1.x
      const dy = node2.y - node1.y
      const distance = Math.sqrt(dx * dx + dy * dy)

      if (distance < minDistance && distance > 0) {
        hasCollision = true
        // 推开重叠节点
        const overlap = minDistance - distance
        const angle = Math.atan2(dy, dx)

        // 按节点大小比例推开
        const totalRadius = (node1.radius || 100) + (node2.radius || 100)
        const ratio1 = (node2.radius || 100) / totalRadius
        const ratio2 = (node1.radius || 100) / totalRadius

        node2.x += Math.cos(angle) * overlap * ratio1
        node2.y += Math.sin(angle) * overlap * ratio1
        node1.x -= Math.cos(angle) * overlap * ratio2
        node1.y -= Math.sin(angle) * overlap * ratio2
      }
    }
  }

  return hasCollision
}

// 节点组件 - 优化版本（支持多行显示和拖拽）
const MindMapNode = ({ node, x, y, color, isExpanded, isDragging, onClick, onDragStart }: any) => {
  const maxCharsPerLine = 18
  const lines = splitTextIntoLines(node.label, maxCharsPerLine)
  const nodeWidth = node.width || Math.max(180, maxCharsPerLine * 14 + 40)
  const nodeHeight = node.height || (50 + (lines.length - 1) * 20)

  // 使用 ref 追踪拖拽状态
  const dragStateRef = useRef({ startX: 0, startY: 0, isDragging: false })

  const handleMouseDown = (e: React.MouseEvent) => {
    // 只处理左键
    if (e.button !== 0) return
    e.stopPropagation()

    // 记录起始位置
    dragStateRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      isDragging: false
    }

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const dx = Math.abs(moveEvent.clientX - dragStateRef.current.startX)
      const dy = Math.abs(moveEvent.clientY - dragStateRef.current.startY)

      // 移动超过 5 像素才认为是拖拽
      if (dx > 5 || dy > 5) {
        dragStateRef.current.isDragging = true
        onDragStart(node.id, e)
        // 拖拽开始后移除监听，交给父组件处理
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
      }
    }

    const handleMouseUp = (_upEvent: MouseEvent) => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)

      // 如果没有拖拽，则触发点击（展开卡片）
      if (!dragStateRef.current.isDragging) {
        onClick(node)
      }
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }

  return (
    <g
      transform={`translate(${x}, ${y})`}
      onMouseDown={handleMouseDown}
      className={`mind-map-node ${isDragging ? 'dragging' : ''}`}
      style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
    >
      {/* 阴影效果 */}
      <rect
        x={-nodeWidth / 2 + 2}
        y={-nodeHeight / 2 + 2}
        width={nodeWidth}
        height={nodeHeight}
        rx={12}
        ry={12}
        fill={isDragging ? 'rgba(0,0,0,0.2)' : 'rgba(0,0,0,0.1)'}
      />
      {/* 主节点 */}
      <rect
        x={-nodeWidth / 2}
        y={-nodeHeight / 2}
        width={nodeWidth}
        height={nodeHeight}
        rx={12}
        ry={12}
        fill={isExpanded ? color : '#fff'}
        stroke={color}
        strokeWidth={isDragging ? 3 : 2}
      />
      {/* 多行文字 */}
      {lines.map((line: string, i: number) => (
        <text
          key={i}
          x={0}
          y={-nodeHeight / 2 + 24 + i * 18}
          textAnchor="middle"
          dominantBaseline="middle"
          fill={isExpanded ? '#fff' : '#333'}
          fontSize={13}
          fontWeight={isExpanded ? 'bold' : 'normal'}
        >
          {line}
        </text>
      ))}
    </g>
  )
}

// 连接线组件
const MindMapLink = ({ source, target, color }: any) => {
  const dx = target.x - source.x
  const dy = target.y - source.y
  const dist = Math.sqrt(dx * dx + dy * dy)

  if (dist === 0) return null

  // 计算起点和终点（从节点边缘开始）
  const sourceRadius = 80
  const targetRadius = 80

  const startX = source.x + (dx / dist) * sourceRadius
  const startY = source.y + (dy / dist) * sourceRadius
  const endX = target.x - (dx / dist) * targetRadius
  const endY = target.y - (dy / dist) * targetRadius

  // 贝塞尔曲线控制点
  const midX = (startX + endX) / 2
  const midY = (startY + endY) / 2
  const controlX = midX + (startY - endY) * 0.2
  const controlY = midY + (endX - startX) * 0.2

  return (
    <path
      d={`M${startX},${startY} Q${controlX},${controlY} ${endX},${endY}`}
      fill="none"
      stroke={color || '#d9d9d9'}
      strokeWidth={2}
      strokeLinecap="round"
      className="mind-map-link"
    />
  )
}

// 答案展开卡片组件 - 优化版本（更大、支持 Markdown）
const AnswerCard = ({ node, x, y, color, onClose }: any) => {
  const cardWidth = 450
  const cardHeight = 380
  const cardX = x - cardWidth / 2
  const cardY = y + 50

  // 阻止滚轮事件冒泡到 SVG（让卡片内部滚动）
  const handleCardWheel = (e: React.WheelEvent) => {
    e.stopPropagation()
  }

  return (
    <g
      transform={`translate(${cardX}, ${cardY})`}
      className="answer-card-group"
      onWheel={handleCardWheel}
    >
      {/* 卡片背景 */}
      <rect
        x={0}
        y={0}
        width={cardWidth}
        height={cardHeight}
        rx={12}
        ry={12}
        fill="#fff"
        stroke={color}
        strokeWidth={2}
        filter="url(#shadow)"
      />
      {/* 标题栏 */}
      <rect
        x={0}
        y={0}
        width={cardWidth}
        height={44}
        rx={12}
        ry={12}
        fill={color}
      />
      <rect
        x={0}
        y={22}
        width={cardWidth}
        height={22}
        fill={color}
      />
      {/* 标题文字 */}
      <text
        x={cardWidth / 2}
        y={27}
        textAnchor="middle"
        fill="#fff"
        fontSize={15}
        fontWeight="bold"
      >
        {node.label.length > 30 ? node.label.substring(0, 30) + '...' : node.label}
      </text>
      {/* 关闭按钮 */}
      <g
        transform={`translate(${cardWidth - 30}, 12)`}
        onClick={(e) => {
          e.stopPropagation()
          onClose()
        }}
        style={{ cursor: 'pointer' }}
      >
        <circle cx={10} cy={10} r={10} fill="rgba(255,255,255,0.3)" />
        <text x={10} y={14} textAnchor="middle" fill="#fff" fontSize={14}>×</text>
      </g>
      {/* 答案内容 */}
      <foreignObject
        x={16}
        y={52}
        width={cardWidth - 32}
        height={cardHeight - 60}
      >
        <div className="answer-card-content">
          <MarkdownRenderer content={node.description || '暂无详细解答'} />
        </div>
      </foreignObject>
    </g>
  )
}

// 分类筛选组件
const CategoryFilter = ({ tree, selectedCategory, onSelect }: any) => {
  const categories = tree.nodes.filter((n: MindNode) => n.level === 1)

  if (categories.length === 0) return null

  return (
    <div className="category-filter">
      <Select
        placeholder="选择分类筛选"
        value={selectedCategory}
        onChange={onSelect}
        allowClear
        style={{ width: 220 }}
        size="small"
      >
        <Option value={null}>全部显示</Option>
        {categories.map((cat: MindNode) => (
          <Option key={cat.id} value={cat.id}>
            {cat.label}
          </Option>
        ))}
      </Select>
    </div>
  )
}

// 快捷键提示组件
const ShortcutHint = () => (
  <Tooltip
    title={
      <div className="shortcut-hint-content">
        <p><kbd>ESC</kbd> 关闭卡片</p>
        <p><kbd>←</kbd> <kbd>→</kbd> 切换题目</p>
        <p><kbd>↑</kbd> <kbd>↓</kbd> 切换分类</p>
        <p><kbd>Ctrl</kbd> + <kbd>+</kbd> 放大</p>
        <p><kbd>Ctrl</kbd> + <kbd>-</kbd> 缩小</p>
        <p><kbd>Ctrl</kbd> + <kbd>0</kbd> 重置视图</p>
      </div>
    }
  >
    <Button icon={<QuestionCircleOutlined />} size="small" />
  </Tooltip>
)

const MindMap = () => {
  const { trees, currentTree, setCurrentTree, loading } = useStore()
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] }>({
    nodes: [],
    links: [],
  })
  const [expandedNodeId, setExpandedNodeId] = useState<string | null>(() => {
    // 从 localStorage 恢复展开状态
    if (currentTree) {
      const saved = localStorage.getItem(`braintree-expanded-${currentTree.id}`)
      return saved ? JSON.parse(saved) : null
    }
    return null
  })
  const [viewBox, setViewBox] = useState(() => {
    // 从 localStorage 恢复视图位置
    if (currentTree) {
      const saved = localStorage.getItem(`braintree-viewbox-${currentTree.id}`)
      return saved ? JSON.parse(saved) : { x: -600, y: -500, width: 1200, height: 1000 }
    }
    return { x: -600, y: -500, width: 1200, height: 1000 }
  })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  // 节点拖拽状态
  const [draggingNode, setDraggingNode] = useState<string | null>(null)
  const [dragNodeStart, setDragNodeStart] = useState({ x: 0, y: 0 })

  // 切换全屏
  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen()
      setIsFullscreen(true)
    } else {
      document.exitFullscreen()
      setIsFullscreen(false)
    }
  }, [])

  // 监听全屏状态变化
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  // 根据选中的分类过滤节点和边
  const filteredTree = useMemo(() => {
    if (!currentTree) return null
    if (!selectedCategory) return currentTree

    const visibleNodes = new Set<string>()

    // 添加选中的分类节点
    visibleNodes.add(selectedCategory)

    // 添加所有后代节点
    const addDescendants = (nodeId: string) => {
      const children = currentTree.edges
        .filter(e => e.source === nodeId && e.type === 'contains')
        .map(e => e.target)

      // 如果没有 contains 关系的边，尝试查找所有以该节点为源的边
      if (children.length === 0) {
        currentTree.edges
          .filter(e => e.source === nodeId)
          .forEach(e => {
            visibleNodes.add(e.target)
            addDescendants(e.target)
          })
      } else {
        children.forEach(childId => {
          visibleNodes.add(childId)
          addDescendants(childId)
        })
      }
    }

    addDescendants(selectedCategory)

    return {
      ...currentTree,
      nodes: currentTree.nodes.filter(n => visibleNodes.has(n.id)),
      edges: currentTree.edges.filter(e => visibleNodes.has(e.source) && visibleNodes.has(e.target))
    }
  }, [currentTree, selectedCategory])

  // 计算布局
  useEffect(() => {
    if (filteredTree) {
      const data = calculateRadialLayout(filteredTree)
      setGraphData(data)
    }
  }, [filteredTree])

  // 保存展开状态到 localStorage
  useEffect(() => {
    if (currentTree) {
      localStorage.setItem(
        `braintree-expanded-${currentTree.id}`,
        JSON.stringify(expandedNodeId)
      )
    }
  }, [expandedNodeId, currentTree])

  // 保存视图位置到 localStorage（防抖）
  useEffect(() => {
    if (!currentTree) return

    const timer = setTimeout(() => {
      localStorage.setItem(
        `braintree-viewbox-${currentTree.id}`,
        JSON.stringify(viewBox)
      )
    }, 500)

    return () => clearTimeout(timer)
  }, [viewBox, currentTree])

  // 快捷键处理
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 忽略输入框中的快捷键
      if ((e.target as HTMLElement).tagName === 'INPUT' ||
          (e.target as HTMLElement).tagName === 'TEXTAREA') {
        return
      }

      // ESC 关闭答案卡片
      if (e.key === 'Escape' && expandedNodeId) {
        e.preventDefault()
        setExpandedNodeId(null)
      }

      // Ctrl + = 放大
      if (e.key === '=' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault()
        handleZoomIn()
      }

      // Ctrl + - 缩小
      if (e.key === '-' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault()
        handleZoomOut()
      }

      // Ctrl + 0 重置视图
      if (e.key === '0' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault()
        handleResetView()
      }

      // 左右箭头切换节点
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault()
        navigateNodes(e.key === 'ArrowRight' ? 1 : -1)
      }

      // 上下箭头切换分类
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        e.preventDefault()
        navigateCategories(e.key === 'ArrowDown' ? 1 : -1)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [expandedNodeId, filteredTree, selectedCategory])

  // 节点导航
  const navigateNodes = (direction: 1 | -1) => {
    if (!filteredTree) return

    const visibleNodes = filteredTree.nodes.filter(n => n.level >= 2)
    if (visibleNodes.length === 0) return

    const currentIndex = expandedNodeId
      ? visibleNodes.findIndex(n => n.id === expandedNodeId)
      : -1

    let nextIndex: number
    if (currentIndex === -1) {
      nextIndex = direction === 1 ? 0 : visibleNodes.length - 1
    } else {
      nextIndex = (currentIndex + direction + visibleNodes.length) % visibleNodes.length
    }

    setExpandedNodeId(visibleNodes[nextIndex].id)
  }

  // 分类导航
  const navigateCategories = (direction: 1 | -1) => {
    if (!currentTree) return

    const categories = currentTree.nodes.filter(n => n.level === 1)
    if (categories.length === 0) return

    const currentIndex = selectedCategory
      ? categories.findIndex(n => n.id === selectedCategory)
      : -1

    let nextIndex: number
    if (currentIndex === -1) {
      nextIndex = direction === 1 ? 0 : categories.length - 1
    } else {
      nextIndex = (currentIndex + direction + categories.length) % categories.length
    }

    setSelectedCategory(categories[nextIndex].id)
  }

  const handleNodeClick = useCallback((node: any) => {
    setExpandedNodeId(prev => prev === node.id ? null : node.id)
  }, [])

  const handleBackgroundClick = useCallback(() => {
    setExpandedNodeId(null)
  }, [])

  const handleZoomIn = () => {
    setViewBox((prev: any) => ({
      x: prev.x + prev.width * 0.1,
      y: prev.y + prev.height * 0.1,
      width: prev.width * 0.8,
      height: prev.height * 0.8,
    }))
  }

  const handleZoomOut = () => {
    setViewBox((prev: any) => ({
      x: prev.x - prev.width * 0.1,
      y: prev.y - prev.height * 0.1,
      width: prev.width * 1.2,
      height: prev.height * 1.2,
    }))
  }

  const handleResetView = () => {
    setViewBox({ x: -600, y: -500, width: 1200, height: 1000 })
    setExpandedNodeId(null)
  }

  // 节点拖拽开始
  const handleNodeDragStart = useCallback((nodeId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const node = graphData.nodes.find(n => n.id === nodeId)
    if (!node) return

    setDraggingNode(nodeId)
    setDragNodeStart({ x: e.clientX, y: e.clientY })
    setIsDragging(false) // 防止画布拖拽
  }, [graphData.nodes])

  // 节点拖拽中
  const handleNodeDragMove = useCallback((e: React.MouseEvent) => {
    if (!draggingNode) return

    // 计算鼠标移动的像素差
    const dx = e.clientX - dragNodeStart.x
    const dy = e.clientY - dragNodeStart.y

    // 转换为 SVG 坐标差（考虑缩放比例）
    const svgContainer = svgRef.current
    if (!svgContainer) return

    const rect = svgContainer.getBoundingClientRect()
    const scaleX = viewBox.width / rect.width
    const scaleY = viewBox.height / rect.height

    const svgDx = dx * scaleX
    const svgDy = dy * scaleY

    // 更新节点位置
    setGraphData(prev => ({
      ...prev,
      nodes: prev.nodes.map(node =>
        node.id === draggingNode
          ? { ...node, x: node.x + svgDx, y: node.y + svgDy }
          : node
      )
    }))

    setDragNodeStart({ x: e.clientX, y: e.clientY })
  }, [draggingNode, dragNodeStart, viewBox])

  // 节点拖拽结束
  const handleNodeDragEnd = useCallback(() => {
    setDraggingNode(null)
  }, [])

  // 画布拖拽开始
  const handleMouseDown = (e: React.MouseEvent) => {
    // 如果正在拖拽节点，不处理画布拖拽
    if (draggingNode) return

    setIsDragging(true)
    setDragStart({ x: e.clientX, y: e.clientY })
  }

  // 画布拖拽中
  const handleMouseMove = (e: React.MouseEvent) => {
    // 优先处理节点拖拽
    if (draggingNode) {
      handleNodeDragMove(e)
      return
    }

    if (!isDragging) return

    const dx = (e.clientX - dragStart.x) * (viewBox.width / 1200)
    const dy = (e.clientY - dragStart.y) * (viewBox.height / 1000)

    setViewBox((prev: any) => ({
      ...prev,
      x: prev.x - dx,
      y: prev.y - dy,
    }))

    setDragStart({ x: e.clientX, y: e.clientY })
  }

  // 鼠标松开
  const handleMouseUp = () => {
    if (draggingNode) {
      handleNodeDragEnd()
    }
    setIsDragging(false)
  }

  const handleWheel = useCallback((e: React.WheelEvent) => {
    const factor = e.deltaY > 0 ? 1.1 : 0.9
    setViewBox((prev: any) => ({
      x: prev.x + prev.width * (1 - factor) / 2,
      y: prev.y + prev.height * (1 - factor) / 2,
      width: prev.width * factor,
      height: prev.height * factor,
    }))
  }, [])

  const handleSelectTree = (tree: MindTree) => {
    setCurrentTree(tree)
    setSelectedCategory(null)
  }

  const handleCategoryChange = (value: string | null) => {
    setSelectedCategory(value)
    setExpandedNodeId(null)
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    )
  }

  // 如果没有选中思维树，显示思维树列表供选择
  if (!currentTree) {
    return (
      <div style={{ padding: '24px' }}>
        <Title level={2}>思维图谱</Title>
        <Text type="secondary" style={{ display: 'block', marginBottom: '24px' }}>
          选择一个思维树来查看思维导图
        </Text>

        {trees.length === 0 ? (
          <Empty
            description={
              <span>
                暂无思维树
                <br />
                <Text type="secondary">请先上传文件并进行 AI 分析，或手动创建思维树</Text>
              </span>
            }
          />
        ) : (
          <List
            grid={{ gutter: 16, column: 3 }}
            dataSource={trees}
            renderItem={(tree) => (
              <List.Item>
                <Card
                  hoverable
                  onClick={() => handleSelectTree(tree)}
                  style={{ cursor: 'pointer' }}
                >
                  <Card.Meta
                    avatar={<FileOutlined style={{ fontSize: '24px', color: '#1890ff' }} />}
                    title={tree.name}
                    description={
                      <Space direction="vertical" size="small">
                        <Text type="secondary">{tree.description || '暂无描述'}</Text>
                        <Space>
                          <Tag color="blue">{tree.nodes.length} 个节点</Tag>
                          <Tag color="green">{tree.edges.length} 条连接</Tag>
                        </Space>
                      </Space>
                    }
                  />
                </Card>
              </List.Item>
            )}
          />
        )}
      </div>
    )
  }

  const nodePositions = new Map(graphData.nodes.map(n => [n.id, n]))
  const expandedNode = expandedNodeId ? nodePositions.get(expandedNodeId) : null
  const expandedNodeColor = expandedNode ? BRANCH_COLORS[expandedNode.branchIndex || 0] : '#1890ff'

  return (
    <div
      ref={containerRef}
      className={isFullscreen ? 'mind-map-fullscreen' : ''}
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
    >
      <Card
        className="mind-map-header"
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              {currentTree.name}
            </Title>
            <Text type="secondary">
              {filteredTree?.nodes.length || 0} 个节点 · {filteredTree?.edges.length || 0} 条连接
            </Text>
          </Space>
        }
        extra={
          <Space>
            {/* 多棵树选择器 */}
            {trees.length > 1 && (
              <Select
                placeholder="选择思维树"
                value={currentTree.id}
                onChange={(treeId) => {
                  const tree = trees.find(t => t.id === treeId)
                  if (tree) {
                    setCurrentTree(tree)
                    setSelectedCategory(null)
                    setExpandedNodeId(null)
                  }
                }}
                style={{ width: 200 }}
                size="small"
              >
                {trees.map((tree) => (
                  <Option key={tree.id} value={tree.id}>
                    {tree.name}
                  </Option>
                ))}
              </Select>
            )}
            <CategoryFilter
              tree={currentTree}
              selectedCategory={selectedCategory}
              onSelect={handleCategoryChange}
            />
            <ShortcutHint />
            <Button icon={<ZoomInOutlined />} onClick={handleZoomIn} />
            <Button icon={<ZoomOutOutlined />} onClick={handleZoomOut} />
            <Button icon={<ReloadOutlined />} onClick={handleResetView} />
            <Button
              icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
              onClick={toggleFullscreen}
            />
            <Button onClick={() => setCurrentTree(null)}>返回列表</Button>
          </Space>
        }
        style={{ marginBottom: '16px' }}
      >
        <Text type="secondary">{currentTree.description || '暂无描述'}</Text>
      </Card>

      <Card style={{ flex: 1, overflow: 'hidden' }}>
        <div className="mind-map-svg-container" style={{ height: isFullscreen ? 'calc(100vh - 120px)' : '600px', position: 'relative' }}>
          {graphData.nodes.length > 0 ? (
            <svg
              ref={svgRef}
              width="100%"
              height="100%"
              viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onWheel={handleWheel}
              style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
              className="mind-map-svg"
            >
              {/* 定义阴影滤镜 */}
              <defs>
                <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
                  <feDropShadow dx="2" dy="2" stdDeviation="4" floodOpacity="0.2" />
                </filter>
              </defs>

              {/* 背景透明矩形 - 用于捕获背景点击 */}
              <rect
                x={viewBox.x}
                y={viewBox.y}
                width={viewBox.width}
                height={viewBox.height}
                fill="transparent"
                onClick={handleBackgroundClick}
              />

              {/* 绘制连接线 */}
              {graphData.links.map((link, i) => {
                const source = nodePositions.get(link.source)
                const target = nodePositions.get(link.target)
                if (!source || !target) return null
                const color = BRANCH_COLORS[target.branchIndex || 0]
                return (
                  <MindMapLink
                    key={i}
                    source={source}
                    target={target}
                    color={color}
                  />
                )
              })}

              {/* 绘制节点 */}
              {graphData.nodes.map((node) => {
                const color = BRANCH_COLORS[node.branchIndex || 0]
                return (
                  <MindMapNode
                    key={node.id}
                    node={node}
                    x={node.x}
                    y={node.y}
                    color={color}
                    isExpanded={expandedNodeId === node.id}
                    isDragging={draggingNode === node.id}
                    onClick={handleNodeClick}
                    onDragStart={handleNodeDragStart}
                  />
                )
              })}

              {/* 绘制展开的答案卡片 */}
              {expandedNode && (
                <AnswerCard
                  node={expandedNode}
                  x={expandedNode.x}
                  y={expandedNode.y}
                  color={expandedNodeColor}
                  onClose={() => setExpandedNodeId(null)}
                />
              )}
            </svg>
          ) : (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
              <Empty description="暂无节点数据" />
            </div>
          )}
        </div>
      </Card>

      <Card style={{ marginTop: '16px' }}>
        <Space>
          <Text strong>分支颜色:</Text>
          {BRANCH_COLORS.slice(0, 6).map((color, i) => (
            <Space key={i}>
              <span style={{ display: 'inline-block', width: '12px', height: '12px', background: color, borderRadius: '50%' }} />
              <Text>分支 {i + 1}</Text>
            </Space>
          ))}
        </Space>
      </Card>
    </div>
  )
}

export default MindMap
