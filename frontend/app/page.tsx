"use client"

import { useEffect, useState } from "react"
import {
  FileText,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  Mic,
  Type,
  File as FileIcon,
  MessageCircle,
  Sparkles,
} from "lucide-react"
import { OnboardingModal } from "@/components/onboarding-modal"
import { TopNav } from "@/components/top-nav"
import { SourceListPanel } from "@/components/home/source-list-panel"
import { ChatListPanel } from "@/components/home/chat-list-panel"
import { ChatTopBar } from "@/components/home/chat-top-bar"
import { ChatMessages } from "@/components/home/chat-messages"
import { ChatInput } from "@/components/home/chat-input"
import { ReflectionBanner } from "@/components/home/reflection-banner"
import { RightSidebar } from "@/components/home/right-sidebar"
import { NewSourceMenu } from "@/components/home/new-source-menu"
import { NoteEditor } from "@/components/home/note-editor"
import { GraphStage } from "@/components/home/graph-stage"
import { StageHeader } from "@/components/home/stage-header"
import { api, type AppSettings, type OllamaModelEntry } from "@/lib/api"
import { useSourceManagement } from "@/hooks/useSourceManagement"
import { useChatManagement } from "@/hooks/useChatManagement"
import { useSidebarResize } from "@/hooks/useSidebarResize"
import type { LeftTab } from "@/components/home/types"
import { toast } from "sonner"

const leftTabStorageKey = "reflect_left_tab"

type Stage = "chat" | "note" | "graph"

export default function HomePage() {
  const [leftTab, setLeftTab] = useState<LeftTab>("sources")
  const [stage, setStage] = useState<Stage>("chat")
  const [isRunningSearch, setIsRunningSearch] = useState(false)
  const [tagFilter, setTagFilter] = useState<string[]>([])
  const [appSettings, setAppSettings] = useState<AppSettings | null>(null)
  const [installedModels, setInstalledModels] = useState<OllamaModelEntry[]>([])
  const [isOllamaReachable, setIsOllamaReachable] = useState(true)
  const [isSavingChatModel, setIsSavingChatModel] = useState(false)

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

  // Esc returns from the graph stage back to the base chat layer. The note
  // stage is intentionally excluded so in-progress writing is never discarded.
  useEffect(() => {
    if (stage !== "graph") return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setStage("chat")
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [stage])

  useEffect(() => {
    void api.getSettings().then(setAppSettings).catch(() => {})
    void api
      .listOllamaModels()
      .then((listing) => {
        setIsOllamaReachable(listing.available)
        setInstalledModels(listing.models)
      })
      .catch(() => setIsOllamaReachable(false))
  }, [])

  const handleChangeChatModel = async (model: string) => {
    if (!appSettings || appSettings.chat_model === model) return
    setIsSavingChatModel(true)
    try {
      const updated = await api.updateSettings({ chat_model: model })
      setAppSettings(updated)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update chat model")
    } finally {
      setIsSavingChatModel(false)
    }
  }

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
        {sidebar.isLeftCollapsed ? (
          <div className="border-r flex flex-col items-center bg-muted/10 shrink-0 min-h-0 w-12 py-2">
            <button
              onClick={sidebar.toggleLeftCollapsed}
              aria-label="Show sources and chats panel"
              title="Show panel"
              className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors"
            >
              <PanelLeftOpen className="h-4 w-4" />
            </button>
            <button
              onClick={() => {
                sources.setAddSourceMode(null)
                setLeftTab("sources")
                sidebar.toggleLeftCollapsed()
              }}
              aria-label="Add a source"
              title="Add a source"
              className="mt-1 flex h-8 w-8 items-center justify-center rounded-md border border-dashed text-muted-foreground hover:border-emerald-500 hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors"
            >
              <Plus className="h-4 w-4" />
            </button>
            <span
              className="mt-2 text-[10px] font-medium tabular-nums text-muted-foreground"
              title={`${sources.includedSources.length} of ${sources.rawSources.length} sources included`}
            >
              {sources.includedSources.length}/{sources.rawSources.length}
            </span>
            <div className="mt-2 flex-1 min-h-0 w-full overflow-y-auto no-scrollbar flex flex-col items-center gap-1.5">
              {sources.rawSources.map((source) => (
                <button
                  key={source.id}
                  onClick={() => {
                    setLeftTab("sources")
                    sidebar.toggleLeftCollapsed()
                  }}
                  title={source.name}
                  aria-label={source.name}
                  className={`flex h-7 w-7 items-center justify-center rounded-md transition-opacity hover:opacity-100 ${
                    source.included ? "opacity-100" : "opacity-50"
                  } ${
                    source.type === "recording"
                      ? "bg-emerald-100 dark:bg-emerald-900/30"
                      : source.type === "file"
                        ? "bg-blue-100 dark:bg-blue-900/30"
                        : "bg-amber-100 dark:bg-amber-900/30"
                  }`}
                >
                  {source.type === "recording" ? (
                    <Mic className="h-3 w-3 text-emerald-600" />
                  ) : source.type === "file" ? (
                    <FileIcon className="h-3 w-3 text-blue-600" />
                  ) : (
                    <Type className="h-3 w-3 text-amber-600" />
                  )}
                </button>
              ))}
            </div>
          </div>
        ) : (
        <aside
          className="border-r flex flex-col bg-muted/10 relative shrink-0 min-h-0"
          style={{ width: sidebar.leftSidebarWidth }}
        >
          <div className="border-b flex h-12 shrink-0">
            <button
              onClick={() => setLeftTab("sources")}
              className={`flex-1 flex items-center justify-center gap-1.5 text-xs font-medium transition-colors ${
                leftTab === "sources"
                  ? "bg-background border-b-2 border-emerald-500"
                  : "text-muted-foreground hover:bg-muted/50"
              }`}
            >
              <FileText className="h-3.5 w-3.5" />
              Sources
            </button>
            <button
              onClick={() => setLeftTab("chats")}
              className={`flex-1 flex items-center justify-center gap-1.5 text-xs font-medium transition-colors ${
                leftTab === "chats"
                  ? "bg-background border-b-2 border-emerald-500"
                  : "text-muted-foreground hover:bg-muted/50"
              }`}
            >
              <MessageSquare className="h-3.5 w-3.5" />
              Chats
            </button>
            <button
              onClick={sidebar.toggleLeftCollapsed}
              aria-label="Hide panel"
              title="Hide panel"
              className="flex w-10 items-center justify-center border-l text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors shrink-0"
            >
              <PanelLeftClose className="h-3.5 w-3.5" />
            </button>
          </div>

          {leftTab === "sources" ? (
            <>
              <div className="p-3 border-b flex items-center justify-between">
                <h2 className="text-sm font-medium">Library</h2>
                <NewSourceMenu
                  addSourceMode={sources.addSourceMode}
                  setAddSourceMode={sources.setAddSourceMode}
                  onNewNote={() => setStage("note")}
                  isSavingSource={sources.isSavingSource}
                  isDragOverUpload={sources.isDragOverUpload}
                  isRecording={sources.isRecording}
                  recordingSeconds={sources.recordingSeconds}
                  fileInputRef={sources.fileInputRef}
                  onAddFileSource={sources.handleAddFileSource}
                  onFileDrop={sources.handleFileDrop}
                  onFileDragEnter={sources.handleFileDragEnter}
                  onFileDragOver={sources.handleFileDragOver}
                  onFileDragLeave={sources.handleFileDragLeave}
                  onToggleRecording={sources.handleToggleRecording}
                  onCloseRecordingPanel={sources.handleCloseRecordingPanel}
                  rawUploadUrl={sources.rawUploadUrl}
                />
              </div>
              <SourceListPanel
                rawSources={sources.rawSources}
                includedSources={sources.includedSources}
                isLoadingSources={sources.isLoadingSources}
                tagFilter={tagFilter}
                onToggleTagFilter={handleToggleTagFilter}
                onSetSourceIncluded={sources.handleSetSourceIncluded}
                onDeleteSource={sources.handleDeleteSource}
                onRenameSource={sources.handleRenameSource}
                onRetryProcessing={sources.handleRetryProcessing}
              />
            </>
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
        )}

        <div className="flex-1 flex flex-col min-w-0 min-h-0 relative">
          {chats.activeChatId !== null && chats.activeChat && (
            <ChatTopBar
              activeChat={chats.activeChat}
              activeChatSourceId={chats.activeChatSourceId}
              isRenamingTitle={chats.renamingChatId === chats.activeChat.id}
              titleDraft={chats.renameDraft}
              setTitleDraft={chats.setRenameDraft}
              onStartRenameTitle={chats.handleStartRenameActiveChat}
              onCommitRenameTitle={() => void chats.handleCommitRename(chats.activeChat!.id)}
              onCancelRenameTitle={() => chats.setRenamingChatId(null)}
            />
          )}
          <ReflectionBanner
            active={chats.gibbsActive}
            step={chats.gibbsStep}
            generating={chats.gibbsGenerating}
            onStart={() => void chats.startReflection()}
            onAdvance={() => void chats.advanceGibbsStep()}
            onClarify={() => void chats.askClarifying()}
            onEnd={chats.exitReflection}
            onSelectStep={(step) => void chats.handleSelectGibbsStep(step)}
          />
          <ChatMessages
            activeChatMessages={chats.activeChatMessages}
            isLoadingActiveChat={chats.isLoadingActiveChat}
            streamingAssistant={chats.streamingAssistant}
          />
          <ChatInput
            inputValue={chats.inputValue}
            setInputValue={chats.setInputValue}
            onSubmitText={chats.handleSubmitText}
            isAssistantThinking={chats.isAssistantThinking}
            activeChatId={chats.activeChatId}
            activeChatSourceId={chats.activeChatSourceId}
            activeChatLinkedSourceStatus={chats.activeChatLinkedSourceStatus}
            isLinkedSourceProcessing={chats.isLinkedSourceProcessing}
            isPromotingChat={chats.isPromotingChat}
            activeChatMessages={chats.activeChatMessages}
            onPromoteChat={chats.handlePromoteChat}
            includedSourcesCount={sources.includedSources.length}
            chatModel={appSettings?.chat_model ?? null}
            installedModels={installedModels}
            isOllamaReachable={isOllamaReachable}
            isSavingChatModel={isSavingChatModel}
            onChangeChatModel={handleChangeChatModel}
          />

          {stage !== "chat" && (
            <div className="absolute inset-0 z-10 bg-background flex flex-col">
              {stage === "note" ? (
                <NoteEditor
                  onClose={() => setStage("chat")}
                  onSave={sources.handleSaveNote}
                  isSaving={sources.isSavingSource}
                />
              ) : (
                <>
                  <StageHeader
                    title="Graph"
                    icon={<Sparkles className="h-3.5 w-3.5 text-emerald-600" />}
                    onClose={() => setStage("chat")}
                  />
                  <GraphStage mode="fullscreen" />
                </>
              )}
            </div>
          )}
        </div>

        {sidebar.isRightCollapsed ? (
          <div className="border-l flex flex-col items-center bg-muted/10 shrink-0 min-h-0 w-12 py-2 gap-1.5">
            <button
              onClick={sidebar.toggleRightCollapsed}
              aria-label="Show tools panel"
              title="Show panel"
              className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors"
            >
              <PanelRightOpen className="h-4 w-4" />
            </button>
            <div className="my-1 h-px w-6 bg-border" />
            <button
              onClick={exportToMarkdown}
              disabled={!hasIncludedSources}
              aria-label="Export to Markdown"
              title="Export to Markdown"
              className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <FileText className="h-4 w-4" />
            </button>
            <button
              onClick={() => void handleAISearch()}
              disabled={!hasIncludedSources || isRunningSearch}
              aria-label="Ask about your sources"
              title="Ask about your sources"
              className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <MessageCircle className="h-4 w-4" />
            </button>
            <button
              onClick={() => setStage("graph")}
              aria-label="Open Graph View"
              title="Open Graph View"
              className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <Sparkles className="h-4 w-4" />
            </button>
          </div>
        ) : (
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
            onCollapse={sidebar.toggleRightCollapsed}
            onOpenGraph={() => setStage("graph")}
          />
        </aside>
        )}
      </div>
    </div>
  )
}
