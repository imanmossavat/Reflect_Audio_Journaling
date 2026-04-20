"use client"

import { useEffect, useMemo, useState, type FormEvent } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import { ArrowLeft, CalendarClock, CircleDot, FileAudio2, FileText, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { TopNav } from "@/components/top-nav"
import { useToast } from "@/hooks/use-toast"
import { api, type SourceRecord, type SourceTag } from "@/lib/api"

const getSourceKind = (source: SourceRecord) => {
    const fileType = (source.file_type ?? "").toLowerCase()
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

export default function SourceDetailPage() {
    const params = useParams<{ id: string }>()
    const { toast } = useToast()

    const [source, setSource] = useState<SourceRecord | null>(null)
    const [sourceText, setSourceText] = useState("")
    const [sourceTags, setSourceTags] = useState<SourceTag[]>([])
    const [newTagName, setNewTagName] = useState("")
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [isProcessing, setIsProcessing] = useState(false)
    const [isAddingTag, setIsAddingTag] = useState(false)
    const [tagIdsBeingRemoved, setTagIdsBeingRemoved] = useState<number[]>([])
    const [processNotice, setProcessNotice] = useState<string | null>(null)

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
            setProcessNotice(null)
            setSourceTags([])
            setNewTagName("")
            setTagIdsBeingRemoved([])

            try {
                const loadedSource = await api.getSourceById(sourceId)
                setSource(loadedSource)

                const textPromise = loadedSource.text ? Promise.resolve(loadedSource.text) : api.getSourceText(sourceId)
                const [fullText, loadedTags] = await Promise.all([textPromise, api.getSourceTags(sourceId)])
                setSourceText(fullText ?? "")
                setSourceTags(loadedTags)
            } catch (loadError) {
                setError(loadError instanceof Error ? loadError.message : "Unknown error")
            } finally {
                setIsLoading(false)
            }
        }

        void loadSource()
    }, [sourceId])

    const handleAddTag = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault()
        if (!source || sourceId === null || isAddingTag) return

        const normalizedName = newTagName.trim().toLowerCase()
        if (!normalizedName) return

        if (sourceTags.some((tag) => tag.name.toLowerCase() === normalizedName)) {
            toast({
                title: "Tag already exists",
                description: `${normalizedName} is already attached to this source.`,
            })
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
            toast({
                title: "Tag added",
                description: `${addedTag.name} was added.`,
            })
        } catch (addTagError) {
            toast({
                title: "Could not add tag",
                description: addTagError instanceof Error ? addTagError.message : "Unknown error",
                variant: "destructive",
            })
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
            toast({
                title: "Tag removed",
                description: `${tag.name} was removed.`,
            })
        } catch (removeTagError) {
            toast({
                title: "Could not remove tag",
                description: removeTagError instanceof Error ? removeTagError.message : "Unknown error",
                variant: "destructive",
            })
        } finally {
            setTagIdsBeingRemoved((currentIds) => currentIds.filter((id) => id !== tag.id))
        }
    }

    const handleProcess = async () => {
        if (!source || isProcessing) return

        setIsProcessing(true)
        try {
            const updatedSource = await api.processSource(source.id)
            setSource(updatedSource)
            if (typeof updatedSource.text === "string") {
                setSourceText(updatedSource.text)
            }
            setProcessNotice("Source processed successfully.")
        } catch (processError) {
            setProcessNotice(`Could not process source: ${processError instanceof Error ? processError.message : "Unknown error"}`)
        } finally {
            setIsProcessing(false)
        }
    }

    const canProcess = source && source.status.toLowerCase() !== "processed"
    const normalizedNewTag = newTagName.trim().toLowerCase()
    const isDuplicateNewTag = normalizedNewTag.length > 0 && sourceTags.some((tag) => tag.name.toLowerCase() === normalizedNewTag)
    const sourceKind = source ? getSourceKind(source) : "File"

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
                                <h1 className="mt-2 text-2xl font-semibold tracking-tight">{source.filename || "Quick thought"}</h1>
                                <div className={`mt-3 inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium ${getStatusClassName(source.status)}`}>
                                    <CircleDot className="h-3 w-3" />
                                    {source.status}
                                </div>
                            </div>

                            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
                                <div className="rounded-xl border bg-background p-4 sm:p-5">
                                    <div className="flex flex-wrap items-center justify-between gap-3">
                                        <h2 className="text-base font-semibold">Complete transcript</h2>
                                        {canProcess && (
                                            <Button
                                                type="button"
                                                size="sm"
                                                className="bg-emerald-600 hover:bg-emerald-700"
                                                disabled={isProcessing}
                                                onClick={() => {
                                                    void handleProcess()
                                                }}
                                            >
                                                {isProcessing ? "Processing..." : "Process source"}
                                            </Button>
                                        )}
                                    </div>

                                    {processNotice && (
                                        <p className="mt-3 rounded-lg border bg-muted/20 p-3 text-sm text-muted-foreground">{processNotice}</p>
                                    )}

                                    {sourceText.trim() ? (
                                        <pre className="mt-4 whitespace-pre-wrap wrap-break-word text-sm leading-6 text-foreground">{sourceText}</pre>
                                    ) : (
                                        <p className="mt-4 text-sm text-muted-foreground">No transcript or text is available for this source yet.</p>
                                    )}
                                </div>

                                <aside className="space-y-4">
                                    <div className="rounded-xl border bg-background p-4">
                                        <h2 className="text-sm font-semibold">Details</h2>
                                        <div className="mt-3 space-y-2">
                                            <div className="rounded-lg border bg-muted/20 p-3">
                                                <div className="text-xs text-muted-foreground">Created</div>
                                                <div className="mt-1 flex items-center gap-2 text-sm font-medium">
                                                    <CalendarClock className="h-4 w-4 text-muted-foreground" />
                                                    {new Date(source.created_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}
                                                </div>
                                            </div>
                                            <div className="rounded-lg border bg-muted/20 p-3">
                                                <div className="text-xs text-muted-foreground">Type</div>
                                                <div className="mt-1 flex items-center gap-2 text-sm font-medium">
                                                    {sourceKind === "Audio" ? (
                                                        <FileAudio2 className="h-4 w-4 text-muted-foreground" />
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
                                                disabled={isAddingTag}
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
                                                            {tag.name}
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
