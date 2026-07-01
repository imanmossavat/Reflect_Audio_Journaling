"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { api, type ChatSummary, type ChatMessageRecord, type GuardUnavailableInfo, type SafetyKind, type TopicGroup, PROCESSING_STATUSES } from "@/lib/api"
import type { RawSource } from "@/components/home/types"
import { mapBackendSource } from "@/hooks/useSourceManagement"
import { useGeneration } from "@/context/generation-provider"
import type { StreamingAssistant, StreamingStage } from "@/context/generation-provider"
import { GIBBS_STEP_COUNT } from "@/lib/gibbs"
import { toast } from "sonner"

// Streaming types now live with the provider that owns the streaming state. Re-export
// them here so existing consumers (e.g. chat-messages) keep their import path.
export type { StreamingStage, StreamingAssistant }

interface UseChatManagementOptions {
  rawSources: RawSource[]
  setRawSources: React.Dispatch<React.SetStateAction<RawSource[]>>
  setProcessingSources: React.Dispatch<React.SetStateAction<Set<number>>>
}

const ACTIVE_CHAT_STORAGE_KEY = "reflect.activeChatId"

function readStoredActiveChatId(): number | null {
  if (typeof window === "undefined") return null
  const raw = window.localStorage.getItem(ACTIVE_CHAT_STORAGE_KEY)
  if (raw === null) return null
  const parsed = Number(raw)
  return Number.isFinite(parsed) ? parsed : null
}
function mergeChatLists(prev: ChatSummary[], list: ChatSummary[]): ChatSummary[] {
  if (prev.length === 0) return list
  const prevById = new Map(prev.map((c) => [c.id, c]))
  const serverIds = new Set(list.map((c) => c.id))
  const merged = list.map((c) => ({ ...prevById.get(c.id), ...c }))
  const localOnly = prev.filter((c) => !serverIds.has(c.id))
  const next = [...localOnly, ...merged]
  return JSON.stringify(next) === JSON.stringify(prev) ? prev : next
}

export function useChatManagement({ rawSources, setRawSources, setProcessingSources }: UseChatManagementOptions) {
  const [chats, setChats] = useState<ChatSummary[]>([])
  const [activeChatId, setActiveChatId] = useState<number | null>(null)
  const [activeChatMessages, setActiveChatMessages] = useState<ChatMessageRecord[]>([])
  const [isLoadingChats, setIsLoadingChats] = useState(true)
  const [isLoadingActiveChat, setIsLoadingActiveChat] = useState(false)
  const [renamingChatId, setRenamingChatId] = useState<number | null>(null)
  const [renameDraft, setRenameDraft] = useState("")
  const [isPromotingChat, setIsPromotingChat] = useState(false)
  const [inputValue, setInputValue] = useState("")
  // Query answers stream through the GenerationProvider so they survive navigation and
  // refresh. The local streamingAssistant below is only for guided Gibbs questions,
  // which are session-local by design and don't need to outlive the page.
  const generation = useGeneration()
  const [streamingAssistant, setStreamingAssistant] = useState<StreamingAssistant | null>(null)
  // Which chat the local (Gibbs) stream belongs to, so it only shows in its own chat.
  const [streamingChatId, setStreamingChatId] = useState<number | null>(null)
  // A live mirror of activeChatId so async stream callbacks (onDone) can check the
  // *current* chat instead of the stale value captured when the stream started.
  const activeChatIdRef = useRef<number | null>(null)
  // Only surface a stream in the chat that owns it (no bleed across chats). The query
  // answer (provider) takes precedence; otherwise fall back to a local Gibbs stream.
  const queryStreaming = generation.generationFor(activeChatId)
  const gibbsStreaming = streamingChatId === activeChatId ? streamingAssistant : null
  const visibleStreamingAssistant = queryStreaming ?? gibbsStreaming
  // Block re-submitting only while *this* chat is busy (other chats can queue).
  const isAssistantThinking = visibleStreamingAssistant !== null
  // Guided Gibbs reflection mode. Step state is local to this session (not yet
  // persisted on the Chat), so it resets when the chat changes or on reload.
  const [gibbsActive, setGibbsActive] = useState(false)
  const [gibbsStep, setGibbsStep] = useState(1)
  const [gibbsGenerating, setGibbsGenerating] = useState(false)
  // The setup phase: after starting a reflection the user picks sources and writes a
  // goal before any questions are asked. While true, the right panel shows the setup
  // screen and no facilitator call has been made yet.
  const [gibbsSetup, setGibbsSetup] = useState(false)
  // The user's stated focus/topic for this reflection. Persisted on the Chat (so it
  // survives reload/resume) and sent to the facilitator on every step.
  const [gibbsGoal, setGibbsGoal] = useState("")
  // Supporting excerpts for the chosen topic (when grouping was used). Keep the
  // facilitator scoped and are persisted alongside the goal as the reflection scope.
  const [gibbsScopeItems, setGibbsScopeItems] = useState<string[]>([])
  // Once the final stage is finished the cycle enters a "complete" wrap-up phase
  // (still active, so the right panel shows the summary instead of step controls).
  const [gibbsComplete, setGibbsComplete] = useState(false)
  // A distress signal surfaced for the chat on screen. Ephemeral (never persisted), shown
  // as a dismissible support card; cleared whenever the active chat changes.
  const [supportCard, setSupportCard] = useState<{ kind: SafetyKind } | null>(null)
  const dismissSupportCard = () => setSupportCard(null)
  // The mandatory guard model isn't installed, so the chat couldn't answer. Shown as a
  // dismissible in-thread setup card (like the support card); cleared on chat change.
  const [guardNotice, setGuardNotice] = useState<GuardUnavailableInfo | null>(null)
  const dismissGuardNotice = () => setGuardNotice(null)
  // Don't persist activeChatId until we've restored it from storage on mount,
  // otherwise the initial null would wipe the stored value before we read it.
  const hasRestoredActiveChat = useRef(false)

  useEffect(() => {
    let cancelled = false

    // Fetch the chat list in interval when no response yet 
    const syncChats = async (): Promise<boolean> => {
      let list: ChatSummary[]
      try {
        list = await api.listChats()
      } catch {
        return false // backend not up yet / transient — the interval retries
      }
      if (cancelled) return true
      setChats((prev) => mergeChatLists(prev, list))
      if (!hasRestoredActiveChat.current) {
        // Restore after mount (not during render, to avoid an SSR/client hydration
        // mismatch). Only restore it if it still exists.
        setActiveChatId((prev) => {
          const candidate = prev ?? readStoredActiveChatId()
          return candidate !== null && list.some((c) => c.id === candidate) ? candidate : prev
        })
        hasRestoredActiveChat.current = true
      }
      return true
    }

    void syncChats().finally(() => { if (!cancelled) setIsLoadingChats(false) })
    const interval = setInterval(() => { void syncChats() }, 5000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [])

  useEffect(() => {
    if (typeof window === "undefined" || !hasRestoredActiveChat.current) return
    if (activeChatId === null) window.localStorage.removeItem(ACTIVE_CHAT_STORAGE_KEY)
    else window.localStorage.setItem(ACTIVE_CHAT_STORAGE_KEY, String(activeChatId))
  }, [activeChatId])

  useEffect(() => {
    activeChatIdRef.current = activeChatId
  }, [activeChatId])

  useEffect(() => {
    setSupportCard(null) // ephemeral: a support card belongs to the chat that triggered it
    setGuardNotice(null) // ditto for the guard-setup card
    if (activeChatId === null) { setActiveChatMessages([]); return }
    const loadChat = async () => {
      setIsLoadingActiveChat(true)
      try {
        const detail = await api.getChat(activeChatId)
        setActiveChatMessages(detail.messages)
        // Reflection state isn't stored on the Chat, but reflection messages are
        // tagged with their Gibbs stage. If this chat has any, treat it as a
        // reflection again and resume at the furthest stage reached, so leaving
        // and returning to (or reloading) the chat doesn't lose that it's guided.
        const steps = detail.messages
          .map((m) => m.gibbs_step)
          .filter((s): s is number => typeof s === "number" && s >= 1)
        if (steps.length > 0) {
          setGibbsActive(true)
          setGibbsComplete(false)
          // Resuming an in-progress reflection goes straight to the active phase —
          // setup only happens once, when the cycle is first started.
          setGibbsSetup(false)
          setGibbsGoal(detail.reflection_goal ?? detail.reflection_scope?.topic ?? "")
          setGibbsScopeItems(detail.reflection_scope?.items ?? [])
          setGibbsStep(Math.min(Math.max(...steps), GIBBS_STEP_COUNT))
        }
      } catch (error) {
        toast.error(`Could not load chat: ${error instanceof Error ? error.message : "Unknown error"}`)
      } finally {
        setIsLoadingActiveChat(false)
      }
    }
    void loadChat()
  }, [activeChatId])

  const activeChat = useMemo(
    () => (activeChatId === null ? null : chats.find((c) => c.id === activeChatId) ?? null),
    [activeChatId, chats]
  )
  const activeChatSourceId = activeChat?.source_id ?? null
  const activeChatLinkedSourceStatus = useMemo(() => {
    if (activeChatSourceId === null) return null
    return rawSources.find((s) => Number(s.id) === activeChatSourceId)?.status ?? null
  }, [activeChatSourceId, rawSources])
  const isLinkedSourceProcessing = activeChatLinkedSourceStatus
    ? PROCESSING_STATUSES.has(activeChatLinkedSourceStatus)
    : false

  const refreshChats = async () => {
    try { setChats(await api.listChats()) } catch (error) { console.warn("Failed to refresh chats", error) }
  }

  const ensureActiveChat = async (): Promise<number> => {
    if (activeChatId !== null) return activeChatId
    const created = await api.createChat()
    setActiveChatId(created.id)
    setChats((prev) => [created, ...prev])
    return created.id
  }

  const persistMessage = async (chatId: number, payload: Parameters<typeof api.appendChatMessage>[1]) => {
    try {
      const created = await api.appendChatMessage(chatId, payload)
      // Only touch the visible list if this is still the chat on screen; otherwise
      // it's a background write and would otherwise leak into the chat you switched to.
      if (activeChatIdRef.current === chatId) setActiveChatMessages((prev) => [...prev, created])
      void refreshChats()
      return created
    } catch (error) {
      toast.error(`Could not save message: ${error instanceof Error ? error.message : "Unknown error"}`)
      return null
    }
  }

  // Send the box as one turn. "reflect" tags it with the current Gibbs stage and keeps
  // the facilitator silent (one answer per question); "ask" runs it as a RAG context
  // question grounded in the sources. Returns the persisted answer so callers that also
  // advance the stage (Continue) can hand the facilitator fresh history.
  const submitText = async (intent: "reflect" | "ask"): Promise<ChatMessageRecord | null> => {
    const trimmed = inputValue.trim()
    if (!trimmed || isAssistantThinking) return null
    setInputValue("")
    let chatId: number
    let created: ChatMessageRecord | null = null
    try {
      chatId = await ensureActiveChat()
      // A reflection answer only when actively reflecting; otherwise it's a RAG question.
      const asReflection = gibbsActive && intent === "reflect"
      created = await persistMessage(chatId, {
        role: "answer",
        text: trimmed,
        // Tag reflection answers with their stage so the chat can group them.
        ...(asReflection ? { gibbs_step: gibbsStep } : {}),
      })
      if (asReflection) {
        // Screen the reflection answer for distress — non-blocking, so it never delays the
        // save or interrupts journaling. On a hit, surface an empathetic support card.
        void api.checkSafety(trimmed)
          .then((v) => {
            if (v.flagged && v.kind && activeChatIdRef.current === chatId) setSupportCard({ kind: v.kind })
          })
          .catch(() => {})
        // The facilitator stays silent (no question is asked or shown), but the answer
        // still needs to reach Gist/Open Thread so the next question stays grounded in
        // it. Fire mode "reflect" in the background — it updates server-side state and
        // returns no text, so failures are logged, not surfaced to the user.
        void api.streamGeneratedQuestion(
          {
            mode: "reflect",
            chat_id: chatId,
            step: gibbsStep,
            journal_text: buildJournalText() || undefined,
            history: buildGibbsHistory(created ? [created] : undefined),
            goal: gibbsGoal.trim() || undefined,
          },
          {
            onProgress: () => {},
            onDone: () => {},
            onError: (error) => console.warn("[reflect-only update] failed:", error),
          }
        )
        // The facilitator stays silent after a reflection answer — one answer per
        // question. The user advances the stage or asks another question.
        return created
      }
    } catch (error) {
      toast.error(`Could not save message: ${error instanceof Error ? error.message : "Unknown error"}`)
      return null
    }
    // Hand off to the provider: it runs the answer server-side (so it survives leaving
    // the page) and streams it back. Completion is handled by the onComplete effect.
    generation.startTextGeneration(chatId, trimmed)
    return created
  }

  // Form submit / Enter: reflect while a cycle is running, otherwise ask the sources.
  const handleSubmitText = async (e: React.FormEvent) => {
    e.preventDefault()
    await submitText(gibbsActive && !gibbsComplete ? "reflect" : "ask")
  }

  // When a query generation finishes, fold its answer into the on-screen chat (if it's
  // the one in view) and drop the streaming entry. Runs for generations started here or
  // resumed after a refresh. The provider also auto-clears as a safety net.
  useEffect(() => {
    return generation.onComplete((chatId, outcome, info) => {
      if (outcome === "fallback") {
        // The guard intercepted the question or blocked the answer — show support, no message.
        if (info && "kind" in info && activeChatIdRef.current === chatId) setSupportCard({ kind: info.kind })
        generation.clearGeneration(chatId)
      } else if (outcome === "guard_unavailable") {
        // The mandatory guard model isn't installed — show the setup card, no message.
        if (info && "command" in info && activeChatIdRef.current === chatId) setGuardNotice(info)
        generation.clearGeneration(chatId)
      } else if (outcome === "done" && info && "message_id" in info && activeChatIdRef.current === chatId) {
        const messageId = info.message_id
        void (async () => {
          try {
            const detail = await api.getChat(chatId)
            const created = detail.messages.find((m) => m.id === messageId)
            setActiveChatMessages((prev) => (created ? [...prev, created] : detail.messages))
          } catch (error) {
            console.warn("Failed to refetch chat after stream", error)
          } finally {
            generation.clearGeneration(chatId)
          }
        })()
      } else {
        generation.clearGeneration(chatId)
      }
      void refreshChats()
    })
    // onComplete/clearGeneration are stable; refreshChats is closure-stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generation.onComplete, generation.clearGeneration])

  // --- Guided Gibbs reflection -------------------------------------------------

  // Build the conversation so far as Q&A pairs to give the facilitator context for
  // its next question.
  // `extra` lets a caller include just-persisted messages that React state hasn't
  // committed yet (e.g. the answer submitted by Continue before advancing the stage).
  const buildGibbsHistory = (extra?: ChatMessageRecord[]): Array<Record<string, unknown>> => {
    const msgs: Array<Pick<ChatMessageRecord, "role" | "text">> = extra
      ? [...activeChatMessages, ...extra]
      : activeChatMessages
    const pairs: Array<{ question?: string; answer?: string }> = []
    let pending: { question?: string; answer?: string } | null = null
    for (const m of msgs) {
      if (m.role === "question") {
        if (pending) pairs.push(pending)
        pending = { question: m.text }
      } else {
        if (!pending) pending = {}
        pending.answer = m.text
        pairs.push(pending)
        pending = null
      }
    }
    if (pending) pairs.push(pending)
    // Keep the recent conversation (last 8 turns) so the facilitator has context
    // without sending the whole thread.
    return pairs.slice(-8)
  }

  // Ground the facilitator in the user's included sources (mirrors AI Search). Shared
  // by the streamed facilitator calls and the silent "Answer" (reflect-only) call.
  const buildJournalText = (): string =>
    rawSources
      .filter((s) => s.included)
      .map((s) => s.content)
      .filter(Boolean)
      .join("\n")
      .slice(0, 2000)

  // Shared streaming runner for the conversational Gibbs facilitator. The facilitator's
  // reply is persisted as a "question" (assistant) message so it renders on the AI side.
  const streamFacilitator = async (
    chatId: number,
    mode: "deep_dive" | "clarifying" | "reply",
    step: number,
    history: Array<Record<string, unknown>>
  ) => {
    const journalText = buildJournalText()

    setGibbsGenerating(true)
    setStreamingChatId(chatId)
    setStreamingAssistant({ stages: [], thinking: "", answer: "", progressChars: 0 })
    await new Promise<void>((resolve) => {
      api.streamGeneratedQuestion(
        {
          mode,
          chat_id: chatId,
          step,
          journal_text: journalText || undefined,
          history,
          goal: gibbsGoal.trim() || undefined,
          scope_items: gibbsScopeItems.length ? gibbsScopeItems : undefined,
        },
        {
          onProgress: (chars) => {
            setStreamingAssistant((prev) => (prev ? { ...prev, progressChars: chars } : prev))
          },
          onDone: async ({ text, model, fallbackKind }) => {
            try {
              if (fallbackKind) {
                // The facilitator's question was blocked by the output guard — offer support
                // instead of revealing/persisting it.
                if (activeChatIdRef.current === chatId) setSupportCard({ kind: fallbackKind })
              } else if (text) {
                // persistMessage guards the on-screen append by chat id; the message
                // is always saved server-side even if the user switched chats. Tag the
                // facilitator's question with the stage it belongs to, and record the
                // model that generated it (shown as "generated by:" like a plain chat).
                await persistMessage(chatId, { role: "question", text, model, gibbs_step: step })
              }
            } finally {
              setStreamingAssistant(null)
              setStreamingChatId(null)
              setGibbsGenerating(false)
              resolve()
            }
          },
          onError: (error) => {
            toast.error(error.message.replace(/^API\s+\d+:\s*/, ""))
            setStreamingAssistant(null)
            setStreamingChatId(null)
            setGibbsGenerating(false)
            resolve()
          },
        }
      )
    })
  }

  const generateGibbsQuestion = async (
    targetStep: number,
    mode: "deep_dive" | "clarifying" = "deep_dive",
    extraHistory?: ChatMessageRecord[],
  ) => {
    let chatId: number
    try {
      chatId = await ensureActiveChat()
    } catch (error) {
      toast.error(`Could not start reflection: ${error instanceof Error ? error.message : "Unknown error"}`)
      return
    }
    await streamFacilitator(chatId, mode, targetStep, buildGibbsHistory(extraHistory))
  }

  // Starting a reflection no longer fires a question. It opens the setup phase, where
  // the user picks sources and writes a goal. Sources start deselected so the user
  // deliberately opts each one in. The first question is generated by beginReflection().
  const startReflection = async () => {
    if (gibbsGenerating) return
    // Reset synchronously, before the `await` below. The caller (ReflectionBanner's
    // onStart) opens the sources sidebar in the same click, before this function's
    // promise settles — if the deselect-all ran only after `ensureActiveChat()`
    // resolves, a source the user ticks while that network call is still pending
    // gets silently reverted the moment it lands (visible as a tick-then-untick
    // flicker; see docs/ISSUES.md #18). Doing it first closes that window entirely.
    setRawSources((prev) => prev.map((s) => (s.included ? { ...s, included: false } : s)))
    try {
      await ensureActiveChat()
    } catch (error) {
      toast.error(`Could not start reflection: ${error instanceof Error ? error.message : "Unknown error"}`)
      return
    }
    setGibbsActive(true)
    setGibbsComplete(false)
    setGibbsSetup(true)
    setGibbsStep(1)
    setGibbsGoal("")
    setGibbsScopeItems([])
  }

  // Group the included sources into topics so the user can pick a theme without naming
  // it themselves. Returns [] (and toasts) on failure so the UI can fall back to free text.
  const groupReflectionTopics = async (): Promise<TopicGroup[]> => {
    const journalText = rawSources
      .filter((s) => s.included)
      .map((s) => s.content)
      .filter(Boolean)
      .join("\n")
      .slice(0, 6000)
    if (!journalText.trim()) return []
    try {
      const { topics } = await api.groupTopics(journalText)
      return topics
    } catch (error) {
      toast.error(`Could not group topics: ${error instanceof Error ? error.message.replace(/^API\s+\d+:\s*/, "") : "Unknown error"}`)
      return []
    }
  }

  // Leave the setup phase and ask the first question, persisting the goal/scope on the
  // chat so they survive reload/resume. By the time the user reaches the Ready stage,
  // the goal/scope state has settled, so we read it directly.
  const beginReflection = async () => {
    if (gibbsGenerating) return
    const goal = gibbsGoal.trim()
    if (activeChatId !== null) {
      const chatId = activeChatId
      const sourceIds = rawSources.filter((s) => s.included).map((s) => Number(s.id)).filter(Number.isFinite)
      // Persist the scope when a topic with excerpts was chosen; otherwise just the goal.
      const save = gibbsScopeItems.length
        ? api.setReflectionScope(chatId, { topic: goal, items: gibbsScopeItems, source_ids: sourceIds })
        : goal
          ? api.setReflectionGoal(chatId, goal)
          : null
      if (save) {
        void save
          .then((updated) =>
            setChats((prev) => prev.map((c) => (c.id === chatId ? { ...c, reflection_goal: updated.reflection_goal, reflection_scope: updated.reflection_scope } : c)))
          )
          .catch((error) =>
            toast.error(`Could not save reflection setup: ${error instanceof Error ? error.message : "Unknown error"}`)
          )
      }
    }
    setGibbsSetup(false)
    await generateGibbsQuestion(1, "deep_dive")
  }

  const advanceGibbsStep = async (extraAnswer?: ChatMessageRecord) => {
    if (gibbsGenerating) return
    if (gibbsStep >= GIBBS_STEP_COUNT) {
      // Final stage finished — enter the wrap-up phase (panel stays open).
      setGibbsComplete(true)
      return
    }
    const next = gibbsStep + 1
    setGibbsStep(next)
    await generateGibbsQuestion(next, "deep_dive", extraAnswer ? [extraAnswer] : undefined)
  }

  // The "Continue" lever: record whatever is in the box as this stage's reflection, then
  // move to the next stage (or finish). An empty box just advances.
  const continueStage = async () => {
    if (gibbsGenerating) return
    if (inputValue.trim()) {
      const created = await submitText("reflect")
      if (!created) return
      await advanceGibbsStep(created)
    } else {
      await advanceGibbsStep()
    }
  }

  // After the wrap-up, start a brand-new cycle in a fresh chat.
  const beginNewCycle = async () => {
    if (gibbsGenerating) return
    resetChatState()
    await startReflection()
  }

  const askClarifying = async () => {
    if (gibbsGenerating) return
    await generateGibbsQuestion(gibbsStep, "clarifying")
  }

  const handleSelectGibbsStep = async (target: number) => {
    if (gibbsGenerating || target === gibbsStep) return
    setGibbsStep(target)
    await generateGibbsQuestion(target, "deep_dive")
  }

  const exitReflection = () => {
    setGibbsActive(false)
    setGibbsComplete(false)
    setGibbsSetup(false)
    setGibbsGoal("")
    setGibbsScopeItems([])
  }

  const handleSelectChat = (chatId: number) => {
    setActiveChatId(chatId)
    setInputValue("")
    setGibbsActive(false)
    setGibbsComplete(false)
    setGibbsSetup(false)
    setGibbsGoal("")
    setGibbsScopeItems([])
  }

  const handleStartRenameChat = (chat: ChatSummary, event: React.MouseEvent) => {
    event.stopPropagation()
    setRenamingChatId(chat.id)
    setRenameDraft(chat.title)
  }

  const handleStartRenameActiveChat = () => {
    if (!activeChat) return
    setRenamingChatId(activeChat.id)
    setRenameDraft(activeChat.title)
  }

  const handleCommitRename = async (chatId: number) => {
    const next = renameDraft.trim()
    setRenamingChatId(null)
    if (!next) return
    const existing = chats.find((c) => c.id === chatId)
    if (!existing || existing.title === next) return
    try {
      const updated = await api.renameChat(chatId, next)
      setChats((prev) => prev.map((c) => (c.id === chatId ? { ...c, title: updated.title } : c)))
    } catch (error) {
      toast.error(`Rename failed: ${error instanceof Error ? error.message : "Unknown error"}`)
    }
  }

  const handleDeleteChat = async (chat: ChatSummary, event?: React.MouseEvent) => {
    event?.stopPropagation()
    const warning = chat.source_id
      ? `Delete "${chat.title}"? The promoted source will remain in your sources.`
      : `Delete "${chat.title}"? This cannot be undone.`
    if (!window.confirm(warning)) return
    try {
      await api.deleteChat(chat.id)
      setChats((prev) => prev.filter((c) => c.id !== chat.id))
      if (activeChatId === chat.id) { setActiveChatId(null); setActiveChatMessages([]) }
    } catch (error) {
      toast.error(`Delete failed: ${error instanceof Error ? error.message : "Unknown error"}`)
    }
  }

  // Promote/update a specific chat (defaults to the active one). Whether it creates a
  // new source or re-indexes an existing one is decided by that chat's source_id.
  const handlePromoteChat = async (chatId?: number) => {
    const id = chatId ?? activeChatId
    if (id === null || isPromotingChat) return
    const sourceId = chats.find((c) => c.id === id)?.source_id ?? null
    setIsPromotingChat(true)
    try {
      if (sourceId === null) {
        const result = await api.promoteChat(id)
        setChats((prev) => prev.map((c) => (c.id === id ? { ...c, source_id: result.source.id } : c)))
        setRawSources((prev) => [mapBackendSource(result.source), ...prev])
        setProcessingSources((prev) => new Set([...prev, result.source.id]))
        toast("Chat promoted — indexing in background.")
      } else {
        const updated = await api.reindexChat(id)
        setRawSources((prev) => prev.map((s) => (Number(s.id) === updated.id ? { ...s, status: updated.status } : s)))
        setProcessingSources((prev) => new Set([...prev, updated.id]))
        toast("Updating chat content...")
      }
    } catch (error) {
      toast.error(`Operation failed: ${error instanceof Error ? error.message : "Unknown error"}`)
    } finally {
      setIsPromotingChat(false)
    }
  }

  const resetChatState = () => {
    setActiveChatId(null)
    setActiveChatMessages([])
    setInputValue("")
    setGibbsActive(false)
    setGibbsComplete(false)
    setGibbsSetup(false)
    setGibbsGoal("")
    setGibbsScopeItems([])
  }

  return {
    chats, activeChatId, activeChatMessages, isLoadingChats, isLoadingActiveChat,
    renamingChatId, renameDraft, setRenameDraft, setRenamingChatId,
    isPromotingChat, inputValue, setInputValue, isAssistantThinking,
    streamingAssistant: visibleStreamingAssistant,
    generatingChatIds: generation.generatingChatIds,
    activeChat, activeChatSourceId, activeChatLinkedSourceStatus, isLinkedSourceProcessing,
    handleSelectChat, handleStartRenameChat, handleStartRenameActiveChat, handleCommitRename, handleDeleteChat,
    handlePromoteChat, handleSubmitText,
    submitReflection: () => void submitText("reflect"),
    submitQuestion: () => void submitText("ask"),
    continueStage,
    resetChatState,
    supportCard, dismissSupportCard,
    guardNotice, dismissGuardNotice,
    gibbsActive, gibbsStep, gibbsGenerating, gibbsComplete, gibbsSetup, gibbsGoal, setGibbsGoal,
    gibbsScopeItems, setGibbsScopeItems, groupReflectionTopics,
    startReflection, beginReflection, advanceGibbsStep, askClarifying, exitReflection, handleSelectGibbsStep, beginNewCycle,
  }
}
