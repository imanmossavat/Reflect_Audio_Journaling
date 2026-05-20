"use client"

import { Send, Upload, RotateCw } from "lucide-react"
import { PROCESSING_STATUS_LABELS } from "@/lib/api"
import type { ChatMessageRecord } from "@/lib/api"

const EXAMPLE_PROMPTS = [
  "What topics show up across more than one of my entries?",
  "Ask me a question about something I described but didn't explain.",
  "Show me which entries mention deadlines.",
]

interface ChatInputProps {
  inputValue: string
  setInputValue: (v: string) => void
  onSubmitText: (e: React.FormEvent) => Promise<void>
  isAssistantThinking: boolean
  // promote-to-source controls
  activeChatId: number | null
  activeChatSourceId: number | null
  activeChatLinkedSourceStatus: string | null
  isLinkedSourceProcessing: boolean
  isPromotingChat: boolean
  activeChatMessages: ChatMessageRecord[]
  onPromoteChat: () => Promise<void>
}

export function ChatInput({
  inputValue,
  setInputValue,
  onSubmitText,
  isAssistantThinking,
  activeChatId,
  activeChatSourceId,
  activeChatLinkedSourceStatus,
  isLinkedSourceProcessing,
  isPromotingChat,
  activeChatMessages,
  onPromoteChat,
}: ChatInputProps) {
  const showPrompts = inputValue.trim().length === 0
  const promoteDisabled = isPromotingChat || isLinkedSourceProcessing || activeChatMessages.length === 0
  const promoteLabel = (() => {
    if (activeChatSourceId === null) return isPromotingChat ? "Promoting..." : "Promote to source"
    if (isLinkedSourceProcessing) return PROCESSING_STATUS_LABELS[activeChatLinkedSourceStatus ?? ""] ?? "Processing..."
    return isPromotingChat ? "Updating source..." : "Update source"
  })()
  const PromoteIcon = activeChatSourceId === null ? Upload : RotateCw
  const promoteIconSpin = activeChatSourceId !== null && isLinkedSourceProcessing

  return (
    <div className="bg-background p-4">
      <div className="max-w-2xl mx-auto">
        {(showPrompts || activeChatId !== null) && (
          <div className="flex items-end gap-3 mb-3">
            {showPrompts && (
              <div className="flex flex-col gap-2 items-start flex-1 min-w-0">
                {EXAMPLE_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => setInputValue(prompt)}
                    className="text-xs px-3 py-2 rounded-lg border border-border bg-muted/30 hover:border-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors text-left text-muted-foreground hover:text-foreground max-w-full"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            )}
            {activeChatId !== null && (
              <button
                type="button"
                onClick={() => void onPromoteChat()}
                disabled={promoteDisabled}
                className="h-7 px-2.5 inline-flex items-center gap-1.5 text-xs font-medium rounded-md border border-border bg-background hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors ml-auto shrink-0"
              >
                <PromoteIcon className={`h-3 w-3 ${promoteIconSpin ? "animate-spin" : ""}`} />
                {promoteLabel}
              </button>
            )}
          </div>
        )}
        <form onSubmit={onSubmitText} className="relative">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                void onSubmitText(e as unknown as React.FormEvent)
              }
            }}
            placeholder="Write a message..."
            rows={1}
            className="w-full py-2.5 pl-3 pr-11 rounded-xl border bg-background resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 leading-5 block"
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isAssistantThinking}
            aria-label="Send message"
            className="absolute top-1/2 -translate-y-1/2 right-1.5 p-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:bg-muted disabled:text-muted-foreground text-white transition-colors"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </form>
      </div>
    </div>
  )
}
