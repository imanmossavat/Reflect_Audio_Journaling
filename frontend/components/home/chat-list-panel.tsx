"use client"

import { Plus, MessageSquare, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import type { ChatSummary } from "@/lib/api"

interface ChatListPanelProps {
  chats: ChatSummary[]
  isLoadingChats: boolean
  activeChatId: number | null
  renamingChatId: number | null
  renameDraft: string
  setRenameDraft: (v: string) => void
  onNewChat: () => void
  onSelectChat: (id: number) => void
  onStartRenameChat: (chat: ChatSummary, e: React.MouseEvent) => void
  onCommitRename: (id: number) => Promise<void>
  onCancelRename: () => void
  onDeleteChat: (chat: ChatSummary, e: React.MouseEvent) => Promise<void>
}

export function ChatListPanel({
  chats,
  isLoadingChats,
  activeChatId,
  renamingChatId,
  renameDraft,
  setRenameDraft,
  onNewChat,
  onSelectChat,
  onStartRenameChat,
  onCommitRename,
  onCancelRename,
  onDeleteChat,
}: ChatListPanelProps) {
  return (
    <>
      <div className="p-4 border-b">
        <Button
          onClick={onNewChat}
          size="sm"
          className="w-full bg-emerald-600 hover:bg-emerald-700"
        >
          <Plus className="h-4 w-4 mr-1" />
          New chat
        </Button>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto no-scrollbar p-2 space-y-1">
        {isLoadingChats ? (
          Array.from({ length: 3 }).map((_, index) => (
            <div key={`chat-skeleton-${index}`} className="p-2.5 rounded-lg bg-background/40">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-20 mt-1" />
            </div>
          ))
        ) : chats.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-6 px-4">
            No chats yet. Click &quot;New chat&quot; to start a reflection.
          </p>
        ) : (
          chats.map((chat) => {
            const isActive = chat.id === activeChatId
            const isRenaming = chat.id === renamingChatId
            return (
              <div
                key={chat.id}
                onClick={() => !isRenaming && onSelectChat(chat.id)}
                onDoubleClick={(e) => onStartRenameChat(chat, e)}
                className={`group p-2.5 rounded-lg cursor-pointer transition-colors ${
                  isActive ? "bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-300/60" : "hover:bg-muted/50"
                }`}
              >
                <div className="flex items-start gap-2">
                  <MessageSquare className="h-3.5 w-3.5 mt-0.5 shrink-0 text-muted-foreground" />
                  <div className="flex-1 min-w-0">
                    {isRenaming ? (
                      <input
                        autoFocus
                        value={renameDraft}
                        onChange={(e) => setRenameDraft(e.target.value)}
                        onBlur={() => void onCommitRename(chat.id)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            void onCommitRename(chat.id)
                          } else if (e.key === "Escape") {
                            onCancelRename()
                          }
                        }}
                        className="w-full text-sm font-medium bg-background border rounded px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : (
                      <p className="text-sm font-medium truncate">{chat.title}</p>
                    )}
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className="text-[10px] text-muted-foreground">
                        {chat.message_count} message{chat.message_count === 1 ? "" : "s"}
                      </span>
                      {chat.source_id !== null && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                          indexed
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={(e) => void onDeleteChat(chat, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-muted text-muted-foreground hover:text-destructive transition-opacity"
                    aria-label={`Delete chat ${chat.title}`}
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </>
  )
}
