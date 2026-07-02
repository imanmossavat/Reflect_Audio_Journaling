"use client"

import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

interface MarkdownProps {
  children: string
  className?: string
  /** `source_id:unit_id` -> unit text, for inline reflection citation tokens. The caller
   * pre-converts literal `{{source_id:unit_id}}` text into `[·](cite:source_id:unit_id)`
   * links (see chat-messages.tsx) before passing `children` in — real markdown links are
   * unaffected, only `cite:` hrefs are intercepted. */
  citations?: Record<string, string>
}

/**
 * Renders Markdown text (assistant answers, reflection prompts) with GitHub-flavored
 * extensions. Styling comes from the `.markdown` rules in globals.css, mirroring `.tiptap`.
 */
export function Markdown({ children, className, citations }: MarkdownProps) {
  return (
    <div className={`markdown${className ? ` ${className}` : ""}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, href, ...props }) => {
            if (href?.startsWith("cite:")) {
              const unitText = citations?.[href.slice(5)]
              // Unresolved (e.g. a reloaded chat — citations aren't persisted, only
              // available for the live session) — fail gracefully, show nothing rather
              // than a dead/misleading marker.
              if (!unitText) return null
              return (
                <sup
                  title={unitText}
                  className="mx-0.5 inline-flex h-3.5 w-3.5 cursor-help select-none items-center justify-center rounded-full border border-emerald-600/40 bg-emerald-50 align-super text-[8px] font-semibold text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400"
                >
                  i
                </sup>
              )
            }
            return <a target="_blank" rel="noreferrer" href={href} {...props} />
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
