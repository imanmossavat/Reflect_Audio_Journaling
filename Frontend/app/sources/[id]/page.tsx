"use client"

import React, { useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { AlertTriangle, ArrowLeft, CalendarClock, CircleDot, FileAudio2, FileText, MessageSquare, Pencil, RefreshCw, X } from "lucide-react"
import { Input } from "@/components/ui/input"
import { TopNav } from "@/components/top-nav"
import { toast } from "sonner"
import { api, type ChatMessageRecord, type SourceRecord, type SourceTag, type TranscriptSegment, PROCESSING_STATUSES, PROCESSING_STATUS_LABELS, OLLAMA_FAILURE_STATUSES, explainFailure } from "@/lib/api"

const getSourceKind = (source: SourceRecord) => {
    const fileType = (source.file_type ?? "").toLowerCase()
    if (fileType === "chat") return "Chat"
    if (fileType.includes("audio")) return "Audio"
    if (fileType.includes("text") || !source.filename) return "Text"
    return "File"
}

const getStatusClassName = (status: string) => {
    const normalized = status.toLowerCase()
    if (normalized === "processed") {
        return "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/50 dark:bg-emerald-900/20 dark:text-emerald-300"
    }
    return "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-300"
}

// Backend serializes naive UTC datetimes without a timezone marker; force UTC interpretation.
const parseBackendDate = (s: string) => new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(s) ? s : `${s}Z`)

const markdownClasses = [
    "mt-4 cursor-text min-h-[60px] text-sm leading-7 text-foreground",
    "[&_h1]:text-2xl [&_h1]:font-bold [&_h1]:mb-2",
    "[&_h2]:text-xl [&_h2]:font-semibold [&_h2]:mb-1",
    "[&_p]:mb-3 [&_strong]:font-bold [&_em]:italic",
    "[&_ul]:list-disc [&_ul]:pl-5 [&_ul]:mb-3",
    "[&_ol]:list-decimal [&_ol]:pl-5 [&_ol]:mb-3",
    "[&_code]:font-mono [&_code]:bg-muted [&_code]:px-1 [&_code]:rounded",
    "[&_blockquote]:border-l-4 [&_blockquote]:pl-4 [&_blockquote]:text-muted-foreground",
    "[&_a]:text-emerald-600 [&_a]:underline",
].join(" ")

export default function SourceDetailPage() {
    const params = useParams<{ id: string }>()
    const [source, setSource] = useState<SourceRecord | null>(null)
    const [sourceText, setSourceText] = useState("")
    const [sourceTags, setSourceTags] = useState<SourceTag[]>([])
    const [newTagName, setNewTagName] = useState("")
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [isAddingTag, setIsAddingTag] = useState(false)
    const [tagIdsBeingRemoved, setTagIdsBeingRemoved] = useState<number[]>([])
    const [chatMessages, setChatMessages] = useState<ChatMessageRecord[] | null>(null)
    const [currentTime, setCurrentTime] = useState(0)
    const [titleValue, setTitleValue] = useState("")
    const [editingDate, setEditingDate] = useState(false)
    const [editingTranscript, setEditingTranscript] = useState(false)
    const [isRetrying, setIsRetrying] = useState(false)

    const audioRef = useRef<HTMLAudioElement>(null)
    const activeSegmentRef = useRef<HTMLSpanElement>(null)
    const titleSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const transcriptSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const isEditingTranscriptRef = useRef(false)
    const textareaRef = useRef<HTMLTextAreaElement>(null)

    const sourceId = useMemo(() => {
        const parsed = Number(params.id)
        if (!Number.isInteger(parsed) || parsed <= 0) {
            return null
        }
        return parsed
    }, [params.id])

    useEffect(() => {
        const loadSource = async () => {
            if (sourceId === null) {
                setError("Invalid source id.")
                setIsLoading(false)
                setSourceTags([])
                return
            }

            setIsLoading(true)
            setError(null)
            setSourceTags([])
            setNewTagName("")
            setTagIdsBeingRemoved([])
            setChatMessages(null)

            try {
                const loadedSource = await api.getSourceById(sourceId)
                setSource(loadedSource)
                setTitleValue(loadedSource.filename || "")

                const textPromise = loadedSource.text ? Promise.resolve(loadedSource.text) : api.getSourceText(sourceId)
                const [fullText, loadedTags] = await Promise.all([textPromise, api.getSourceTags(sourceId)])
                setSourceText(fullText ?? "")
                setSourceTags(loadedTags)

                if (loadedSource.file_type === "chat") {
                    const chats = await api.listChats()
                    const linked = chats.find(c => c.source_id === sourceId)
                    if (linked) {
                        const detail = await api.getChat(linked.id)
                        setChatMessages(detail.messages)
                    }
                }
            } catch (loadError) {
                setError(loadError instanceof Error ? loadError.message : "Unknown error")
            } finally {
                setIsLoading(false)
            }
        }

        void loadSource()
    }, [sourceId])

    // Poll while source is being processed in background
    useEffect(() => {
        if (!source || !PROCESSING_STATUSES.has(source.status)) return

        const interval = setInterval(async () => {
            try {
                const updated = await api.getSourceById(source.id)
                setSource(updated)
                if (updated.text && updated.text !== sourceText && !isEditingTranscriptRef.current) {
                    setSourceText(updated.text)
                }
                if (!PROCESSING_STATUSES.has(updated.status)) {
                    clearInterval(interval)
                }
            } catch {
                // ignore transient errors
            }
        }, 2500)

        return () => clearInterval(interval)
    }, [source?.status, source?.id])

    // Auto-resize textarea when editing opens
    useEffect(() => {
        if (editingTranscript && textareaRef.current) {
            const el = textareaRef.current
            el.style.height = "auto"
            el.style.height = `${el.scrollHeight}px`
        }
    }, [editingTranscript])

    const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value
        setTitleValue(val)
        if (titleSaveTimerRef.current) clearTimeout(titleSaveTimerRef.current)
        const id = source?.id
        if (!id) return
        titleSaveTimerRef.current = setTimeout(async () => {
            const trimmed = val.trim()
            if (!trimmed) return
            try {
                const updated = await api.patchSource(id, { filename: trimmed })
                setSource(updated)
            } catch (err) {
                toast.error(`Could not save title: ${err instanceof Error ? err.message : "Unknown error"}`)
            }
        }, 700)
    }

    const handleTranscriptChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const val = e.target.value
        setSourceText(val)
        e.target.style.height = "auto"
        e.target.style.height = `${e.target.scrollHeight}px`
        if (transcriptSaveTimerRef.current) clearTimeout(transcriptSaveTimerRef.current)
        const id = source?.id
        if (!id) return
        transcriptSaveTimerRef.current = setTimeout(async () => {
            try {
                const updated = await api.patchSource(id, { text: val })
                setSource(updated)
                if (updated.status === "not processed") {
                    const queued = await api.processSource(id)
                    setSource(queued)
                }
            } catch (err) {
                toast.error(`Could not save transcript: ${err instanceof Error ? err.message : "Unknown error"}`)
            }
        }, 800)
    }

    const handleTranscriptBlur = async (e: React.FocusEvent<HTMLTextAreaElement>) => {
        const currentText = e.target.value
        isEditingTranscriptRef.current = false
        if (transcriptSaveTimerRef.current) {
            clearTimeout(transcriptSaveTimerRef.current)
            transcriptSaveTimerRef.current = null
        }
        setEditingTranscript(false)
        setSourceText(currentText)
        if (!source) return
        try {
            const updated = await api.patchSource(source.id, { text: currentText })
            setSource(updated)
            if (updated.status === "not processed") {
                const queued = await api.processSource(source.id)
                setSource(queued)
            }
        } catch (err) {
            toast.error(`Could not save transcript: ${err instanceof Error ? err.message : "Unknown error"}`)
        }
    }

    const startEditingTranscript = () => {
        isEditingTranscriptRef.current = true
        setEditingTranscript(true)
    }

    const handleAddTag = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault()
        if (!source || sourceId === null || isAddingTag) return

        const normalizedName = newTagName.trim().toLowerCase()
        if (!normalizedName) return

        if (sourceTags.some((tag) => tag.name.toLowerCase() === normalizedName)) {
            return
        }

        setIsAddingTag(true)
        try {
            const addedTag = await api.addTagToSource(sourceId, normalizedName)
            setSourceTags((currentTags) => {
                if (currentTags.some((tag) => tag.id === addedTag.id)) {
                    return currentTags
                }
                return [...currentTags, addedTag]
            })
            setNewTagName("")
        } catch (addTagError) {
            toast.error("Could not add tag", { description: addTagError instanceof Error ? addTagError.message : "Unknown error" })
        } finally {
            setIsAddingTag(false)
        }
    }

    const handleRemoveTag = async (tag: SourceTag) => {
        if (sourceId === null) return
        if (tagIdsBeingRemoved.includes(tag.id)) return

        setTagIdsBeingRemoved((currentIds) => [...currentIds, tag.id])
        try {
            await api.removeTagFromSource(sourceId, tag.id)
            setSourceTags((currentTags) => currentTags.filter((currentTag) => currentTag.id !== tag.id))
        } catch (removeTagError) {
            toast.error("Could not remove tag", { description: removeTagError instanceof Error ? removeTagError.message : "Unknown error" })
        } finally {
            setTagIdsBeingRemoved((currentIds) => currentIds.filter((id) => id !== tag.id))
        }
    }

    const handleSaveDate = async (isoValue: string) => {
        if (!source || !isoValue) { setEditingDate(false); return }
        try {
            const [datePart, timePart] = isoValue.split("T")
            const [year, month, day] = datePart.split("-").map(Number)
            const [hour, minute] = timePart.split(":").map(Number)
            const localDate = new Date(year, month - 1, day, hour, minute)
            const updated = await api.patchSource(source.id, { created_at: localDate.toISOString() })
            setSource(updated)
        } catch (err) {
            toast.error(`Could not save date: ${err instanceof Error ? err.message : "Unknown error"}`)
        } finally {
            setEditingDate(false)
        }
    }

    const segments: TranscriptSegment[] | null = source?.transcript_segments ?? null
    const isAudio = source?.file_type?.toLowerCase().includes("audio") ?? false
    const isChat = source?.file_type?.toLowerCase() === "chat"

    const activeSegmentIndex = useMemo(() => {
        if (!segments) return -1
        for (let i = 0; i < segments.length; i++) {
            const seg = segments[i]
            const start = seg.start_s ?? 0
            const end = seg.end_s ?? Infinity
            if (currentTime >= start && currentTime < end) return i
        }
        return -1
    }, [segments, currentTime])

    useEffect(() => {
        activeSegmentRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" })
    }, [activeSegmentIndex])

    const handleRetry = async () => {
        if (!source || isRetrying) return
        setIsRetrying(true)
        try {
            const updated = await api.processSource(source.id)
            setSource(updated)
        } catch (err) {
            toast.error(`Could not retry: ${err instanceof Error ? err.message : "Unknown error"}`)
        } finally {
            setIsRetrying(false)
        }
    }

    const isSourceInProgress = source ? PROCESSING_STATUSES.has(source.status) : false
    const failureInfo = source ? explainFailure(source.status) : null
    const isOllamaFailure = source ? OLLAMA_FAILURE_STATUSES.has(source.status) : false
    const normalizedNewTag = newTagName.trim().toLowerCase()
    const isDuplicateNewTag = normalizedNewTag.length > 0 && sourceTags.some((tag) => tag.name.toLowerCase() === normalizedNewTag)
    const sourceKind = source ? getSourceKind(source) : "File"

    const transcriptEditSection = editingTranscript ? (
        <textarea
            ref={textareaRef}
            autoFocus
            value={sourceText}
            onChange={handleTranscriptChange}
            onBlur={(e) => void handleTranscriptBlur(e)}
            className="mt-4 w-full min-h-[60px] overflow-hidden resize-none text-sm leading-7 text-foreground bg-transparent border-none focus:outline-none p-0 m-0 font-sans"
        />
    ) : sourceText.trim() ? (
        <div onClick={startEditingTranscript} className={markdownClasses}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{sourceText}</ReactMarkdown>
        </div>
    ) : (
        <p
            onClick={startEditingTranscript}
            className="mt-4 text-sm text-muted-foreground italic cursor-text min-h-[60px] leading-7"
        >
            Click to start writing...
        </p>
    )

    return (
        <div className="min-h-screen bg-background">
            <TopNav activePath="/" />

            <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
                <Link
                    href="/"
                    className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                    <ArrowLeft className="h-4 w-4" />
                    Back to sources
                </Link>

                <section className="mt-4 rounded-2xl border bg-card p-5 shadow-sm sm:p-6">
                    {isLoading ? (
                        <p className="text-sm text-muted-foreground">Loading source...</p>
                    ) : error || !source ? (
                        <p className="text-sm text-red-600">Could not load source: {error ?? "Not found"}</p>
                    ) : (
                        <div className="space-y-6">
                            <div>
                                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600">Source detail</p>
                                <input
                                    value={titleValue}
                                    onChange={handleTitleChange}
                                    placeholder="Untitled"
                                    className="mt-2 w-full text-2xl font-semibold tracking-tight bg-transparent border-b border-transparent hover:border-muted-foreground/20 focus:border-emerald-400 focus:outline-none"
                                />
                                <div className={`mt-3 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${
                                    isSourceInProgress
                                        ? "border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300"
                                        : failureInfo
                                            ? (isOllamaFailure
                                                ? "border-orange-300 bg-orange-50 text-orange-700 dark:border-orange-800 dark:bg-orange-900/30 dark:text-orange-300"
                                                : "border-red-300 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/30 dark:text-red-300")
                                            : getStatusClassName(source.status)
                                }`}>
                                    {isSourceInProgress ? (
                                        <>
                                            <span className="flex gap-0.5">
                                                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce [animation-delay:0ms]" />
                                                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce [animation-delay:150ms]" />
                                                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce [animation-delay:300ms]" />
                                            </span>
                                            {PROCESSING_STATUS_LABELS[source.status] ?? "Processing..."}
                                        </>
                                    ) : failureInfo ? (
                                        <>
                                            <AlertTriangle className="h-3 w-3" />
                                            {PROCESSING_STATUS_LABELS[source.status] ?? "Processing failed"}
                                        </>
                                    ) : (
                                        <>
                                            <CircleDot className="h-3 w-3" />
                                            {source.status}
                                        </>
                                    )}
                                </div>
                            </div>

                            {failureInfo && (
                                <div className={`rounded-xl border p-4 ${
                                    isOllamaFailure
                                        ? "border-orange-200 bg-orange-50/40 dark:border-orange-900/50 dark:bg-orange-900/10"
                                        : "border-red-200 bg-red-50/40 dark:border-red-900/50 dark:bg-red-900/10"
                                }`}>
                                    <div className="flex items-start gap-3">
                                        <AlertTriangle className={`h-5 w-5 mt-0.5 shrink-0 ${isOllamaFailure ? "text-orange-600 dark:text-orange-400" : "text-red-600 dark:text-red-400"}`} />
                                        <div className="flex-1 min-w-0">
                                            <p className={`text-sm font-semibold ${isOllamaFailure ? "text-orange-800 dark:text-orange-200" : "text-red-800 dark:text-red-200"}`}>
                                                {failureInfo.title}
                                            </p>
                                            <p className="mt-1 text-sm text-muted-foreground">
                                                {failureInfo.description}
                                            </p>
                                            {failureInfo.command && (
                                                <pre className="mt-2 inline-block max-w-full overflow-x-auto rounded-md bg-muted px-3 py-1.5 text-xs font-mono">
                                                    {failureInfo.command}
                                                </pre>
                                            )}
                                            <div className="mt-3">
                                                <button
                                                    type="button"
                                                    onClick={() => void handleRetry()}
                                                    disabled={isRetrying}
                                                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors disabled:opacity-50 ${
                                                        isOllamaFailure
                                                            ? "bg-orange-600 hover:bg-orange-700 text-white"
                                                            : "bg-red-600 hover:bg-red-700 text-white"
                                                    }`}
                                                >
                                                    <RefreshCw className={`h-3.5 w-3.5 ${isRetrying ? "animate-spin" : ""}`} />
                                                    {isRetrying ? "Retrying..." : "Retry"}
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
                                <div className="rounded-xl border bg-background p-4 sm:p-5">
                                    {isAudio && source && (
                                        <div className="sticky top-14 z-10 -mx-4 sm:-mx-5 -mt-4 sm:-mt-5 px-4 sm:px-5 pt-4 sm:pt-5 pb-2 bg-background/95 backdrop-blur-sm rounded-t-xl">
                                            <audio
                                                ref={audioRef}
                                                src={api.getSourceAudioUrl(source.id)}
                                                controls
                                                controlsList="nodownload"
                                                onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
                                                className="w-full rounded-lg"
                                            />
                                        </div>
                                    )}

                                    {isChat && chatMessages ? (
                                        <div className="mt-4 space-y-4">
                                            {(() => {
                                                const items: React.ReactNode[] = []
                                                let pendingQuestion: ChatMessageRecord | null = null
                                                for (const message of chatMessages) {
                                                    if (message.role === "question") {
                                                        pendingQuestion = message
                                                        continue
                                                    }
                                                    const answerText =
                                                        message.scale_value !== null && message.scale_value !== undefined
                                                            ? `${message.scale_value}/${message.scale_max ?? 10}`
                                                            : message.text
                                                    items.push(
                                                        <div key={message.id} className="space-y-2">
                                                            {pendingQuestion && (
                                                                <div className="flex justify-start">
                                                                    <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3 max-w-[85%]">
                                                                        <span className="text-xs text-emerald-600 font-medium block mb-1">REFLECT</span>
                                                                        <p className="text-[15px]">{pendingQuestion.text}</p>
                                                                    </div>
                                                                </div>
                                                            )}
                                                            <div className="flex justify-end">
                                                                <div className="bg-emerald-900 text-white rounded-2xl rounded-tr-sm px-4 py-3 max-w-[85%]">
                                                                    <p className="text-[15px] whitespace-pre-wrap">{answerText}</p>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    )
                                                    pendingQuestion = null
                                                }
                                                if (pendingQuestion !== null) {
                                                    const q = pendingQuestion as ChatMessageRecord
                                                    items.push(
                                                        <div key={`pending-${q.id}`} className="flex justify-start">
                                                            <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3 max-w-[85%]">
                                                                <span className="text-xs text-emerald-600 font-medium block mb-1">REFLECT</span>
                                                                <p className="text-[15px]">{q.text}</p>
                                                            </div>
                                                        </div>
                                                    )
                                                }
                                                return items
                                            })()}
                                        </div>
                                    ) : isAudio && segments && segments.length > 0 ? (
                                        <div className="mt-4 space-y-0.5 text-sm leading-7 text-foreground">
                                            {segments.map((seg, i) => (
                                                <span
                                                    key={i}
                                                    ref={i === activeSegmentIndex ? activeSegmentRef : null}
                                                    onClick={() => {
                                                        if (audioRef.current && seg.start_s != null) {
                                                            audioRef.current.currentTime = seg.start_s
                                                            void audioRef.current.play()
                                                        }
                                                    }}
                                                    className={[
                                                        "cursor-pointer rounded px-0.5 transition-colors",
                                                        i === activeSegmentIndex
                                                            ? "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200"
                                                            : "hover:bg-muted/50",
                                                    ].join(" ")}
                                                >
                                                    {seg.text}{" "}
                                                </span>
                                            ))}
                                        </div>
                                    ) : isAudio ? (
                                        sourceText.trim() ? (
                                            <pre className="mt-4 whitespace-pre-wrap wrap-break-word text-sm leading-7 text-foreground">{sourceText}</pre>
                                        ) : (
                                            <p className="mt-4 text-sm text-muted-foreground">No transcript yet.</p>
                                        )
                                    ) : (
                                        transcriptEditSection
                                    )}
                                </div>

                                <aside className="space-y-4">
                                    <div className="rounded-xl border bg-background p-4">
                                        <h2 className="text-sm font-semibold">Details</h2>
                                        <div className="mt-3 space-y-2">
                                            <div className="rounded-lg border bg-muted/20 p-3">
                                                <div className="flex items-center justify-between gap-1">
                                                    <div className="text-xs text-muted-foreground">Date</div>
                                                    <button
                                                        onClick={() => setEditingDate((v) => !v)}
                                                        className="p-0.5 rounded hover:bg-muted text-muted-foreground transition-colors"
                                                        aria-label="Edit date"
                                                    >
                                                        <Pencil className="h-3 w-3" />
                                                    </button>
                                                </div>
                                                {editingDate ? (
                                                    <input
                                                        type="datetime-local"
                                                        autoFocus
                                                        defaultValue={(() => {
                                                            const d = parseBackendDate(source.created_at)
                                                            const pad = (n: number) => String(n).padStart(2, "0")
                                                            return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
                                                        })()}
                                                        onBlur={(e) => void handleSaveDate(e.target.value)}
                                                        className="mt-1 w-full text-sm bg-background border rounded px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                                                    />
                                                ) : (
                                                    <div className="mt-1 flex items-center gap-2 text-sm font-medium">
                                                        <CalendarClock className="h-4 w-4 text-muted-foreground" />
                                                        {parseBackendDate(source.created_at).toLocaleString('en-US', { dateStyle: "medium", timeStyle: "short", hour12: false })}
                                                    </div>
                                                )}
                                            </div>
                                            <div className="rounded-lg border bg-muted/20 p-3">
                                                <div className="text-xs text-muted-foreground">Type</div>
                                                <div className="mt-1 flex items-center gap-2 text-sm font-medium">
                                                    {sourceKind === "Audio" ? (
                                                        <FileAudio2 className="h-4 w-4 text-muted-foreground" />
                                                    ) : sourceKind === "Chat" ? (
                                                        <MessageSquare className="h-4 w-4 text-muted-foreground" />
                                                    ) : (
                                                        <FileText className="h-4 w-4 text-muted-foreground" />
                                                    )}
                                                    {sourceKind}
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="rounded-xl border bg-background p-4">
                                        <div className="flex items-center justify-between gap-2">
                                            <h2 className="text-sm font-semibold">Tags</h2>
                                            <span className="text-xs text-muted-foreground">{sourceTags.length}</span>
                                        </div>

                                        <form
                                            className="mt-3"
                                            onSubmit={(event) => {
                                                void handleAddTag(event)
                                            }}
                                        >
                                            <Input
                                                value={newTagName}
                                                onChange={(event) => setNewTagName(event.target.value)}
                                                placeholder="Type a tag and press Enter"
                                                autoComplete="off"
                                            />
                                        </form>
                                        <p className="mt-2 text-xs text-muted-foreground">
                                            {isAddingTag ? "Adding tag..." : "Press Enter to add a tag."}
                                        </p>
                                        {isDuplicateNewTag && !isAddingTag && (
                                            <p className="mt-1 text-xs text-amber-600">This tag is already attached.</p>
                                        )}

                                        {sourceTags.length > 0 ? (
                                            <div className="mt-3 flex flex-wrap gap-2">
                                                {sourceTags.map((tag) => {
                                                    const isRemovingTag = tagIdsBeingRemoved.includes(tag.id)
                                                    return (
                                                        <span
                                                            key={tag.id}
                                                            className="inline-flex items-center gap-1 rounded-full border bg-muted/20 px-2.5 py-1 text-xs font-medium"
                                                        >
                                                            <Link
                                                                href={`/?tag=${encodeURIComponent(tag.name)}`}
                                                                className="hover:text-emerald-600 transition-colors"
                                                                title={`Filter sources by "${tag.name}"`}
                                                            >
                                                                {tag.name}
                                                            </Link>
                                                            <button
                                                                type="button"
                                                                className="inline-flex h-4 w-4 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-50"
                                                                disabled={isRemovingTag}
                                                                aria-label={`Remove tag ${tag.name}`}
                                                                onClick={() => {
                                                                    void handleRemoveTag(tag)
                                                                }}
                                                            >
                                                                <X className="h-3 w-3" />
                                                            </button>
                                                        </span>
                                                    )
                                                })}
                                            </div>
                                        ) : (
                                            <p className="mt-3 text-sm text-muted-foreground">No tags yet.</p>
                                        )}
                                    </div>
                                </aside>
                            </div>
                        </div>
                    )}
                </section>
            </main>
        </div>
    )
}
