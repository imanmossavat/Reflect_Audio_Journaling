"use client"

import { useEffect, useRef } from "react"
import { Send, PenLine, Search, ChevronRight, CheckCircle2 } from "lucide-react"
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
  // Three send levers, shown during a guided reflection: "Ask my notes" (RAG),
  // "Next question" (record the answer if any, then ask a follow-up at the same
  // stage — works with or without typed text), and "Next Gibbs stage" (record the
  // answer if any, then advance).
  reflectionActive: boolean
  gibbsGenerating: boolean
  isLastStep: boolean
  nextStageLabel: string | null
  onReflect: () => void
  onAsk: () => void
  onContinue: () => void
  // toolbar
  activeChatMessages: ChatMessageRecord[]
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
  reflectionActive,
  gibbsGenerating,
  isLastStep,
  nextStageLabel,
  onReflect,
  onAsk,
  onContinue,
  activeChatMessages,
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
  const hasText = inputValue.trim().length > 0
  const placeholder = reflectionActive ? "Write your reflection…" : "Write a message..."
  const maxHeightPx = LINE_HEIGHT_PX * MAX_TEXTAREA_ROWS + TEXTAREA_VERTICAL_PADDING_PX
  const modelInList = chatModel ? installedModels.some((m) => m.name === chatModel) : false
  // The three send levers share one look so none reads as higher-ranked than the others.
  const leverClass =
    "h-8 inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-xs font-medium text-foreground hover:bg-muted hover:border-emerald-500/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"

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
        {showPrompts && (
          <div className="mb-3 flex flex-col gap-2 items-start">
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
        <form
          onSubmit={onSubmitText}
          className="rounded-xl border bg-background focus-within:ring-2 focus-within:ring-emerald-500/20 focus-within:border-emerald-500 overflow-hidden"
        >
          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              // During an active reflection, Enter must not silently pick a lever on the
              // user's behalf (it used to fire the same silent path as "Answer" — see
              // docs/REFLECTION_FLOW.md). Fall through to the textarea's native
              // behavior (insert a newline) instead; all three levers require an
              // explicit click. Outside a reflection, Enter still submits as before.
              if (e.key === "Enter" && !e.shiftKey && !reflectionActive) {
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
            <div className="flex items-center gap-2 min-w-0">
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
                  <SelectContent align="start">
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
            </div>

            <div className="ml-auto flex items-center gap-1.5 shrink-0">
              {reflectionActive ? (
                <>
                  <button
                    type="button"
                    onClick={onAsk}
                    disabled={!hasText || isAssistantThinking}
                    title="Send this as a question to your sources"
                    className={leverClass}
                  >
                    <Search className="h-3.5 w-3.5 text-emerald-600" />
                    Ask my notes
                  </button>
                  <button
                    type="button"
                    onClick={onReflect}
                    disabled={gibbsGenerating}
                    title="Save your answer (if any), then ask a follow-up on this stage"
                    className={leverClass}
                  >
                    <PenLine className="h-3.5 w-3.5 text-emerald-600" />
                    Next question
                  </button>
                  <button
                    type="button"
                    onClick={onContinue}
                    disabled={gibbsGenerating}
                    title={
                      isLastStep
                        ? "Save your answer and finish the reflection"
                        : nextStageLabel
                          ? `Save your answer and continue to ${nextStageLabel}`
                          : "Save your answer and continue"
                    }
                    className={leverClass}
                  >
                    {isLastStep ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-emerald-600" />
                    )}
                    Next Gibbs stage
                  </button>
                </>
              ) : (
                <button
                  type="submit"
                  disabled={!hasText || isAssistantThinking}
                  aria-label="Send message"
                  className="p-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:bg-muted disabled:text-muted-foreground text-white transition-colors"
                >
                  <Send className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
