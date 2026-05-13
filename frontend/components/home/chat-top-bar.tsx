"use client"

import { Upload, RotateCw, MessageSquare } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { PROCESSING_STATUS_LABELS } from "@/lib/api"
import type { ChatSummary, ChatMessageRecord } from "@/lib/api"

interface ChatTopBarProps {
  activeChat: ChatSummary
  activeChatSourceId: number | null
  activeChatLinkedSourceStatus: string | null
  isLinkedSourceProcessing: boolean
  isPromotingChat: boolean
  activeChatMessages: ChatMessageRecord[]
  onPromoteChat: () => Promise<void>
}

export function ChatTopBar({
  activeChat,
  activeChatSourceId,
  activeChatLinkedSourceStatus,
  isLinkedSourceProcessing,
  isPromotingChat,
  activeChatMessages,
  onPromoteChat,
}: ChatTopBarProps) {
  return (
    <div className="border-b bg-muted/10 px-6 py-2.5 flex items-center justify-between gap-3">
      <div className="flex items-center gap-2 min-w-0">
        <MessageSquare className="h-4 w-4 text-muted-foreground shrink-0" />
        <span className="text-sm font-medium truncate">{activeChat.title}</span>
        {activeChatSourceId !== null && (
          <Link
            href={`/sources/${activeChatSourceId}`}
            className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:underline"
          >
            indexed source
          </Link>
        )}
      </div>
      <Button
        size="sm"
        variant="outline"
        onClick={() => void onPromoteChat()}
        disabled={isPromotingChat || isLinkedSourceProcessing || activeChatMessages.length === 0}
        className="shrink-0"
      >
        {activeChatSourceId === null ? (
          <>
            <Upload className="h-3.5 w-3.5 mr-1" />
            {isPromotingChat ? "Promoting..." : "Promote to source"}
          </>
        ) : isLinkedSourceProcessing ? (
          <>
            <RotateCw className="h-3.5 w-3.5 mr-1 animate-spin" />
            {PROCESSING_STATUS_LABELS[activeChatLinkedSourceStatus ?? ""] ?? "Processing..."}
          </>
        ) : (
          <>
            <RotateCw className="h-3.5 w-3.5 mr-1" />
            {isPromotingChat ? "Re-indexing..." : "Re-index"}
          </>
        )}
      </Button>
    </div>
  )
}
