"use client"

import { MessageSquare, Pencil } from "lucide-react"
import Link from "next/link"
import type { ChatSummary } from "@/lib/api"

interface ChatTopBarProps {
  activeChat: ChatSummary
  activeChatSourceId: number | null
  isRenamingTitle: boolean
  titleDraft: string
  setTitleDraft: (v: string) => void
  onStartRenameTitle: () => void
  onCommitRenameTitle: () => void
  onCancelRenameTitle: () => void
}

export function ChatTopBar({
  activeChat,
  activeChatSourceId,
  isRenamingTitle,
  titleDraft,
  setTitleDraft,
  onStartRenameTitle,
  onCommitRenameTitle,
  onCancelRenameTitle,
}: ChatTopBarProps) {
  return (
    <div className="border-b bg-muted/10 px-6 h-12 flex items-center gap-3 shrink-0">
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <MessageSquare className="h-4 w-4 text-muted-foreground shrink-0" />
        {isRenamingTitle ? (
          <input
            autoFocus
            value={titleDraft}
            onChange={(e) => setTitleDraft(e.target.value)}
            onBlur={onCommitRenameTitle}
            onKeyDown={(e) => {
              if (e.key === "Enter") onCommitRenameTitle()
              else if (e.key === "Escape") onCancelRenameTitle()
            }}
            className="text-sm font-medium bg-background border rounded px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-emerald-500 min-w-0 flex-1 max-w-md"
          />
        ) : (
          <button
            type="button"
            onDoubleClick={onStartRenameTitle}
            className="group flex items-center gap-1.5 min-w-0 text-left hover:text-emerald-600 transition-colors"
          >
            <span className="text-sm font-medium truncate">{activeChat.title}</span>
            <Pencil
              className="h-3 w-3 opacity-0 group-hover:opacity-60 shrink-0"
              onClick={(e) => {
                e.stopPropagation()
                onStartRenameTitle()
              }}
            />
          </button>
        )}
        {activeChatSourceId !== null && (
          <Link
            href={`/sources/${activeChatSourceId}`}
            className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:underline shrink-0"
          >
            saved as source
          </Link>
        )}
      </div>
    </div>
  )
}
