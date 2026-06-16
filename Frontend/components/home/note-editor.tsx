"use client"

import { useEffect, useState } from "react"
import { Pencil, Loader2, Check } from "lucide-react"
import { EditorContent, useEditor } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import { Placeholder } from "@tiptap/extensions"
import { StageHeader } from "./stage-header"

interface NoteEditorProps {
  onClose: () => void
  onSave: (content: string, title?: string) => Promise<void>
  isSaving: boolean
}

export function NoteEditor({ onClose, onSave, isSaving }: NoteEditorProps) {
  const [title, setTitle] = useState("")
  const [content, setContent] = useState("")

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: "Start writing…" }),
    ],
    content: "",
    immediatelyRender: false,
    editorProps: {
      attributes: {
        class:
          "tiptap min-h-[55vh] w-full bg-transparent text-[15px] leading-7 focus:outline-none",
      },
    },
    onUpdate: ({ editor }) => {
      // Store rich HTML — the backend strips it to plain text for RAG.
      setContent(editor.isEmpty ? "" : editor.getHTML())
    },
  })

  useEffect(() => {
    editor?.commands.focus()
  }, [editor])

  const isEmpty = editor?.isEmpty ?? true
  const canSave = !isEmpty && !isSaving

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
          onClick={() => void handleSave()}
          disabled={!canSave}
          className="flex items-center gap-1.5 rounded-md bg-emerald-600 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
          {isSaving ? "Saving..." : "Save note"}
        </button>
      </StageHeader>

      <div
        className="flex-1 min-h-0 overflow-y-auto"
        onKeyDown={(e) => {
          if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
            e.preventDefault()
            void handleSave()
          }
        }}
      >
        <div className="mx-auto w-full max-w-3xl px-8 py-10">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Untitled note"
            className="w-full bg-transparent text-3xl font-semibold placeholder:text-muted-foreground/50 focus:outline-none"
          />
          <div className="mt-6">
            <EditorContent editor={editor} />
          </div>
        </div>
      </div>
    </div>
  )
}
