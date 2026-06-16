"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { api, type ChatSummary, type ChatMessageRecord, PROCESSING_STATUSES } from "@/lib/api"
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
  // Don't persist activeChatId until we've restored it from storage on mount,
  // otherwise the initial null would wipe the stored value before we read it.
  const hasRestoredActiveChat = useRef(false)

  useEffect(() => {
    const loadChats = async () => {
      setIsLoadingChats(true)
      try {
        const list = await api.listChats()
        setChats(list)
        // Restore the last active chat after mount (not during render, to avoid an
        // SSR/client hydration mismatch). Only restore it if it still exists.
        setActiveChatId((prev) => {
          const candidate = prev ?? readStoredActiveChatId()
          return candidate !== null && list.some((c) => c.id === candidate) ? candidate : prev
        })
      } catch (error) {
        toast.error(`Could not load chats: ${error instanceof Error ? error.message : "Unknown error"}`)
      } finally {
        hasRestoredActiveChat.current = true
        setIsLoadingChats(false)
      }
    }
    void loadChats()
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
    if (activeChatId === null) { setActiveChatMessages([]); return }
    const loadChat = async () => {
      setIsLoadingActiveChat(true)
      try {
        const detail = await api.getChat(activeChatId)
        setActiveChatMessages(detail.messages)
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

  const handleSubmitText = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = inputValue.trim()
    if (!trimmed || isAssistantThinking) return
    setInputValue("")
    let chatId: number
    try {
      chatId = await ensureActiveChat()
      await persistMessage(chatId, { role: "answer", text: trimmed })
    } catch (error) {
      toast.error(`Could not save message: ${error instanceof Error ? error.message : "Unknown error"}`)
      return
    }
    // In guided reflection mode the facilitator responds conversationally to each
    // typed answer (rather than running a full source-grounded query).
    if (gibbsActive) {
      await generateGibbsReply(chatId, trimmed)
      return
    }
    // Hand off to the provider: it runs the answer server-side (so it survives leaving
    // the page) and streams it back. Completion is handled by the onComplete effect.
    generation.startTextGeneration(chatId, trimmed)
  }

  // When a query generation finishes, fold its answer into the on-screen chat (if it's
  // the one in view) and drop the streaming entry. Runs for generations started here or
  // resumed after a refresh. The provider also auto-clears as a safety net.
  useEffect(() => {
    return generation.onComplete((chatId, outcome, info) => {
      if (outcome === "done" && info && activeChatIdRef.current === chatId) {
        void (async () => {
          try {
            const detail = await api.getChat(chatId)
            const created = detail.messages.find((m) => m.id === info.message_id)
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

  // Build the conversation so far as Q&A pairs for the facilitator. Pass `appendAnswer`
  // to include a just-typed answer that may not be in `activeChatMessages` state yet
  // (state updates are async; this closure still holds the pre-answer list).
  const buildGibbsHistory = (appendAnswer?: string): Array<Record<string, unknown>> => {
    const msgs: Array<Pick<ChatMessageRecord, "role" | "text">> = appendAnswer
      ? [...activeChatMessages, { role: "answer", text: appendAnswer }]
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

  // Shared streaming runner for the conversational Gibbs facilitator. The facilitator's
  // reply is persisted as a "question" (assistant) message so it renders on the AI side.
  const streamFacilitator = async (
    chatId: number,
    mode: "deep_dive" | "clarifying" | "reply",
    step: number,
    history: Array<Record<string, unknown>>
  ) => {
    // Ground the facilitator in the user's included sources (mirrors AI Search).
    const journalText = rawSources
      .filter((s) => s.included)
      .map((s) => s.content)
      .filter(Boolean)
      .join("\n")
      .slice(0, 2000)

    setGibbsGenerating(true)
    setStreamingChatId(chatId)
    setStreamingAssistant({ stages: [], thinking: "", answer: "" })
    let acc = ""
    await new Promise<void>((resolve) => {
      api.streamGeneratedQuestion(
        { mode, step, journal_text: journalText || undefined, history },
        {
          onToken: (token) => {
            acc += token
            setStreamingAssistant((prev) => (prev ? { ...prev, answer: prev.answer + token } : prev))
          },
          onDone: async () => {
            const text = acc.trim()
            try {
              // persistMessage guards the on-screen append by chat id; the message
              // is always saved server-side even if the user switched chats.
              if (text) await persistMessage(chatId, { role: "question", text })
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

  const generateGibbsQuestion = async (targetStep: number, mode: "deep_dive" | "clarifying" = "deep_dive") => {
    let chatId: number
    try {
      chatId = await ensureActiveChat()
    } catch (error) {
      toast.error(`Could not start reflection: ${error instanceof Error ? error.message : "Unknown error"}`)
      return
    }
    await streamFacilitator(chatId, mode, targetStep, buildGibbsHistory())
  }

  // The facilitator responds to a typed answer within the current stage.
  const generateGibbsReply = async (chatId: number, answerText: string) => {
    await streamFacilitator(chatId, "reply", gibbsStep, buildGibbsHistory(answerText))
  }

  const startReflection = async () => {
    if (gibbsGenerating) return
    setGibbsActive(true)
    setGibbsStep(1)
    await generateGibbsQuestion(1, "deep_dive")
  }

  const advanceGibbsStep = async () => {
    if (gibbsGenerating) return
    if (gibbsStep >= GIBBS_STEP_COUNT) {
      setGibbsActive(false) // already at the final stage — "Finish"
      return
    }
    const next = gibbsStep + 1
    setGibbsStep(next)
    await generateGibbsQuestion(next, "deep_dive")
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
  }

  const handleSelectChat = (chatId: number) => {
    setActiveChatId(chatId)
    setInputValue("")
    setGibbsActive(false)
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

  const handleDeleteChat = async (chat: ChatSummary, event: React.MouseEvent) => {
    event.stopPropagation()
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

  const handlePromoteChat = async () => {
    if (activeChatId === null || isPromotingChat) return
    setIsPromotingChat(true)
    try {
      if (activeChatSourceId === null) {
        const result = await api.promoteChat(activeChatId)
        setChats((prev) => prev.map((c) => (c.id === activeChatId ? { ...c, source_id: result.source.id } : c)))
        setRawSources((prev) => [mapBackendSource(result.source), ...prev])
        setProcessingSources((prev) => new Set([...prev, result.source.id]))
        toast("Chat promoted — indexing in background.")
      } else {
        const updated = await api.reindexChat(activeChatId)
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
    resetChatState,
    gibbsActive, gibbsStep, gibbsGenerating,
    startReflection, advanceGibbsStep, askClarifying, exitReflection, handleSelectGibbsStep,
  }
}
