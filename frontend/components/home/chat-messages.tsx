"use client"

import { Skeleton } from "@/components/ui/skeleton"
import type { ChatMessageRecord } from "@/lib/api"
import type { CurrentQuestion } from "./types"

interface ChatMessagesProps {
  activeChatMessages: ChatMessageRecord[]
  activeChatId: number | null
  isLoadingActiveChat: boolean
  isGeneratingQuestion: boolean
  currentQuestion: CurrentQuestion | null
  onScaleSelect: (value: number) => Promise<void>
}

export function ChatMessages({
  activeChatMessages,
  activeChatId,
  isLoadingActiveChat,
  isGeneratingQuestion,
  currentQuestion,
  onScaleSelect,
}: ChatMessagesProps) {
  return (
    <div className="flex-1 min-h-0 overflow-y-auto no-scrollbar p-6">
      <div className="max-w-2xl mx-auto space-y-4">
        {isLoadingActiveChat ? (
          <p className="text-sm text-muted-foreground text-center">Loading chat...</p>
        ) : (
          (() => {
            const items: React.ReactNode[] = []
            let pendingQuestion: ChatMessageRecord | null = null
            activeChatMessages.forEach((message) => {
              if (message.role === "question") {
                pendingQuestion = message
                return
              }
              const answerText =
                message.scale_value !== null && message.scale_value !== undefined
                  ? `${message.scale_value}/${message.scale_max ?? 10}`
                  : message.text
              const timestamp = new Date(message.created_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })
              items.push(
                <div key={message.id} className="space-y-2">
                  {pendingQuestion && (
                    <div className="flex justify-start">
                      <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3 max-w-[85%]">
                        <span className="text-xs text-emerald-600 font-medium block mb-1">REFLECT</span>
                        <p className="text-[15px]">{pendingQuestion.text}</p>
                      </div>
                    </div>
                  )}
                  <div className="flex justify-end">
                    <div className="bg-emerald-900 text-white rounded-2xl rounded-tr-sm px-4 py-3 max-w-[85%]">
                      <p className="text-[15px] whitespace-pre-wrap">{answerText}</p>
                      <div className="flex items-center justify-end gap-2 mt-1.5">
                        <span className="text-[10px] text-white/70">{timestamp}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )
              pendingQuestion = null
            })
            if (pendingQuestion !== null) {
              const q = pendingQuestion as ChatMessageRecord
              items.push(
                <div key={`pending-${q.id}`} className="flex justify-start">
                  <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3 max-w-[85%]">
                    <span className="text-xs text-emerald-600 font-medium block mb-1">REFLECT</span>
                    <p className="text-[15px]">{q.text}</p>
                  </div>
                </div>
              )
            }
            return items
          })()
        )}

        {isGeneratingQuestion &&
          currentQuestion &&
          currentQuestion.type !== "quantitative" &&
          !currentQuestion.content.trim() && (
            <div className="space-y-2">
              <div className="flex justify-start">
                <div className="w-full rounded-2xl rounded-tl-sm px-4 py-3 border border-emerald-200/80 bg-emerald-50/80 dark:border-emerald-900/60 dark:bg-emerald-900/20">
                  <span className="text-xs text-emerald-600 font-medium block mb-2">REFLECT</span>
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-full" />
                  </div>
                </div>
              </div>
            </div>
          )}

        {currentQuestion?.type === "quantitative" && currentQuestion.scaleData && (
          <div className="space-y-2">
            <div className="flex justify-start">
              <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3">
                <span className="text-xs text-emerald-600 font-medium block mb-1">REFLECT</span>
                <p className="text-[15px]">{currentQuestion.content}</p>
              </div>
            </div>
            <div className="bg-muted/50 rounded-xl p-5 space-y-3">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{currentQuestion.scaleData.lowLabel}</span>
                <span>{currentQuestion.scaleData.highLabel}</span>
              </div>
              <div className="flex justify-between gap-2">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((value) => (
                  <button
                    key={value}
                    onClick={() => void onScaleSelect(value)}
                    className="flex-1 aspect-square rounded-lg border-2 border-border hover:border-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors flex items-center justify-center font-medium"
                  >
                    {value}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {currentQuestion &&
          currentQuestion.type !== "quantitative" &&
          currentQuestion.content.trim().length > 0 &&
          (activeChatId === null || isGeneratingQuestion) && (
            <div className="space-y-2">
              <div className="flex justify-start">
                <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3">
                  <span className="text-xs text-emerald-600 font-medium block mb-1">REFLECT</span>
                  <p className="text-[15px]">{currentQuestion.content}</p>
                </div>
              </div>
            </div>
          )}
      </div>
    </div>
  )
}
