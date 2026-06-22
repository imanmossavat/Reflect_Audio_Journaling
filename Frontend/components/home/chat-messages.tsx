"use client"

import { Fragment } from "react"
import { ChevronRight, Loader2, Check, Search } from "lucide-react"
import type { ChatMessageRecord, ChatStreamStageName, QuerySource, SafetyKind, AppLanguage } from "@/lib/api"
import type { StreamingAssistant, StreamingStage } from "@/hooks/useChatManagement"
import { formatListTimestamp } from "@/lib/utils"
import { Markdown } from "@/components/markdown"
import { getGibbsStep } from "@/lib/gibbs"
import { CrisisSupportCard } from "@/components/home/crisis-support-card"

/** Divider marking where a thread section begins: a Gibbs stage, or a RAG "context" block. */
function GroupHeader({ step }: { step: number | null }) {
  const label =
    step != null ? `${String(step).padStart(2, "0")} · ${getGibbsStep(step).label}` : "Context"
  return (
    <div className="flex items-center gap-3 pt-2">
      <span className="h-px flex-1 bg-border" />
      <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-emerald-600">
        {step == null && <Search className="h-3 w-3" />}
        {label}
      </span>
      <span className="h-px flex-1 bg-border" />
    </div>
  )
}

/** Source chips under a RAG answer, deduped by source, labelled with the source name. */
function SourceChips({
  sources,
  sourceNameById,
}: {
  sources: QuerySource[]
  sourceNameById: Record<string, string>
}) {
  const seen = new Set<string>()
  const chips: { key: string; label: string }[] = []
  for (const s of sources) {
    const id = s.source_id != null ? String(s.source_id) : null
    const key = id ?? s.node_id ?? s.chunk_id ?? ""
    if (!key || seen.has(key)) continue
    seen.add(key)
    const label = (id && sourceNameById[id]) || (id ? `Source ${id}` : "Source")
    chips.push({ key, label })
  }
  if (chips.length === 0) return null
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {chips.map((c) => (
        <span
          key={c.key}
          className="inline-flex max-w-[200px] items-center gap-1 rounded-full border bg-background px-2 py-0.5 text-[10px] text-muted-foreground"
        >
          <Search className="h-2.5 w-2.5 text-emerald-600 shrink-0" />
          <span className="truncate">{c.label}</span>
        </span>
      ))}
    </div>
  )
}

interface ChatMessagesProps {
  activeChatMessages: ChatMessageRecord[]
  isLoadingActiveChat: boolean
  streamingAssistant: StreamingAssistant | null
  sourceNameById: Record<string, string>
  supportCard: { kind: SafetyKind } | null
  onDismissSupportCard: () => void
  language?: AppLanguage
}

const STAGE_LABELS: Record<ChatStreamStageName, (count?: number) => string> = {
  checking: () => "Preparing",
  queued: () => "Waiting for the model",
  searching: () => "Searching your sources",
  retrieved: (count) => `Read ${count ?? 0} relevant chunk${count === 1 ? "" : "s"}`,
  thinking: () => "Thinking",
  writing: () => "Writing answer",
}

/** The pulsing "skeleton reveal": grows with the answer's character count while the real
 *  text is withheld server-side, then is replaced by the persisted message once the output
 *  guard passes. Conveys length/progress without ever showing unguarded content. */
function AnswerSkeleton({ chars }: { chars: number }) {
  const CHARS_PER_LINE = 56
  const lines = Math.max(1, Math.ceil(chars / CHARS_PER_LINE))
  const lastLineChars = chars - (lines - 1) * CHARS_PER_LINE
  const lastWidth = Math.max(20, Math.min(100, Math.round((lastLineChars / CHARS_PER_LINE) * 100)))
  return (
    <div className="space-y-2 py-0.5" aria-label="Writing answer">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-3.5 rounded bg-muted-foreground/15 animate-pulse"
          style={{ width: i === lines - 1 ? `${lastWidth}%` : "100%" }}
        />
      ))}
    </div>
  )
}

function StageRow({ stage, thinking }: { stage: StreamingStage; thinking?: string }) {
  const label = STAGE_LABELS[stage.name](stage.count)
  const icon = stage.done ? (
    <Check className="h-3.5 w-3.5 text-emerald-600" />
  ) : (
    <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
  )

  if (stage.name === "thinking" && thinking) {
    return (
      <details className="group" open={!stage.done}>
        <summary className="flex items-center gap-2 cursor-pointer list-none text-xs text-muted-foreground hover:text-foreground">
          {icon}
          <ChevronRight className="h-3 w-3 transition-transform group-open:rotate-90" />
          <span>{label}</span>
        </summary>
        <div className="mt-1.5 ml-7 text-xs text-muted-foreground whitespace-pre-wrap border-l-2 border-muted-foreground/20 pl-2">
          {thinking}
        </div>
      </details>
    )
  }

  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      {icon}
      <span>{label}</span>
    </div>
  )
}

export function ChatMessages({ activeChatMessages, isLoadingActiveChat, streamingAssistant, sourceNameById, supportCard, onDismissSupportCard, language }: ChatMessagesProps) {
  return (
    <div className="flex-1 min-h-0 overflow-y-auto no-scrollbar p-6">
      <div className="max-w-2xl mx-auto space-y-4">
        {isLoadingActiveChat ? (
          <p className="text-sm text-muted-foreground text-center">Loading chat...</p>
        ) : (
          (() => {
          // "Context" divider onlyIn a plain (non-reflection) chat
          const hasReflection = activeChatMessages.some((m) => m.gibbs_step != null)
          return activeChatMessages.map((message, i) => {
            const timestamp = formatListTimestamp(message.created_at)
            // Divide the thread into sections: each Gibbs stage, and RAG "context" blocks
            // (gibbs_step == null). Show the header wherever the section changes.
            const curStep = message.gibbs_step ?? null
            const prevStep = i > 0 ? activeChatMessages[i - 1].gibbs_step ?? null : undefined
            const stepHeader =
              curStep !== prevStep && (curStep != null || hasReflection) ? (
                <GroupHeader step={curStep} />
              ) : null
            if (message.role === "question") {
              const hasThinking = !!(message.thinking && message.thinking.trim())
              return (
                <Fragment key={message.id}>
                {stepHeader}
                <div className="flex justify-start">
                  <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3 max-w-[85%]">
                    {hasThinking && (
                      <details className="group mb-2">
                        <summary className="flex items-center gap-1 cursor-pointer list-none text-xs text-muted-foreground hover:text-foreground">
                          <ChevronRight className="h-3 w-3 transition-transform group-open:rotate-90" />
                          <span>Thoughts</span>
                        </summary>
                        <div className="mt-1.5 text-xs text-muted-foreground whitespace-pre-wrap border-l-2 border-muted-foreground/20 pl-2">
                          {message.thinking}
                        </div>
                      </details>
                    )}
                    <Markdown className="text-[15px]">{message.text}</Markdown>
                    {message.sources && message.sources.length > 0 && (
                      <SourceChips sources={message.sources} sourceNameById={sourceNameById} />
                    )}
                    <div className="flex items-center justify-between gap-2 mt-1.5">
                      <span className="text-[10px] text-muted-foreground">{timestamp}</span>
                      {message.model && (
                        <span className="text-[10px] text-muted-foreground/70 font-mono">
                          generated by: {message.model}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                </Fragment>
              )
            }
            const answerText =
              message.scale_value !== null && message.scale_value !== undefined
                ? `${message.scale_value}/${message.scale_max ?? 10}`
                : message.text
            return (
              <Fragment key={message.id}>
              {stepHeader}
              <div className="flex justify-end">
                <div className="bg-emerald-900 text-white rounded-2xl rounded-tr-sm px-4 py-3 max-w-[85%]">
                  <p className="text-[15px] whitespace-pre-wrap">{answerText}</p>
                  <div className="flex items-center justify-end gap-2 mt-1.5">
                    <span className="text-[10px] text-white/70">{timestamp}</span>
                  </div>
                </div>
              </div>
              </Fragment>
            )
          })
          })()
        )}

        {streamingAssistant && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3 max-w-[85%] min-w-[200px]">
              {streamingAssistant.stages.length > 0 && (
                <details className="group mb-2" open>
                  <summary className="flex items-center gap-1 cursor-pointer list-none text-xs text-muted-foreground hover:text-foreground">
                    <ChevronRight className="h-3 w-3 transition-transform group-open:rotate-90" />
                    <span>Process</span>
                  </summary>
                  <div className="mt-1.5 space-y-1.5 pl-1">
                    {streamingAssistant.stages.map((stage, i) => (
                      <StageRow
                        key={`${stage.name}-${i}`}
                        stage={stage}
                        thinking={stage.name === "thinking" ? streamingAssistant.thinking : undefined}
                      />
                    ))}
                  </div>
                </details>
              )}
              {streamingAssistant.progressChars > 0 ? (
                <AnswerSkeleton chars={streamingAssistant.progressChars} />
              ) : streamingAssistant.stages.length === 0 ? (
                <div className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:-0.3s]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:-0.15s]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce" />
                </div>
              ) : null}
            </div>
          </div>
        )}

        {supportCard && (
          <CrisisSupportCard kind={supportCard.kind} language={language} onDismiss={onDismissSupportCard} />
        )}
      </div>
    </div>
  )
}
