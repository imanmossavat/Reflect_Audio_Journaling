"use client"

import { useEffect, useRef } from "react"
import { Send, Upload, RotateCw, PenLine, Search } from "lucide-react"
import { PROCESSING_STATUS_LABELS } from "@/lib/api"
import type { ChatMessageRecord, OllamaModelEntry } from "@/lib/api"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const EXAMPLE_PROMPTS = [
  "What topics show up across more than one of my entries?",
  "Ask me a question about something I described but didn't explain.",
  "Show me which entries mention deadlines.",
]

const MAX_TEXTAREA_ROWS = 10
const LINE_HEIGHT_PX = 20
const TEXTAREA_VERTICAL_PADDING_PX = 20

interface ChatInputProps {
  inputValue: string
  setInputValue: (v: string) => void
  onSubmitText: (e: React.FormEvent) => Promise<void>
  isAssistantThinking: boolean
  // reflect/ask mode (toggle shown only during a guided reflection)
  gibbsActive: boolean
  chatMode: "reflect" | "ask"
  onChangeChatMode: (mode: "reflect" | "ask") => void
  // promote-to-source controls
  activeChatId: number | null
  activeChatSourceId: number | null
  activeChatLinkedSourceStatus: string | null
  isLinkedSourceProcessing: boolean
  isPromotingChat: boolean
  activeChatMessages: ChatMessageRecord[]
  onPromoteChat: () => Promise<void>
  // toolbar
  includedSourcesCount: number
  chatModel: string | null
  installedModels: OllamaModelEntry[]
  isOllamaReachable: boolean
  isSavingChatModel: boolean
  onChangeChatModel: (model: string) => Promise<void> | void
}

export function ChatInput({
  inputValue,
  setInputValue,
  onSubmitText,
  isAssistantThinking,
  gibbsActive,
  chatMode,
  onChangeChatMode,
  activeChatId,
  activeChatSourceId,
  activeChatLinkedSourceStatus,
  isLinkedSourceProcessing,
  isPromotingChat,
  activeChatMessages,
  onPromoteChat,
  includedSourcesCount,
  chatModel,
  installedModels,
  isOllamaReachable,
  isSavingChatModel,
  onChangeChatModel,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  // Example prompts are a starting nudge — only show them on an empty chat, and
  // hide them once the first message has been sent.
  const showPrompts = inputValue.trim().length === 0 && activeChatMessages.length === 0
  const reflectMode = gibbsActive && chatMode === "reflect"
  const placeholder = reflectMode
    ? "Write your reflection…"
    : gibbsActive
      ? "Ask about your sources…"
      : "Write a message..."
  const promoteDisabled = isPromotingChat || isLinkedSourceProcessing || activeChatMessages.length === 0
  const promoteLabel = (() => {
    if (activeChatSourceId === null) return isPromotingChat ? "Promoting..." : "Promote to source"
    if (isLinkedSourceProcessing) return PROCESSING_STATUS_LABELS[activeChatLinkedSourceStatus ?? ""] ?? "Processing..."
    return isPromotingChat ? "Updating source..." : "Update source"
  })()
  const PromoteIcon = activeChatSourceId === null ? Upload : RotateCw
  const promoteIconSpin = activeChatSourceId !== null && isLinkedSourceProcessing
  const maxHeightPx = LINE_HEIGHT_PX * MAX_TEXTAREA_ROWS + TEXTAREA_VERTICAL_PADDING_PX
  const modelInList = chatModel ? installedModels.some((m) => m.name === chatModel) : false

  // The promote/update button is rendered in one of two spots depending on mode:
  // top-right above the prompts outside a reflection, or inline with the
  // reflect/ask toggle during one. Build it once so both placements stay in sync.
  const promoteButton =
    activeChatId !== null ? (
      <button
        type="button"
        onClick={() => void onPromoteChat()}
        disabled={promoteDisabled}
        className="h-7 px-2.5 inline-flex items-center gap-1.5 text-xs font-medium rounded-md border border-border bg-background hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
      >
        <PromoteIcon className={`h-3 w-3 ${promoteIconSpin ? "animate-spin" : ""}`} />
        {promoteLabel}
      </button>
    ) : null

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    const next = Math.min(el.scrollHeight, maxHeightPx)
    el.style.height = `${next}px`
  }, [inputValue, maxHeightPx])

  return (
    <div data-tour="chat" className="bg-background p-4">
      <div className="max-w-2xl mx-auto">
        {/* Top row: example prompts, plus the promote button when not reflecting.
            During a reflection the promote button moves down to the toggle row. */}
        {(showPrompts || (!gibbsActive && promoteButton)) && (
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
            {!gibbsActive && promoteButton && <div className="ml-auto shrink-0">{promoteButton}</div>}
          </div>
        )}
        {gibbsActive && (
          <div className="mb-2 flex items-center gap-2">
            <div className="inline-flex rounded-lg border bg-muted/30 p-0.5 text-xs font-medium">
              <button
                type="button"
                onClick={() => onChangeChatMode("reflect")}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-colors ${
                  chatMode === "reflect"
                    ? "bg-emerald-600 text-white"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <PenLine className="h-3.5 w-3.5" />
                Reflect
              </button>
              <button
                type="button"
                onClick={() => onChangeChatMode("ask")}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-colors ${
                  chatMode === "ask"
                    ? "bg-emerald-600 text-white"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Search className="h-3.5 w-3.5" />
                Ask sources
              </button>
            </div>
            {promoteButton && <div className="ml-auto shrink-0">{promoteButton}</div>}
          </div>
        )}
        <form
          onSubmit={onSubmitText}
          className="rounded-xl border bg-background focus-within:ring-2 focus-within:ring-emerald-500/20 focus-within:border-emerald-500 overflow-hidden"
        >
          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                void onSubmitText(e as unknown as React.FormEvent)
              }
            }}
            placeholder={placeholder}
            rows={1}
            style={{ maxHeight: `${maxHeightPx}px`, lineHeight: `${LINE_HEIGHT_PX}px` }}
            className="w-full px-3 py-2.5 bg-background resize-none focus:outline-none block overflow-y-auto"
          />
          <div className="flex items-center gap-2 px-2 pb-2 pt-1">
            <div className="ml-auto flex items-center gap-2">
              {isOllamaReachable && installedModels.length > 0 ? (
                <Select
                  value={chatModel ?? undefined}
                  onValueChange={(v) => void onChangeChatModel(v)}
                  disabled={isSavingChatModel}
                >
                  <SelectTrigger
                    size="sm"
                    className="h-7 text-[11px] border-0 bg-transparent hover:bg-muted px-2 gap-1 shadow-none w-auto min-w-0"
                  >
                    <SelectValue placeholder="model" />
                  </SelectTrigger>
                  <SelectContent align="end">
                    {installedModels.map((m) => (
                      <SelectItem key={m.name} value={m.name} className="text-xs">
                        {m.name}
                      </SelectItem>
                    ))}
                    {chatModel && !modelInList && (
                      <SelectItem value={chatModel} className="text-xs">
                        {chatModel} (not installed)
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              ) : (
                chatModel && (
                  <span className="text-[11px] text-muted-foreground font-mono">{chatModel}</span>
                )
              )}

              <span
                className="text-[11px] text-muted-foreground"
                title={`${includedSourcesCount} included source${includedSourcesCount === 1 ? "" : "s"}`}
              >
                {includedSourcesCount} source{includedSourcesCount === 1 ? "" : "s"}
              </span>

              <button
                type="submit"
                disabled={!inputValue.trim() || isAssistantThinking}
                aria-label="Send message"
                className="p-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:bg-muted disabled:text-muted-foreground text-white transition-colors"
              >
                <Send className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
