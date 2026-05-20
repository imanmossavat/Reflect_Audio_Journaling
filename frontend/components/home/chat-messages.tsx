"use client"

import type { ChatMessageRecord } from "@/lib/api"
import { formatListTimestamp } from "@/lib/utils"

interface ChatMessagesProps {
  activeChatMessages: ChatMessageRecord[]
  isLoadingActiveChat: boolean
  isAssistantThinking: boolean
}

export function ChatMessages({ activeChatMessages, isLoadingActiveChat, isAssistantThinking }: ChatMessagesProps) {
  return (
    <div className="flex-1 min-h-0 overflow-y-auto no-scrollbar p-6">
      <div className="max-w-2xl mx-auto space-y-4">
        {isLoadingActiveChat ? (
          <p className="text-sm text-muted-foreground text-center">Loading chat...</p>
        ) : (
          activeChatMessages.map((message) => {
            const timestamp = formatListTimestamp(message.created_at)
            if (message.role === "question") {
              return (
                <div key={message.id} className="flex justify-start">
                  <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3 max-w-[85%]">
                    <span className="text-xs text-emerald-600 font-medium block mb-1">REFLECT</span>
                    <p className="text-[15px] whitespace-pre-wrap">{message.text}</p>
                    <div className="flex items-center justify-start gap-2 mt-1.5">
                      <span className="text-[10px] text-muted-foreground">{timestamp}</span>
                    </div>
                  </div>
                </div>
              )
            }
            const answerText =
              message.scale_value !== null && message.scale_value !== undefined
                ? `${message.scale_value}/${message.scale_max ?? 10}`
                : message.text
            return (
              <div key={message.id} className="flex justify-end">
                <div className="bg-emerald-900 text-white rounded-2xl rounded-tr-sm px-4 py-3 max-w-[85%]">
                  <p className="text-[15px] whitespace-pre-wrap">{answerText}</p>
                  <div className="flex items-center justify-end gap-2 mt-1.5">
                    <span className="text-[10px] text-white/70">{timestamp}</span>
                  </div>
                </div>
              </div>
            )
          })
        )}

        {isAssistantThinking && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3">
              <span className="text-xs text-emerald-600 font-medium block mb-1">REFLECT</span>
              <div className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:-0.3s]" />
                <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:-0.15s]" />
                <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce" />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
