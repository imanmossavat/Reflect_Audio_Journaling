"use client"

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react"
import { api, type ChatStreamStageName, type GuardUnavailableInfo, type SafetyKind } from "@/lib/api"
import { toast } from "sonner"

// Streaming-answer shapes (formerly local to useChatManagement). They live here now
// because the generation state is owned by this provider so it can survive route
// navigation and refresh.
export type StreamingStage = {
  name: ChatStreamStageName
  count?: number
  done: boolean
}

export type StreamingAssistant = {
  stages: StreamingStage[]
  thinking: string
  answer: string
  /** Buffered answer length from the backend — drives the pulsing "skeleton reveal". The
   *  real text never streams; it arrives via the persisted message after the guard passes. */
  progressChars: number
}

type GenerationStatus = "active" | "done" | "error" | "fallback" | "guard_unavailable"

type GenerationEntry = StreamingAssistant & { status: GenerationStatus }

export type GenerationDoneInfo = { model: string | null; message_id: number }
export type GenerationFallbackInfo = { kind: SafetyKind }
export type GenerationFinishInfo =
  | GenerationDoneInfo
  | GenerationFallbackInfo
  | GuardUnavailableInfo
  | null

export type GenerationOutcome = "done" | "error" | "fallback" | "guard_unavailable"

// Fired when a generation finishes. Consumers refetch the chat's persisted messages (done),
// surface a support card (fallback), or show the guard setup card (guard_unavailable).
type CompleteListener = (
  chatId: number,
  outcome: GenerationOutcome,
  info: GenerationFinishInfo,
) => void

interface GenerationContextValue {
  /** Begin a text-answer generation for a chat (the user already persisted their turn). */
  startTextGeneration: (chatId: number, question: string) => void
  /** The live streaming state for a chat, or null if nothing is streaming there. */
  generationFor: (chatId: number | null) => StreamingAssistant | null
  /** Chats with a generation still in progress — drives the sidebar spinner. */
  generatingChatIds: Set<number>
  /** Drop a chat's streaming entry (after the persisted message has replaced it). */
  clearGeneration: (chatId: number) => void
  /** Subscribe to completion events; returns an unsubscribe fn. */
  onComplete: (listener: CompleteListener) => () => void
}

const GenerationContext = createContext<GenerationContextValue | null>(null)

// How long a finished entry lingers before auto-clearing, as a safety net for chats no
// consumer is watching (e.g. it finished while the user was on another route).
const FINISHED_RETENTION_MS = 2000

const EMPTY_ENTRY: GenerationEntry = { stages: [], thinking: "", answer: "", progressChars: 0, status: "active" }

export function GenerationProvider({ children }: { children: React.ReactNode }) {
  const [entries, setEntries] = useState<Record<number, GenerationEntry>>({})
  // Stream cancel fns keyed by chat, so we never double-subscribe to the same chat.
  const cancelers = useRef<Map<number, () => void>>(new Map())
  const completeListeners = useRef<Set<CompleteListener>>(new Set())

  const updateEntry = useCallback((chatId: number, fn: (entry: GenerationEntry) => GenerationEntry) => {
    setEntries((prev) => ({ ...prev, [chatId]: fn(prev[chatId] ?? EMPTY_ENTRY) }))
  }, [])

  const clearGeneration = useCallback((chatId: number) => {
    setEntries((prev) => {
      if (!(chatId in prev)) return prev
      const next = { ...prev }
      delete next[chatId]
      return next
    })
  }, [])

  const finish = useCallback(
    (chatId: number, outcome: GenerationOutcome, info: GenerationFinishInfo) => {
      updateEntry(chatId, (entry) => ({ ...entry, status: outcome }))
      cancelers.current.delete(chatId)
      completeListeners.current.forEach((listener) => listener(chatId, outcome, info))
      // Safety net: if no consumer cleared it (e.g. it finished while the user was on
      // another page), drop it so it can't linger and double-render later.
      setTimeout(() => clearGeneration(chatId), FINISHED_RETENTION_MS)
    },
    [updateEntry, clearGeneration]
  )

  // Shared SSE handlers that write a chat's stream into its entry. Used for both a
  // freshly-started generation and a resumed (reconnected) one.
  const handlersFor = useCallback(
    (chatId: number) => ({
      onStage: ({ name, count }: { name: ChatStreamStageName; count?: number }) => {
        updateEntry(chatId, (entry) => {
          const stages = entry.stages.map((s) => ({ ...s, done: true }))
          stages.push({ name, count, done: false })
          return { ...entry, stages, status: "active" as GenerationStatus }
        })
      },
      onProgress: (chars: number) => {
        updateEntry(chatId, (entry) => ({ ...entry, progressChars: chars, status: "active" as GenerationStatus }))
      },
      onDone: (info: GenerationDoneInfo) => finish(chatId, "done", info),
      onFallback: (kind: SafetyKind) => finish(chatId, "fallback", { kind }),
      onGuardUnavailable: (info: GuardUnavailableInfo) => finish(chatId, "guard_unavailable", info),
      onError: (error: Error) => {
        toast.error(error.message.replace(/^API\s+\d+:\s*/, ""))
        finish(chatId, "error", null)
      },
      onIdle: () => {
        // Reconnected but nothing is generating anymore — drop any seeded entry.
        clearGeneration(chatId)
        cancelers.current.delete(chatId)
      },
    }),
    [updateEntry, finish, clearGeneration]
  )

  const startTextGeneration = useCallback(
    (chatId: number, question: string) => {
      if (cancelers.current.has(chatId)) return
      setEntries((prev) => ({ ...prev, [chatId]: { ...EMPTY_ENTRY } }))
      const cancel = api.streamQuery({ chatId, question }, handlersFor(chatId))
      cancelers.current.set(chatId, cancel)
    },
    [handlersFor]
  )

  // On mount, reconnect to any generation already running on the backend (e.g. it was
  // kicked off in another tab, or this is a refresh mid-answer). subscribeGeneration
  // replays buffered events so the partial answer reappears, then streams live.
  useEffect(() => {
    let cancelled = false
    void api
      .listActiveGenerations()
      .then((active) => {
        if (cancelled) return
        for (const { chat_id } of active) {
          if (cancelers.current.has(chat_id)) continue
          setEntries((prev) => (chat_id in prev ? prev : { ...prev, [chat_id]: { ...EMPTY_ENTRY } }))
          const cancel = api.subscribeGeneration(chat_id, handlersFor(chat_id))
          cancelers.current.set(chat_id, cancel)
        }
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
    // handlersFor is stable for the provider's lifetime; run once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const generationFor = useCallback(
    (chatId: number | null): StreamingAssistant | null => {
      if (chatId === null) return null
      const entry = entries[chatId]
      // A terminal non-answer (error, guard tripped, or guard unavailable) shows a card or
      // toast — not a streaming bubble — so hide the bubble for those.
      if (
        !entry ||
        entry.status === "error" ||
        entry.status === "fallback" ||
        entry.status === "guard_unavailable"
      )
        return null
      return { stages: entry.stages, thinking: entry.thinking, answer: entry.answer, progressChars: entry.progressChars }
    },
    [entries]
  )

  const generatingChatIds = useMemo(() => {
    const ids = new Set<number>()
    for (const [id, entry] of Object.entries(entries)) {
      if (entry.status === "active") ids.add(Number(id))
    }
    return ids
  }, [entries])

  const onComplete = useCallback((listener: CompleteListener) => {
    completeListeners.current.add(listener)
    return () => completeListeners.current.delete(listener)
  }, [])

  const value = useMemo<GenerationContextValue>(
    () => ({ startTextGeneration, generationFor, generatingChatIds, clearGeneration, onComplete }),
    [startTextGeneration, generationFor, generatingChatIds, clearGeneration, onComplete]
  )

  return <GenerationContext.Provider value={value}>{children}</GenerationContext.Provider>
}

export function useGeneration(): GenerationContextValue {
  const ctx = useContext(GenerationContext)
  if (!ctx) throw new Error("useGeneration must be used within a GenerationProvider")
  return ctx
}
