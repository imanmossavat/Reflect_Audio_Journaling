"use client"

import { useEffect, useMemo, useState } from "react"
import { api, type ChatSummary, type ChatMessageRecord, PROCESSING_STATUSES } from "@/lib/api"
import type { RawSource } from "@/components/home/types"
import { mapBackendSource } from "@/hooks/useSourceManagement"
import { toast } from "sonner"

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
  const [inputValue, setInputValue] = useState("")
  const [isAssistantThinking, setIsAssistantThinking] = useState(false)

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
    setIsAssistantThinking(true)
    try {
      const result = await api.query(trimmed)
      const answer = result.answer?.trim() || "(empty response)"
      await persistMessage(chatId, { role: "question", text: answer })
    } catch (error) {
      toast.error(`Assistant failed: ${error instanceof Error ? error.message : "Unknown error"}`)
    } finally {
      setIsAssistantThinking(false)
    }
  }

  const handleSelectChat = (chatId: number) => {
    setActiveChatId(chatId)
    setInputValue("")
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
  }

  return {
    chats, activeChatId, activeChatMessages, isLoadingChats, isLoadingActiveChat,
    renamingChatId, renameDraft, setRenameDraft, setRenamingChatId,
    isPromotingChat, inputValue, setInputValue, isAssistantThinking,
    activeChat, activeChatSourceId, activeChatLinkedSourceStatus, isLinkedSourceProcessing,
    handleSelectChat, handleStartRenameChat, handleStartRenameActiveChat, handleCommitRename, handleDeleteChat,
    handlePromoteChat, handleSubmitText,
    resetChatState,
  }
}
