"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import { ArrowLeft, CalendarClock, CircleDot, FileAudio2, FileText, Hash } from "lucide-react"
import { Button } from "@/components/ui/button"
import { TopNav } from "@/components/top-nav"
import { api, type SourceRecord } from "@/lib/api"

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

    const [source, setSource] = useState<SourceRecord | null>(null)
    const [sourceText, setSourceText] = useState("")
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [isProcessing, setIsProcessing] = useState(false)
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
                return
            }

            setIsLoading(true)
            setError(null)
            setProcessNotice(null)

            try {
                const loadedSource = await api.getSourceById(sourceId)
                setSource(loadedSource)

                if (loadedSource.text) {
                    setSourceText(loadedSource.text)
                    return
                }

                const fullText = await api.getSourceText(sourceId)
                setSourceText(fullText ?? "")
            } catch (loadError) {
                setError(loadError instanceof Error ? loadError.message : "Unknown error")
            } finally {
                setIsLoading(false)
            }
        }

        void loadSource()
    }, [sourceId])

    const handleProcess = async () => {
        if (!source || isProcessing) return

        setIsProcessing(true)
        try {
            const updatedSource = await api.processSource(source.id)
            setSource(updatedSource)
            setProcessNotice("Source processed successfully.")
        } catch (processError) {
            setProcessNotice(`Could not process source: ${processError instanceof Error ? processError.message : "Unknown error"}`)
        } finally {
            setIsProcessing(false)
        }
    }

    const canProcess = source && sourceText.trim().length > 0 && source.status.toLowerCase() !== "processed"

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

                            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                                <div className="rounded-xl border bg-muted/20 p-3">
                                    <div className="text-xs text-muted-foreground">Source ID</div>
                                    <div className="mt-1 flex items-center gap-2 text-sm font-medium">
                                        <Hash className="h-4 w-4 text-muted-foreground" />
                                        {source.id}
                                    </div>
                                </div>
                                <div className="rounded-xl border bg-muted/20 p-3">
                                    <div className="text-xs text-muted-foreground">Type</div>
                                    <div className="mt-1 flex items-center gap-2 text-sm font-medium">
                                        {getSourceKind(source) === "Audio" ? (
                                            <FileAudio2 className="h-4 w-4 text-muted-foreground" />
                                        ) : (
                                            <FileText className="h-4 w-4 text-muted-foreground" />
                                        )}
                                        {getSourceKind(source)}
                                    </div>
                                </div>
                                <div className="rounded-xl border bg-muted/20 p-3 sm:col-span-2">
                                    <div className="text-xs text-muted-foreground">Created</div>
                                    <div className="mt-1 flex items-center gap-2 text-sm font-medium">
                                        <CalendarClock className="h-4 w-4 text-muted-foreground" />
                                        {new Date(source.created_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}
                                    </div>
                                </div>
                            </div>

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
                        </div>
                    )}
                </section>
            </main>
        </div>
    )
}
