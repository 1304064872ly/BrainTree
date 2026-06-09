import React, { useEffect, useRef } from 'react'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

interface MarkdownRendererProps {
  content: string
}

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true,
})

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  const containerRef = useRef<HTMLDivElement>(null)

  if (!content) {
    return <div style={{ color: '#999', fontStyle: 'italic' }}>暂无详细解答</div>
  }

  const html = marked(content)

  // 代码高亮
  useEffect(() => {
    if (containerRef.current) {
      const codeBlocks = containerRef.current.querySelectorAll('pre code')
      codeBlocks.forEach((block) => {
        hljs.highlightElement(block as HTMLElement)
      })
    }
  }, [content])

  return (
    <div
      ref={containerRef}
      className="markdown-content"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

export default MarkdownRenderer
