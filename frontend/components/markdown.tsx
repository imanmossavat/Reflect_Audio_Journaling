"use client"

import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

interface MarkdownProps {
  children: string
  className?: string
}

/**
 * Renders Markdown text (assistant answers, reflection prompts) with GitHub-flavored
 * extensions. Styling comes from the `.markdown` rules in globals.css, mirroring `.tiptap`.
 */
export function Markdown({ children, className }: MarkdownProps) {
  return (
    <div className={`markdown${className ? ` ${className}` : ""}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, ...props }) => <a target="_blank" rel="noreferrer" {...props} />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
