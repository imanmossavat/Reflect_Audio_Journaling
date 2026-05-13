"use client"

import { useEffect, useMemo, useState } from "react"
import { api, type ChatSummary, type ChatMessageRecord, PROCESSING_STATUSES } from "@/lib/api"
import type { RawSource, CurrentQuestion, QuestionType } from "@/components/home/types"
import { mapBackendSource } from "@/hooks/useSourceManagement"
import { toast } from "sonner"

const MAX_HISTORY_MESSAGES = 20

const quantitativeQuestions = [
  { question: "How much is stress affecting your life right now?", lowLabel: "Not at all", highLabel: "Significantly" },
  { question: "How energized do you feel today?", lowLabel: "Exhausted", highLabel: "Very energized" },
  { question: "How confident are you feeling about your progress?", lowLabel: "Not confident", highLabel: "Very confident" },
  { question: "How well did you sleep last night?", lowLabel: "Very poorly", highLabel: "Very well" },
  { question: "How anxious are you feeling right now?", lowLabel: "Not at all", highLabel: "Extremely" },
]

const guidedQuestions = [
  "What moment from today are you most grateful for?",
  "What challenge did you face recently, and what did you learn from it?",
  "How did you take care of yourself this week?",
  "What's one thing you'd like to let go of?",
  "What are you looking forward to?",
]

const clarifyingQuestions = [
  "Can you tell me more about what led to that?",
  "How did that make you feel in the moment?",
  "What do you think triggered that response?",
  "What would the ideal outcome look like for you?",
  "Is there a pattern you've noticed here before?",
]

interface UseChatManagementOptions {
  rawSources: RawSource[]
  setRawSources: React.Dispatch<React.SetStateAction<RawSource[]>>
  setProcessingSources: React.Dispatch<React.SetStateAction<Set<number>>>
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
  const [currentQuestion, setCurrentQuestion] = useState<CurrentQuestion | null>(null)
  const [inputValue, setInputValue] = useState("")
  const [isGeneratingQuestion, setIsGeneratingQuestion] = useState(false)

  useEffect(() => {
    const loadChats = async () => {
      setIsLoadingChats(true)
      try {
        const list = await api.listChats()
        setChats(list)
      } catch (error) {
        toast.error(`Could not load chats: ${error instanceof Error ? error.message : "Unknown error"}`)
      } finally {
        setIsLoadingChats(false)
      }
    }
    void loadChats()
  }, [])

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
      setActiveChatMessages((prev) => [...prev, created])
      void refreshChats()
      return created
    } catch (error) {
      toast.error(`Could not save message: ${error instanceof Error ? error.message : "Unknown error"}`)
      return null
    }
  }

  const buildHistoryForGeneration = (): Array<Record<string, unknown>> =>
    activeChatMessages.slice(-MAX_HISTORY_MESSAGES).map((m) => ({
      role: m.role === "question" ? "assistant" : "user",
      content: m.text,
    }))

  const pickFallbackQuestion = (type: QuestionType) =>
    type === "guided"
      ? guidedQuestions[Math.floor(Math.random() * guidedQuestions.length)]
      : clarifyingQuestions[Math.floor(Math.random() * clarifyingQuestions.length)]

  const handleSelectQuestionType = async (type: QuestionType) => {
    let question: string
    let scaleData: { lowLabel: string; highLabel: string } | undefined

    if (type === "quantitative") {
      const random = quantitativeQuestions[Math.floor(Math.random() * quantitativeQuestions.length)]
      question = random.question
      scaleData = { lowLabel: random.lowLabel, highLabel: random.highLabel }
    } else {
      setIsGeneratingQuestion(true)
      setCurrentQuestion({ type, content: "", scaleData: undefined })
      try {
        const mode = type === "guided" ? "deep_dive" : "clarifying"
        const history = buildHistoryForGeneration()
        question = await new Promise<string>((resolve, reject) => {
          let generated = ""
          api.streamGeneratedQuestion(
            { mode, history: history.length > 0 ? history : undefined },
            {
              onToken(token) {
                generated += token
                setCurrentQuestion({ type, content: generated, scaleData: undefined })
              },
              onDone() { resolve(generated.trim()) },
              onError(error) { reject(error) },
            }
          )
        })
        if (!question) {
          question = pickFallbackQuestion(type)
          toast("Question generator returned no content — using a local prompt.")
        }
      } catch (error) {
        question = pickFallbackQuestion(type)
        toast.error(`Question generation unavailable (${error instanceof Error ? error.message : "Unknown error"}). Using a local prompt.`)
      } finally {
        setIsGeneratingQuestion(false)
      }
    }

    setCurrentQuestion({ type, content: question, scaleData })
    if (activeChatId !== null && type !== "quantitative")
      void persistMessage(activeChatId, { role: "question", text: question })
  }

  const handleScaleSelect = async (value: number) => {
    const promptQuestion = currentQuestion?.content ?? "How are you feeling right now?"
    const scaleData = currentQuestion?.scaleData
    setCurrentQuestion(null)
    try {
      const chatId = await ensureActiveChat()
      await persistMessage(chatId, { role: "question", text: promptQuestion })
      await persistMessage(chatId, {
        role: "answer", text: `${value}/10`, scale_value: value, scale_max: 10,
        scale_low_label: scaleData?.lowLabel ?? null, scale_high_label: scaleData?.highLabel ?? null,
      })
    } catch (error) {
      toast.error(`Could not save answer: ${error instanceof Error ? error.message : "Unknown error"}`)
    }
  }

  const handleSubmitText = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmedAnswer = inputValue.trim()
    if (!trimmedAnswer) return
    const promptQuestion = currentQuestion?.content ?? "Reflection"
    const chatExistedBeforeSubmit = activeChatId !== null
    setInputValue("")
    setCurrentQuestion(null)
    try {
      const chatId = await ensureActiveChat()
      if (!chatExistedBeforeSubmit)
        await persistMessage(chatId, { role: "question", text: promptQuestion })
      await persistMessage(chatId, { role: "answer", text: trimmedAnswer })
    } catch (error) {
      toast.error(`Could not save answer: ${error instanceof Error ? error.message : "Unknown error"}`)
    }
  }

  const handleSelectChat = (chatId: number) => {
    setActiveChatId(chatId)
    setCurrentQuestion(null)
    setInputValue("")
  }

  const handleStartRenameChat = (chat: ChatSummary, event: React.MouseEvent) => {
    event.stopPropagation()
    setRenamingChatId(chat.id)
    setRenameDraft(chat.title)
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
        toast("Re-indexing chat content...")
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
    setCurrentQuestion(null)
    setInputValue("")
  }

  return {
    chats, activeChatId, activeChatMessages, isLoadingChats, isLoadingActiveChat,
    renamingChatId, renameDraft, setRenameDraft, setRenamingChatId,
    isPromotingChat, currentQuestion, inputValue, setInputValue, isGeneratingQuestion,
    activeChat, activeChatSourceId, activeChatLinkedSourceStatus, isLinkedSourceProcessing,
    handleSelectChat, handleStartRenameChat, handleCommitRename, handleDeleteChat,
    handlePromoteChat, handleSelectQuestionType, handleScaleSelect, handleSubmitText,
    resetChatState,
  }
}
