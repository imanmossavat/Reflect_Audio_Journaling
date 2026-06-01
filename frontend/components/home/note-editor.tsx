"use client"

import { useEffect, useRef, useState } from "react"
import { Eye, Pencil, Loader2, Check } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { StageHeader } from "./stage-header"

interface NoteEditorProps {
  onClose: () => void
  onSave: (content: string, title?: string) => Promise<void>
  isSaving: boolean
}

// Tailwind class overrides so markdown renders nicely without a typography plugin.
const markdownComponents = {
  h1: (props: React.ComponentProps<"h1">) => <h1 className="text-2xl font-semibold mt-6 mb-3 first:mt-0" {...props} />,
  h2: (props: React.ComponentProps<"h2">) => <h2 className="text-xl font-semibold mt-5 mb-2.5" {...props} />,
  h3: (props: React.ComponentProps<"h3">) => <h3 className="text-lg font-semibold mt-4 mb-2" {...props} />,
  p: (props: React.ComponentProps<"p">) => <p className="my-2.5 leading-7" {...props} />,
  ul: (props: React.ComponentProps<"ul">) => <ul className="my-2.5 ml-5 list-disc space-y-1" {...props} />,
  ol: (props: React.ComponentProps<"ol">) => <ol className="my-2.5 ml-5 list-decimal space-y-1" {...props} />,
  li: (props: React.ComponentProps<"li">) => <li className="leading-7" {...props} />,
  blockquote: (props: React.ComponentProps<"blockquote">) => (
    <blockquote className="my-3 border-l-2 border-emerald-500/60 pl-4 italic text-muted-foreground" {...props} />
  ),
  a: (props: React.ComponentProps<"a">) => <a className="text-emerald-600 underline underline-offset-2" {...props} />,
  code: (props: React.ComponentProps<"code">) => (
    <code className="rounded bg-muted px-1.5 py-0.5 text-[0.85em] font-mono" {...props} />
  ),
  pre: (props: React.ComponentProps<"pre">) => (
    <pre className="my-3 overflow-x-auto rounded-lg bg-muted p-3 text-sm" {...props} />
  ),
  hr: () => <hr className="my-5 border-border" />,
  table: (props: React.ComponentProps<"table">) => (
    <div className="my-3 overflow-x-auto">
      <table className="w-full border-collapse text-sm" {...props} />
    </div>
  ),
  th: (props: React.ComponentProps<"th">) => <th className="border border-border px-2 py-1 text-left font-medium" {...props} />,
  td: (props: React.ComponentProps<"td">) => <td className="border border-border px-2 py-1" {...props} />,
}

export function NoteEditor({ onClose, onSave, isSaving }: NoteEditorProps) {
  const [title, setTitle] = useState("")
  const [content, setContent] = useState("")
  const [isPreview, setIsPreview] = useState(false)
  const bodyRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bodyRef.current?.focus()
  }, [])

  const canSave = content.trim().length > 0 && !isSaving

  const handleSave = async () => {
    if (!canSave) return
    try {
      await onSave(content, title)
      onClose()
    } catch {
      /* error toast handled in the hook; keep the editor open so nothing is lost */
    }
  }

  return (
    <div className="flex flex-col h-full">
      <StageHeader title="New note" icon={<Pencil className="h-3.5 w-3.5 text-amber-600" />} onClose={onClose}>
        <button
          onClick={() => setIsPreview((p) => !p)}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors"
          title={isPreview ? "Switch to writing" : "Preview"}
        >
          {isPreview ? <Pencil className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
          {isPreview ? "Write" : "Preview"}
        </button>
        <button
          onClick={() => void handleSave()}
          disabled={!canSave}
          className="flex items-center gap-1.5 rounded-md bg-emerald-600 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
          {isSaving ? "Saving..." : "Save note"}
        </button>
      </StageHeader>

      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl px-8 py-10">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Untitled note"
            className="w-full bg-transparent text-3xl font-semibold placeholder:text-muted-foreground/50 focus:outline-none"
          />
          <div className="mt-6">
            {isPreview ? (
              content.trim() ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {content}
                </ReactMarkdown>
              ) : (
                <p className="text-muted-foreground italic">Nothing to preview yet.</p>
              )
            ) : (
              <textarea
                ref={bodyRef}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                onKeyDown={(e) => {
                  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                    e.preventDefault()
                    void handleSave()
                  }
                }}
                placeholder="Start writing… Markdown supported (# headings, **bold**, - lists, > quotes)."
                className="min-h-[55vh] w-full resize-none bg-transparent text-[15px] leading-7 placeholder:text-muted-foreground/50 focus:outline-none"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
