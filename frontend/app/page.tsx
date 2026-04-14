"use client"

import { useEffect, useMemo, useState } from "react"
import { Plus, FileText, Mic, FileUp, Type, Sparkles, MessageCircle, Send, Play, Pause, X, File } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { GraphView } from "@/components/graph-view"
import { OnboardingModal, type OnboardingProfile } from "@/components/onboarding-modal"
import { TopNav } from "@/components/top-nav"
import { api, type SourceRecord } from "@/lib/api"

interface RawSource {
  id: string
  type: "recording" | "file" | "text"
  name: string
  content?: string
  duration?: string
  timestamp: string
  included: boolean
  tags: { name: string; color: string }[]
}

interface ChatEntry {
  id: string
  type: "reflection" | "scale" | "freeform"
  question?: string
  answer: string
  scaleValue?: number
  timestamp: string
  tags: { name: string; color: string }[]
}

type QuestionType = "clarifying" | "guided" | "quantitative"
type AddSourceMode = null | "recording" | "file" | "text"

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

const profileStorageKey = "reflect_profile"

const mapSourceType = (source: SourceRecord): RawSource["type"] => {
  const fileType = (source.file_type ?? "").toLowerCase()
  if (fileType.includes("audio")) return "recording"
  if (fileType.includes("text") || !source.filename) return "text"
  return "file"
}

const mapBackendSource = (source: SourceRecord): RawSource => ({
  id: String(source.id),
  type: mapSourceType(source),
  name: source.filename || "Quick thought",
  content: source.text ?? undefined,
  timestamp: new Date(source.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  included: true,
  tags: [],
})

export default function HomePage() {
  const [rawSources, setRawSources] = useState<RawSource[]>([])
  const [chatEntries, setChatEntries] = useState<ChatEntry[]>([])
  const [currentQuestion, setCurrentQuestion] = useState<{ type: QuestionType; content: string; scaleData?: { lowLabel: string; highLabel: string } } | null>(null)
  const [inputValue, setInputValue] = useState("")
  const [rightPanel, setRightPanel] = useState<"tools" | "graph">("tools")
  const [addSourceMode, setAddSourceMode] = useState<AddSourceMode>(null)
  const [newSourceText, setNewSourceText] = useState("")
  const [isRecording, setIsRecording] = useState(false)
  const [toolsNotice, setToolsNotice] = useState<string | null>(null)
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false)
  const [isLoadingSources, setIsLoadingSources] = useState(true)
  const [isSavingSource, setIsSavingSource] = useState(false)
  const [isRunningSearch, setIsRunningSearch] = useState(false)
  const [isGeneratingQuestion, setIsGeneratingQuestion] = useState(false)

  useEffect(() => {
    const loadSources = async () => {
      setIsLoadingSources(true)
      try {
        const sources = await api.getSources()
        const mapped = sources.map(mapBackendSource).sort((a, b) => a.id.localeCompare(b.id))
        setRawSources(mapped)

        const hasProfile = Boolean(window.localStorage.getItem(profileStorageKey))
        setIsOnboardingOpen(!hasProfile && mapped.length === 0)
      } catch (error) {
        setToolsNotice(`Could not load sources from backend: ${error instanceof Error ? error.message : "Unknown error"}`)
      } finally {
        setIsLoadingSources(false)
      }
    }

    void loadSources()
  }, [])

  const includedSources = useMemo(() => rawSources.filter((source) => source.included), [rawSources])
  const hasIncludedSources = includedSources.length > 0

  const pickFallbackQuestion = (type: QuestionType) => {
    if (type === "guided") {
      return guidedQuestions[Math.floor(Math.random() * guidedQuestions.length)]
    }
    return clarifyingQuestions[Math.floor(Math.random() * clarifyingQuestions.length)]
  }

  const handleSelectQuestionType = async (type: QuestionType) => {
    let question: string
    let scaleData: { lowLabel: string; highLabel: string } | undefined

    if (type === "quantitative") {
      const random = quantitativeQuestions[Math.floor(Math.random() * quantitativeQuestions.length)]
      question = random.question
      scaleData = { lowLabel: random.lowLabel, highLabel: random.highLabel }
    } else {
      setIsGeneratingQuestion(true)
      try {
        const mode = type === "guided" ? "deep_dive" : "clarifying"
        question = await new Promise<string>((resolve, reject) => {
          let generated = ""
          api.streamGeneratedQuestion(
            { mode },
            {
              onToken(token) {
                generated += token
              },
              onDone() {
                resolve(generated.trim())
              },
              onError(error) {
                reject(error)
              },
            }
          )
        })

        if (!question) {
          question = pickFallbackQuestion(type)
          setToolsNotice("Question generator returned no content, so a local prompt was used.")
        }
      } catch (error) {
        question = pickFallbackQuestion(type)
        setToolsNotice(
          `Question generation is unavailable (${error instanceof Error ? error.message : "Unknown error"}). Using a local prompt.`
        )
      } finally {
        setIsGeneratingQuestion(false)
      }
    }

    setCurrentQuestion({ type, content: question, scaleData })
  }

  const handleScaleSelect = (value: number) => {
    const newEntry: ChatEntry = {
      id: String(Date.now()),
      type: "scale",
      question: currentQuestion?.content,
      answer: `${value}/10`,
      scaleValue: value,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      tags: [],
    }
    setChatEntries((prev) => [...prev, newEntry])
    setCurrentQuestion(null)
  }

  const handleSubmitText = (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim()) return

    const newEntry: ChatEntry = {
      id: String(Date.now()),
      type: currentQuestion?.type === "guided" ? "reflection" : "freeform",
      question: currentQuestion?.content,
      answer: inputValue,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      tags: [],
    }
    setChatEntries((prev) => [...prev, newEntry])
    setInputValue("")
    setCurrentQuestion(null)
  }

  const handleSetSourceIncluded = (sourceId: string, included: boolean) => {
    setRawSources((prev) =>
      prev.map((source) => (source.id === sourceId ? { ...source, included } : source))
    )
  }

  const handleAddTextSource = async () => {
    if (!newSourceText.trim()) return
    setIsSavingSource(true)
    try {
      const created = await api.uploadTextSource(newSourceText)
      setRawSources((prev) => [mapBackendSource(created), ...prev])
      setNewSourceText("")
      setAddSourceMode(null)
      setToolsNotice("Source added and saved to backend.")
    } catch (error) {
      setToolsNotice(`Could not save source: ${error instanceof Error ? error.message : "Unknown error"}`)
    } finally {
      setIsSavingSource(false)
    }
  }

  const handleToggleRecording = () => {
    if (isRecording) {
      setIsRecording(false)
      setAddSourceMode(null)
      setToolsNotice("Recording UI is present; connect microphone capture to upload audio next.")
      return
    }

    setIsRecording(true)
  }

  const exportToMarkdown = () => {
    if (!hasIncludedSources) {
      setToolsNotice("Select at least one included source before exporting.")
      return
    }

    let markdown = `# Reflection\n\n`
    markdown += `## Sources\n\n`

    includedSources.forEach((source) => {
      if (source.type === "recording") {
        markdown += `- Voice note (${source.duration}) - ${source.timestamp}\n`
      } else if (source.type === "text") {
        markdown += `- ${source.content} - ${source.timestamp}\n`
      } else {
        markdown += `- File: ${source.name} - ${source.timestamp}\n`
      }
    })

    markdown += `\n## Reflections\n\n`

    chatEntries.forEach((entry) => {
      if (entry.question) {
        markdown += `**Q:** ${entry.question}\n\n`
      }
      markdown += `**A:** ${entry.answer}\n\n`
      markdown += `*${entry.timestamp}*\n\n---\n\n`
    })

    const blob = new Blob([markdown], { type: "text/markdown" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "reflection.md"
    a.click()
    URL.revokeObjectURL(url)
    setToolsNotice(`Exported ${includedSources.length} included source${includedSources.length === 1 ? "" : "s"}.`)
  }

  const handleAISearch = async () => {
    if (!hasIncludedSources) {
      setToolsNotice("Select at least one included source before using AI Search.")
      return
    }

    setIsRunningSearch(true)
    try {
      const context = includedSources
        .map((source) => source.content)
        .filter(Boolean)
        .join("\n")
        .slice(0, 2000)
      const answer = await api.query(
        `Summarize the key themes in these selected sources and keep it concise:\n${context || "No text available."}`
      )
      setToolsNotice(answer.answer)
    } catch (error) {
      setToolsNotice(`AI Search failed: ${error instanceof Error ? error.message : "Unknown error"}`)
    } finally {
      setIsRunningSearch(false)
    }
  }

  const handleOnboardingSkip = () => {
    setIsOnboardingOpen(false)
  }

  const handleOnboardingSubmit = (nextProfile: OnboardingProfile) => {
    window.localStorage.setItem(profileStorageKey, JSON.stringify(nextProfile))
    setIsOnboardingOpen(false)
    setToolsNotice(`Welcome ${nextProfile.name}, your onboarding profile is saved locally.`)
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <OnboardingModal
        open={isOnboardingOpen}
        onSkip={handleOnboardingSkip}
        onSubmit={handleOnboardingSubmit}
      />
      <TopNav activePath="/" />

      <div className="flex-1 flex">
        <aside className="w-64 border-r flex flex-col bg-muted/10">
          <div className="p-4 border-b">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium">Sources</h2>
              <span className="text-xs text-muted-foreground">{includedSources.length}/{rawSources.length}</span>
            </div>
            {isLoadingSources && (
              <p className="text-xs text-muted-foreground mb-2">Loading sources from backend...</p>
            )}

            {!addSourceMode ? (
              <div className="grid grid-cols-3 gap-1.5">
                <button
                  onClick={() => setAddSourceMode("recording")}
                  className="flex flex-col items-center gap-1 p-2 rounded-lg border border-dashed border-border hover:border-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors"
                >
                  <Mic className="h-4 w-4 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground">Record</span>
                </button>
                <button
                  onClick={() => setAddSourceMode("file")}
                  className="flex flex-col items-center gap-1 p-2 rounded-lg border border-dashed border-border hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                >
                  <FileUp className="h-4 w-4 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground">File</span>
                </button>
                <button
                  onClick={() => setAddSourceMode("text")}
                  className="flex flex-col items-center gap-1 p-2 rounded-lg border border-dashed border-border hover:border-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors"
                >
                  <Type className="h-4 w-4 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground">Text</span>
                </button>
              </div>
            ) : addSourceMode === "recording" ? (
              <div className="p-3 rounded-lg border bg-background space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium">Voice recording</span>
                  <button onClick={() => { setAddSourceMode(null); setIsRecording(false) }} className="p-1 rounded hover:bg-muted">
                    <X className="h-3 w-3" />
                  </button>
                </div>
                <div className="flex items-center justify-center gap-3">
                  <button
                    onClick={handleToggleRecording}
                    className={`p-3 rounded-full transition-colors ${isRecording
                      ? "bg-red-500 text-white animate-pulse"
                      : "bg-emerald-500 text-white hover:bg-emerald-600"
                      }`}
                  >
                    {isRecording ? <Pause className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                  </button>
                </div>
                {isRecording && (
                  <p className="text-xs text-center text-muted-foreground">Recording... Tap to stop</p>
                )}
              </div>
            ) : addSourceMode === "text" ? (
              <div className="p-3 rounded-lg border bg-background space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium">Quick thought</span>
                  <button onClick={() => setAddSourceMode(null)} className="p-1 rounded hover:bg-muted">
                    <X className="h-3 w-3" />
                  </button>
                </div>
                <textarea
                  value={newSourceText}
                  onChange={(e) => setNewSourceText(e.target.value)}
                  placeholder="Write a thought..."
                  className="w-full p-2 text-sm rounded border bg-background resize-none focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  rows={3}
                />
                <Button
                  onClick={handleAddTextSource}
                  disabled={!newSourceText.trim() || isSavingSource}
                  size="sm"
                  className="w-full bg-emerald-600 hover:bg-emerald-700"
                >
                  {isSavingSource ? "Saving..." : "Add"}
                </Button>
              </div>
            ) : (
              <div className="p-3 rounded-lg border bg-background space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium">Upload file</span>
                  <button onClick={() => setAddSourceMode(null)} className="p-1 rounded hover:bg-muted">
                    <X className="h-3 w-3" />
                  </button>
                </div>
                <div className="border-2 border-dashed rounded-lg p-4 text-center space-y-2">
                  <FileUp className="h-6 w-6 mx-auto text-muted-foreground mb-2" />
                  <p className="text-xs text-muted-foreground">Choose a .wav, .mp3, .txt, or .md file</p>
                  <input
                    type="file"
                    className="text-xs"
                    accept=".wav,.mp3,.m4a,.txt,.md"
                    onChange={async (event) => {
                      const selectedFile = event.target.files?.[0]
                      if (!selectedFile) return
                      setIsSavingSource(true)
                      try {
                        const created = await api.uploadFileSource(selectedFile)
                        setRawSources((prev) => [mapBackendSource(created), ...prev])
                        setAddSourceMode(null)
                        setToolsNotice(`Uploaded ${selectedFile.name}`)
                      } catch (error) {
                        setToolsNotice(`Upload failed: ${error instanceof Error ? error.message : "Unknown error"}`)
                      } finally {
                        setIsSavingSource(false)
                      }
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {rawSources.map((source) => (
              <div
                key={source.id}
                className={`p-2.5 rounded-lg hover:bg-muted/50 transition-colors group ${source.included ? "" : "opacity-60"}`}
              >
                <div className="flex items-start gap-2.5">
                  <div className={`p-1.5 rounded-md ${source.type === "recording" ? "bg-emerald-100 dark:bg-emerald-900/30" :
                    source.type === "file" ? "bg-blue-100 dark:bg-blue-900/30" :
                      "bg-amber-100 dark:bg-amber-900/30"
                    }`}>
                    {source.type === "recording" ? (
                      <Mic className="h-3 w-3 text-emerald-600" />
                    ) : source.type === "file" ? (
                      <File className="h-3 w-3 text-blue-600" />
                    ) : (
                      <Type className="h-3 w-3 text-amber-600" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">{source.name}</span>
                    </div>
                    {source.type === "recording" && (
                      <div className="flex items-center gap-2 mt-0.5">
                        <Play className="h-3 w-3 text-muted-foreground" />
                        <span className="text-xs text-muted-foreground">{source.duration}</span>
                      </div>
                    )}
                    {source.type === "text" && source.content && (
                      <p className="text-xs text-muted-foreground truncate mt-0.5">{source.content}</p>
                    )}
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] text-muted-foreground">{source.timestamp}</span>
                      {source.tags.map((tag) => (
                        <span
                          key={tag.name}
                          className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted"
                        >
                          {tag.name}
                        </span>
                      ))}
                    </div>
                  </div>
                  <Checkbox
                    checked={source.included}
                    onCheckedChange={(checked) => handleSetSourceIncluded(source.id, checked === true)}
                    aria-label={`Include ${source.name}`}
                    className="self-center"
                  />
                </div>
              </div>
            ))}
          </div>
        </aside>

        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-2xl mx-auto space-y-4">
              {chatEntries.map((entry) => (
                <div key={entry.id} className="space-y-2">
                  {entry.question && (
                    <div className="flex justify-start">
                      <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3 max-w-[85%]">
                        <span className="text-xs text-emerald-600 font-medium block mb-1">REFLECT</span>
                        <p className="text-[15px]">{entry.question}</p>
                      </div>
                    </div>
                  )}
                  <div className="flex justify-end">
                    <div className="bg-emerald-900 text-white rounded-2xl rounded-tr-sm px-4 py-3 max-w-[85%]">
                      <p className="text-[15px]">{entry.answer}</p>
                      <div className="flex items-center justify-end gap-2 mt-1.5">
                        {entry.tags.map((tag) => (
                          <span
                            key={tag.name}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-white/20"
                          >
                            {tag.name}
                          </span>
                        ))}
                        <span className="text-[10px] text-white/70">{entry.timestamp}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {currentQuestion?.type === "quantitative" && currentQuestion.scaleData && (
                <div className="space-y-2">
                  <div className="flex justify-start">
                    <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3">
                      <span className="text-xs text-emerald-600 font-medium block mb-1">REFLECT</span>
                      <p className="text-[15px]">{currentQuestion.content}</p>
                    </div>
                  </div>
                  <div className="bg-muted/50 rounded-xl p-5 space-y-3">
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>{currentQuestion.scaleData.lowLabel}</span>
                      <span>{currentQuestion.scaleData.highLabel}</span>
                    </div>
                    <div className="flex justify-between gap-2">
                      {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((value) => (
                        <button
                          key={value}
                          onClick={() => handleScaleSelect(value)}
                          className="flex-1 aspect-square rounded-lg border-2 border-border hover:border-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors flex items-center justify-center font-medium"
                        >
                          {value}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {currentQuestion && currentQuestion.type !== "quantitative" && (
                <div className="space-y-2">
                  <div className="flex justify-start">
                    <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3">
                      <span className="text-xs text-emerald-600 font-medium block mb-1">REFLECT</span>
                      <p className="text-[15px]">{currentQuestion.content}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="border-t bg-background p-4">
            <div className="max-w-2xl mx-auto">
              {currentQuestion && currentQuestion.type !== "quantitative" && (
                <form onSubmit={handleSubmitText} className="flex gap-2 mb-4">
                  <div className="flex-1 relative">
                    <textarea
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      placeholder="Write your response..."
                      className="w-full min-h-[60px] p-3 pr-10 rounded-xl border bg-background resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                      rows={2}
                    />
                    <button type="button" className="absolute bottom-2 right-2 p-1.5 rounded-lg hover:bg-muted text-muted-foreground">
                      <Mic className="h-4 w-4" />
                    </button>
                  </div>
                  <Button type="submit" disabled={!inputValue.trim()} className="bg-emerald-600 hover:bg-emerald-700 text-white self-end">
                    <Send className="h-4 w-4" />
                  </Button>
                </form>
              )}

              {!currentQuestion && (
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground text-center">What would you like to add?</p>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      onClick={() => void handleSelectQuestionType("clarifying")}
                      disabled={isGeneratingQuestion}
                      className="p-3 rounded-xl border-2 border-border hover:border-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors text-left"
                    >
                      <MessageCircle className="h-4 w-4 text-amber-600 mb-2" />
                      <div className="text-sm font-medium">Clarifying</div>
                      <div className="text-xs text-muted-foreground">
                        {isGeneratingQuestion ? "Generating..." : "Follow-up questions"}
                      </div>
                    </button>
                    <button
                      onClick={() => void handleSelectQuestionType("guided")}
                      disabled={isGeneratingQuestion}
                      className="p-3 rounded-xl border-2 border-border hover:border-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors text-left"
                    >
                      <Sparkles className="h-4 w-4 text-emerald-600 mb-2" />
                      <div className="text-sm font-medium">Guided</div>
                      <div className="text-xs text-muted-foreground">
                        {isGeneratingQuestion ? "Generating..." : "Reflective prompts"}
                      </div>
                    </button>
                    <button
                      onClick={() => void handleSelectQuestionType("quantitative")}
                      disabled={isGeneratingQuestion}
                      className="p-3 rounded-xl border-2 border-border hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors text-left"
                    >
                      <span className="text-blue-600 font-bold text-xs block mb-2">1-10</span>
                      <div className="text-sm font-medium">Quantitative</div>
                      <div className="text-xs text-muted-foreground">Rate how you feel</div>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <aside className="w-64 border-l flex flex-col bg-muted/10">
          <div className="flex border-b">
            <button
              onClick={() => setRightPanel("tools")}
              className={`flex-1 py-3 text-sm font-medium transition-colors ${rightPanel === "tools" ? "border-b-2 border-emerald-500 text-foreground" : "text-muted-foreground"
                }`}
            >
              Tools
            </button>
            <button
              onClick={() => setRightPanel("graph")}
              className={`flex-1 py-3 text-sm font-medium transition-colors ${rightPanel === "graph" ? "border-b-2 border-emerald-500 text-foreground" : "text-muted-foreground"
                }`}
            >
              Graph
            </button>
          </div>

          {rightPanel === "tools" ? (
            <div className="p-4 space-y-4">
              <div>
                <h3 className="text-sm font-medium mb-3">Export</h3>
                <button
                  onClick={exportToMarkdown}
                  disabled={!hasIncludedSources}
                  className="w-full flex items-center gap-3 p-3 rounded-lg border hover:bg-muted transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <div className="text-sm font-medium">Export to Markdown</div>
                    <div className="text-xs text-muted-foreground">Download included sources</div>
                  </div>
                </button>
              </div>

              <div>
                <h3 className="text-sm font-medium mb-3">Tags</h3>
                <div className="flex flex-wrap gap-1.5">
                  {["work", "stress", "sleep"].map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-muted hover:bg-muted/80 cursor-pointer"
                    >
                      {tag}
                    </span>
                  ))}
                  <button className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs text-muted-foreground hover:bg-muted">
                    <Plus className="h-3 w-3" />
                    Add
                  </button>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-medium mb-3">AI Search</h3>
                <button
                  onClick={handleAISearch}
                  disabled={!hasIncludedSources || isRunningSearch}
                  className="w-full flex items-center gap-3 p-3 rounded-lg border hover:bg-muted transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <MessageCircle className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <div className="text-sm font-medium">{isRunningSearch ? "Searching..." : "Ask about your sources"}</div>
                    <div className="text-xs text-muted-foreground">Search included sources only</div>
                  </div>
                </button>
              </div>

              {toolsNotice && (
                <p className="text-xs text-muted-foreground rounded-lg border p-2 bg-background">
                  {toolsNotice}
                </p>
              )}
            </div>
          ) : (
            <div className="flex-1 p-4">
              <p className="text-xs text-muted-foreground mb-3">Connections in included sources</p>
              <GraphView sources={includedSources} />
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
