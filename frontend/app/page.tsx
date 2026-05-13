"use client"

import { useEffect, useState } from "react"
import { FileText, MessageSquare } from "lucide-react"
import { OnboardingModal } from "@/components/onboarding-modal"
import { TopNav } from "@/components/top-nav"
import { SourceListPanel } from "@/components/home/source-list-panel"
import { ChatListPanel } from "@/components/home/chat-list-panel"
import { ChatTopBar } from "@/components/home/chat-top-bar"
import { ChatMessages } from "@/components/home/chat-messages"
import { ChatInput } from "@/components/home/chat-input"
import { RightSidebar } from "@/components/home/right-sidebar"
import { api } from "@/lib/api"
import { useSourceManagement } from "@/hooks/useSourceManagement"
import { useChatManagement } from "@/hooks/useChatManagement"
import { useSidebarResize } from "@/hooks/useSidebarResize"
import type { LeftTab } from "@/components/home/types"
import { toast } from "sonner"

const leftTabStorageKey = "reflect_left_tab"

export default function HomePage() {
  const [leftTab, setLeftTab] = useState<LeftTab>("sources")
  const [isRunningSearch, setIsRunningSearch] = useState(false)
  const [tagFilter, setTagFilter] = useState<string[]>([])

  const sources = useSourceManagement()
  const chats = useChatManagement({
    rawSources: sources.rawSources,
    setRawSources: sources.setRawSources,
    setProcessingSources: sources.setProcessingSources,
  })
  const sidebar = useSidebarResize()

  useEffect(() => {
    if (typeof window === "undefined") return
    const saved = window.localStorage.getItem(leftTabStorageKey)
    if (saved === "chats" || saved === "sources") setLeftTab(saved)
  }, [])

  useEffect(() => {
    if (typeof window === "undefined") return
    const params = new URLSearchParams(window.location.search)
    const tags = params.getAll("tag").filter(Boolean)
    if (tags.length > 0) {
      setTagFilter(tags)
      setLeftTab("sources")
    }
  }, [])

  const handleToggleTagFilter = (tag: string) => {
    setTagFilter((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    )
  }

  useEffect(() => {
    if (typeof window !== "undefined") window.localStorage.setItem(leftTabStorageKey, leftTab)
  }, [leftTab])

  const hasIncludedSources = sources.includedSources.length > 0

  const handleNewChat = () => {
    chats.resetChatState()
    setLeftTab("chats")
  }

  const exportToMarkdown = () => {
    if (!hasIncludedSources) { toast.error("Select at least one included source before exporting."); return }
    let markdown = `# Reflection\n\n## Sources\n\n`
    sources.includedSources.forEach((source) => {
      if (source.type === "recording") markdown += `- Voice note (${source.duration}) - ${source.timestamp}\n`
      else if (source.type === "text") markdown += `- ${source.content} - ${source.timestamp}\n`
      else markdown += `- File: ${source.name} - ${source.timestamp}\n`
    })
    markdown += `\n## Reflections\n\n`
    let pendingQuestion: string | null = null
    chats.activeChatMessages.forEach((message) => {
      if (message.role === "question") { pendingQuestion = message.text; return }
      if (pendingQuestion) { markdown += `**Q:** ${pendingQuestion}\n\n`; pendingQuestion = null }
      const answer = message.scale_value !== null && message.scale_value !== undefined
        ? `${message.scale_value}/${message.scale_max ?? 10}`
        : message.text
      markdown += `**A:** ${answer}\n\n---\n\n`
    })
    if (pendingQuestion) markdown += `**Q:** ${pendingQuestion}\n\n---\n\n`
    const blob = new Blob([markdown], { type: "text/markdown" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url; a.download = "reflection.md"; a.click()
    URL.revokeObjectURL(url)
    toast(`Exported ${sources.includedSources.length} included source${sources.includedSources.length === 1 ? "" : "s"}.`)
  }

  const handleAISearch = async () => {
    if (!hasIncludedSources) { toast.error("Select at least one included source before using AI Search."); return }
    setIsRunningSearch(true)
    try {
      const context = sources.includedSources.map((s) => s.content).filter(Boolean).join("\n").slice(0, 2000)
      const answer = await api.query(`Summarize the key themes in these selected sources and keep it concise:\n${context || "No text available."}`)
      toast("AI Search", { description: answer.answer, duration: 12000 })
    } catch (error) {
      toast.error(`AI Search failed: ${error instanceof Error ? error.message : "Unknown error"}`)
    } finally {
      setIsRunningSearch(false)
    }
  }

  return (
    <div className="h-screen bg-background flex flex-col overflow-hidden">
      <OnboardingModal
        open={sources.isOnboardingOpen}
        onSkip={sources.handleOnboardingSkip}
        onSubmit={sources.handleOnboardingSubmit}
      />
      <TopNav activePath="/" />

      <div className="flex-1 flex min-h-0">
        <aside
          className="border-r flex flex-col bg-muted/10 relative shrink-0 min-h-0"
          style={{ width: sidebar.leftSidebarWidth }}
        >
          <div className="px-4 pt-3 border-b">
            <div className="flex gap-1 mb-3">
              <button
                onClick={() => setLeftTab("sources")}
                className={`flex-1 flex items-center justify-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md transition-colors ${
                  leftTab === "sources" ? "bg-background border shadow-sm" : "text-muted-foreground hover:bg-muted/50"
                }`}
              >
                <FileText className="h-3.5 w-3.5" />
                Sources
              </button>
              <button
                onClick={() => setLeftTab("chats")}
                className={`flex-1 flex items-center justify-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md transition-colors ${
                  leftTab === "chats" ? "bg-background border shadow-sm" : "text-muted-foreground hover:bg-muted/50"
                }`}
              >
                <MessageSquare className="h-3.5 w-3.5" />
                Chats
              </button>
            </div>
          </div>

          {leftTab === "sources" ? (
            <SourceListPanel
              rawSources={sources.rawSources}
              includedSources={sources.includedSources}
              isLoadingSources={sources.isLoadingSources}
              addSourceMode={sources.addSourceMode}
              setAddSourceMode={sources.setAddSourceMode}
              newSourceText={sources.newSourceText}
              setNewSourceText={sources.setNewSourceText}
              isSavingSource={sources.isSavingSource}
              isDragOverUpload={sources.isDragOverUpload}
              isRecording={sources.isRecording}
              recordingSeconds={sources.recordingSeconds}
              fileInputRef={sources.fileInputRef}
              tagFilter={tagFilter}
              onToggleTagFilter={handleToggleTagFilter}
              onSetSourceIncluded={sources.handleSetSourceIncluded}
              onAddTextSource={sources.handleAddTextSource}
              onAddFileSource={sources.handleAddFileSource}
              onFileDrop={sources.handleFileDrop}
              onFileDragEnter={sources.handleFileDragEnter}
              onFileDragOver={sources.handleFileDragOver}
              onFileDragLeave={sources.handleFileDragLeave}
              onToggleRecording={sources.handleToggleRecording}
              onCloseRecordingPanel={sources.handleCloseRecordingPanel}
              rawUploadUrl={sources.rawUploadUrl}
            />
          ) : (
            <ChatListPanel
              chats={chats.chats}
              isLoadingChats={chats.isLoadingChats}
              activeChatId={chats.activeChatId}
              renamingChatId={chats.renamingChatId}
              renameDraft={chats.renameDraft}
              setRenameDraft={chats.setRenameDraft}
              onNewChat={handleNewChat}
              onSelectChat={chats.handleSelectChat}
              onStartRenameChat={chats.handleStartRenameChat}
              onCommitRename={chats.handleCommitRename}
              onCancelRename={() => chats.setRenamingChatId(null)}
              onDeleteChat={chats.handleDeleteChat}
            />
          )}

          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize left sidebar"
            onMouseDown={(e) => sidebar.handleSidebarResizeStart("left", e)}
            className="absolute top-0 right-0 h-full w-1 translate-x-1/2 cursor-col-resize bg-transparent hover:bg-emerald-500/30 transition-colors"
          />
        </aside>

        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          {chats.activeChatId !== null && chats.activeChat && (
            <ChatTopBar
              activeChat={chats.activeChat}
              activeChatSourceId={chats.activeChatSourceId}
              activeChatLinkedSourceStatus={chats.activeChatLinkedSourceStatus}
              isLinkedSourceProcessing={chats.isLinkedSourceProcessing}
              isPromotingChat={chats.isPromotingChat}
              activeChatMessages={chats.activeChatMessages}
              onPromoteChat={chats.handlePromoteChat}
            />
          )}
          <ChatMessages
            activeChatMessages={chats.activeChatMessages}
            activeChatId={chats.activeChatId}
            isLoadingActiveChat={chats.isLoadingActiveChat}
            isGeneratingQuestion={chats.isGeneratingQuestion}
            currentQuestion={chats.currentQuestion}
            onScaleSelect={chats.handleScaleSelect}
          />
          <ChatInput
            currentQuestion={chats.currentQuestion}
            inputValue={chats.inputValue}
            setInputValue={chats.setInputValue}
            isGeneratingQuestion={chats.isGeneratingQuestion}
            onSubmitText={chats.handleSubmitText}
            onSelectQuestionType={chats.handleSelectQuestionType}
          />
        </div>

        <aside
          className="border-l flex flex-col bg-muted/10 relative shrink-0 min-h-0"
          style={{ width: sidebar.rightSidebarWidth }}
        >
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize right sidebar"
            onMouseDown={(e) => sidebar.handleSidebarResizeStart("right", e)}
            className="absolute top-0 left-0 h-full w-1 -translate-x-1/2 cursor-col-resize bg-transparent hover:bg-emerald-500/30 transition-colors"
          />
          <RightSidebar
            hasIncludedSources={hasIncludedSources}
            isRunningSearch={isRunningSearch}
            onExportMarkdown={exportToMarkdown}
            onAISearch={handleAISearch}
          />
        </aside>
      </div>
    </div>
  )
}
