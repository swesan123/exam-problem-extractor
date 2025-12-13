import React, { useMemo } from 'react'
import { InlineMath, BlockMath } from 'react-katex'
import 'katex/dist/katex.min.css'

interface LatexRendererProps {
  content: string
  className?: string
}

/**
 * Component to render LaTeX math expressions and markdown formatting in text.
 * Handles:
 * - Markdown headings (#, ##, ###, etc.)
 * - Markdown bold (**text**)
 * - Inline code (`text`)
 * - Horizontal rules (---, ***, ___)
 * - Lists (-, *, +)
 * - Code blocks (```)
 * - Inline math ($...$ or \(...\))
 * - Display math ($$...$$ or \[...\])
 */
const LatexRenderer: React.FC<LatexRendererProps> = ({ content, className = '' }) => {
  if (!content) return null

  /**
   * Process text to handle markdown and LaTeX, returning an array of React nodes
   * Processes line by line to handle block-level markdown elements
   */
  const processContent = (text: string): React.ReactNode[] => {
    let partIndex = 0

    // Split into lines for block-level processing
    const lines = text.split('\n')
    const processedLines: React.ReactNode[] = []

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]
      let processed = false

      // Check for horizontal rule (---, ***, or ___)
      if (/^(\-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
        processedLines.push(
          <hr key={`hr-${i}`} className="my-4 border-gray-300" style={{ borderTop: '1px solid #d1d5db', marginTop: '1rem', marginBottom: '1rem' }} />
        )
        processed = true
      }
      // Check for headings (#, ##, ###, etc.)
      else if (/^(#{1,6})\s+(.+)$/.test(line)) {
        const match = line.match(/^(#{1,6})\s+(.+)$/)
        if (match) {
          const level = match[1].length
          const headingText = match[2]
          const HeadingTag = `h${Math.min(level, 6)}` as keyof JSX.IntrinsicElements
          const sizeClasses = {
            1: 'text-3xl font-bold mt-6 mb-4',
            2: 'text-2xl font-bold mt-5 mb-3',
            3: 'text-xl font-bold mt-4 mb-2',
            4: 'text-lg font-bold mt-3 mb-2',
            5: 'text-base font-bold mt-2 mb-1',
            6: 'text-sm font-bold mt-2 mb-1'
          }
          processedLines.push(
            <HeadingTag key={`heading-${i}`} className={sizeClasses[level as keyof typeof sizeClasses] || sizeClasses[3]}>
              {processInlineMarkdown(headingText, partIndex++)}
            </HeadingTag>
          )
          processed = true
        }
      }
      // Check for code blocks (```)
      else if (/^```/.test(line)) {
        const codeLines: string[] = []
        let j = i + 1
        while (j < lines.length && !lines[j].startsWith('```')) {
          codeLines.push(lines[j])
          j++
        }
        if (j < lines.length) {
          processedLines.push(
            <pre key={`code-${i}`} className="bg-gray-100 p-3 rounded my-2 overflow-x-auto">
              <code className="text-sm">{codeLines.join('\n')}</code>
            </pre>
          )
          i = j // Skip to after the closing ```
          processed = true
        }
      }
      // Check for list items (-, *, +)
      else if (/^[\s]*[-*+]\s+(.+)$/.test(line)) {
        const match = line.match(/^[\s]*[-*+]\s+(.+)$/)
        if (match) {
          const indent = line.match(/^[\s]*/)?.[0].length || 0
          const listText = match[1]
          processedLines.push(
            <div key={`list-${i}`} className="flex my-1" style={{ paddingLeft: `${indent * 0.5}rem` }}>
              <span className="mr-2">•</span>
              <span>{processInlineMarkdown(listText, partIndex++)}</span>
            </div>
          )
          processed = true
        }
      }

      // If not processed as a block element, process as regular text
      if (!processed && line.trim()) {
        processedLines.push(
          <div key={`line-${i}`} className="my-1">
            {processInlineMarkdown(line, partIndex++)}
          </div>
        )
      } else if (!processed && !line.trim()) {
        // Empty line
        processedLines.push(<br key={`br-${i}`} />)
      }
    }

    return processedLines.length > 0 ? processedLines : [<span key="empty">{text}</span>]
  }

  /**
   * Process inline markdown (bold, LaTeX) within a line
   */
  const processInlineMarkdown = (text: string, baseIndex: number): React.ReactNode[] => {
    const parts: React.ReactNode[] = []
    let partIndex = baseIndex

    // First, extract and replace LaTeX math expressions with placeholders
    const mathExpressions: Array<{ placeholder: string; content: string; isDisplay: boolean }> = []
    // Pattern to match: $$...$$, $...$, \[...\], \(...\)
    // For \(...\), we need to match content that may contain backslashes (like \frac)
    const mathPattern = /(\$\$[\s\S]*?\$\$|\$[^$\n]+?\$|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\))/g
    const matches: Array<{ content: string; start: number; end: number }> = []
    let match

    // Collect all matches with their positions
    while ((match = mathPattern.exec(text)) !== null) {
      matches.push({
        content: match[0],
        start: match.index,
        end: match.index + match[0].length
      })
    }

    // Build processed text with placeholders
    let result = ''
    let lastIndex = 0
    matches.forEach((match, idx) => {
      // Add text before this match
      result += text.substring(lastIndex, match.start)
      
      // Add placeholder for this math expression
      const placeholder = `__MATH_PLACEHOLDER_${idx}__`
      result += placeholder
      
      // Extract and store the math expression
      const mathContent = match.content
      const isDisplay = mathContent.startsWith('$$') || mathContent.startsWith('\\[')
      
      let mathExpr = mathContent
      if (mathContent.startsWith('$$')) {
        mathExpr = mathContent.slice(2, -2).trim()
      } else if (mathContent.startsWith('$') && !mathContent.startsWith('$$')) {
        mathExpr = mathContent.slice(1, -1).trim()
      } else if (mathContent.startsWith('\\[')) {
        mathExpr = mathContent.slice(2, -2).trim()
      } else if (mathContent.startsWith('\\(')) {
        mathExpr = mathContent.slice(2, -2).trim()
      }
      
      mathExpressions.push({ placeholder, content: mathExpr, isDisplay })
      lastIndex = match.end
    })
    
    // Add remaining text after last match
    result += text.substring(lastIndex)

    // Process inline markdown: bold (**text**) and inline code (`text`)
    const processInlineMarkdownElements = (text: string): React.ReactNode[] => {
      const nodes: React.ReactNode[] = []
      let lastIndex = 0

      // Pattern to match both bold (**text**) and inline code (`text`)
      // We need to match them in order of appearance
      const patterns = [
        { regex: /\*\*([^*]+)\*\*/g, type: 'bold' },
        { regex: /`([^`]+)`/g, type: 'code' }
      ]

      // Collect all matches with their positions
      const allMatches: Array<{ start: number; end: number; type: string; content: string }> = []
      
      patterns.forEach(({ regex, type }) => {
        let match
        regex.lastIndex = 0 // Reset regex
        while ((match = regex.exec(text)) !== null) {
          allMatches.push({
            start: match.index,
            end: match.index + match[0].length,
            type,
            content: match[1]
          })
        }
      })

      // Sort matches by position
      allMatches.sort((a, b) => a.start - b.start)

      // Process matches in order
      allMatches.forEach((match) => {
        // Add text before this match
        if (match.start > lastIndex) {
          const textBefore = text.substring(lastIndex, match.start)
          if (textBefore) {
            nodes.push(textBefore)
          }
        }

        // Add the formatted element
        if (match.type === 'bold') {
          nodes.push(<strong key={`bold-${match.start}-${partIndex}`}>{match.content}</strong>)
        } else if (match.type === 'code') {
          nodes.push(
            <code key={`code-${match.start}-${partIndex}`} className="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono">
              {match.content}
            </code>
          )
        }

        lastIndex = match.end
      })

      // Add remaining text
      if (lastIndex < text.length) {
        const textAfter = text.substring(lastIndex)
        if (textAfter) {
          nodes.push(textAfter)
        }
      }

      return nodes.length > 0 ? nodes : [text]
    }

    // If no math expressions found, just process markdown on the whole text
    if (mathExpressions.length === 0) {
      const markdownNodes = processInlineMarkdownElements(text)
      return markdownNodes.map((node, index) => {
        if (typeof node === 'string') {
          return <span key={`text-${index}-${partIndex}`}>{node}</span>
        }
        return node
      })
    }

    // Split by math placeholders and process each segment
    const segments = result.split(/(__MATH_PLACEHOLDER_\d+__)/g)

    segments.forEach((segment: string) => {
      if (segment.startsWith('__MATH_PLACEHOLDER_') && segment.endsWith('__')) {
        // This is a math placeholder - render the math
        const placeholderNum = parseInt(segment.match(/\d+/)![0])
        const mathExpr = mathExpressions[placeholderNum]
        
        if (mathExpr) {
          try {
            if (mathExpr.isDisplay) {
              parts.push(
                <BlockMath key={`math-${partIndex}`} math={mathExpr.content} />
              )
            } else {
              parts.push(
                <InlineMath key={`math-${partIndex}`} math={mathExpr.content} />
              )
            }
          } catch (error) {
            console.warn('LaTeX parsing error:', error)
            parts.push(<span key={`error-${partIndex}`}>{segment}</span>)
          }
        } else {
          parts.push(<span key={`text-${partIndex}`}>{segment}</span>)
        }
        partIndex++
      } else if (segment) {
        // This is regular text - process markdown (bold and inline code)
        const markdownNodes = processInlineMarkdownElements(segment)
        markdownNodes.forEach((node, nodeIndex) => {
          if (typeof node === 'string') {
            parts.push(<span key={`text-${partIndex}-${nodeIndex}`}>{node}</span>)
          } else {
            parts.push(node)
          }
        })
        partIndex++
      }
    })

    return parts.length > 0 ? parts : [<span key={`empty-${partIndex}`}>{text}</span>]
  }

  // Memoize processed content to avoid re-processing on every render
  const processedParts = useMemo(() => processContent(content), [content])

  return <div className={className} style={{ backgroundColor: 'transparent' }}>{processedParts}</div>
}

export default LatexRenderer
