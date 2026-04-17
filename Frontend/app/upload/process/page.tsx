"use client"

import { useEffect, useRef, useState } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { ArrowLeft, FileUp, Mic, Type } from "lucide-react"
import { Button } from "@/components/ui/button"
import { TopNav } from "@/components/top-nav"
import { api, type SourceRecord } from "@/lib/api"

type UploadMode = "recording" | "file" | "text"

const allowedUploadExtensions = new Set([".wav", ".mp3", ".m4a", ".txt", ".md"])
const allowedUploadMimeTypes = new Set(["audio/mpeg", "audio/wav", "text/plain", "text/markdown"])
const allowedM4aMimeTypes = new Set(["audio/mp4", "audio/x-m4a"])

const getFileExtension = (filename: string) => {
    const dotIndex = filename.lastIndexOf(".")
    return dotIndex === -1 ? "" : filename.slice(dotIndex).toLowerCase()
}

const validateUploadFile = (file: File) => {
    const extension = getFileExtension(file.name)
    if (!allowedUploadExtensions.has(extension)) {
        return "Unsupported file type. Use .wav, .mp3, .m4a, .txt, or .md."
    }

    const mimeType = file.type.toLowerCase()
    if (!mimeType) {
        return null
    }

    const isM4aMime = extension === ".m4a" && allowedM4aMimeTypes.has(mimeType)
    if (!allowedUploadMimeTypes.has(mimeType) && !isM4aMime) {
        return "Unsupported file format. Please upload .wav, .mp3, .m4a, .txt, or .md files."
    }

    return null
}

const isUploadMode = (value: string | null): value is UploadMode => {
    return value === "recording" || value === "file" || value === "text"
}

export default function ProcessUploadPage() {
    const searchParams = useSearchParams()
    const fileInputRef = useRef<HTMLInputElement>(null)

    const [mode, setMode] = useState<UploadMode>("file")
    const [textValue, setTextValue] = useState("")
    const [isSaving, setIsSaving] = useState(false)
    const [isDragOver, setIsDragOver] = useState(false)
    const [notice, setNotice] = useState<string | null>(null)
    const [createdSource, setCreatedSource] = useState<SourceRecord | null>(null)

    useEffect(() => {
        const requestedMode = searchParams.get("mode")
        if (isUploadMode(requestedMode)) {
            setMode(requestedMode)
        }
    }, [searchParams])

    const handleUploadFile = async (selectedFile: File | null) => {
        if (!selectedFile || isSaving) return

        const validationError = validateUploadFile(selectedFile)
        if (validationError) {
            setNotice(validationError)
            return
        }

        setIsSaving(true)
        try {
            const created = await api.uploadFileSource(selectedFile, true)
            setCreatedSource(created)
            setNotice(`Uploaded ${selectedFile.name} and sent for processing.`)
        } catch (error) {
            setNotice(`Upload failed: ${error instanceof Error ? error.message : "Unknown error"}`)
        } finally {
            setIsSaving(false)
            setIsDragOver(false)
            if (fileInputRef.current) {
                fileInputRef.current.value = ""
            }
        }
    }

    const handleUploadText = async () => {
        if (!textValue.trim() || isSaving) return

        setIsSaving(true)
        try {
            const created = await api.uploadTextSource(textValue, true)
            setCreatedSource(created)
            setTextValue("")
            setNotice("Text source saved and sent for processing.")
        } catch (error) {
            setNotice(`Could not save source: ${error instanceof Error ? error.message : "Unknown error"}`)
        } finally {
            setIsSaving(false)
        }
    }

    const handleFileDrop = async (event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault()
        event.stopPropagation()
        setIsDragOver(false)
        await handleUploadFile(event.dataTransfer.files?.[0] ?? null)
    }

    const handleFileDragEnter = (event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault()
        event.stopPropagation()
        if (!isSaving) {
            setIsDragOver(true)
        }
    }

    const handleFileDragOver = (event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault()
        event.stopPropagation()
        if (!isSaving) {
            setIsDragOver(true)
        }
    }

    const handleFileDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault()
        event.stopPropagation()
        const nextTarget = event.relatedTarget
        if (!(nextTarget instanceof Node) || !event.currentTarget.contains(nextTarget)) {
            setIsDragOver(false)
        }
    }

    return (
        <div className="min-h-screen bg-background">
            <TopNav activePath="/" />

            <main className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6">
                <Link
                    href="/"
                    className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                    <ArrowLeft className="h-4 w-4" />
                    Back to sources
                </Link>

                <section className="mt-4 rounded-2xl border bg-card p-5 shadow-sm sm:p-6">
                    <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600">Upload</p>
                        <h1 className="mt-2 text-2xl font-semibold tracking-tight">Upload and process</h1>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Sources uploaded here are processed immediately for transcription and search.
                        </p>
                    </div>

                    <div className="mt-5 grid grid-cols-3 gap-2">
                        <button
                            onClick={() => setMode("recording")}
                            className={`rounded-xl border-2 p-3 text-left transition-colors ${mode === "recording"
                                    ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20"
                                    : "border-border hover:border-emerald-400 hover:bg-emerald-50/50 dark:hover:bg-emerald-900/10"
                                }`}
                        >
                            <Mic className="h-4 w-4 text-emerald-600 mb-2" />
                            <div className="text-sm font-medium">Record</div>
                            <div className="text-xs text-muted-foreground">Mic capture</div>
                        </button>
                        <button
                            onClick={() => setMode("file")}
                            className={`rounded-xl border-2 p-3 text-left transition-colors ${mode === "file"
                                    ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                                    : "border-border hover:border-blue-400 hover:bg-blue-50/50 dark:hover:bg-blue-900/10"
                                }`}
                        >
                            <FileUp className="h-4 w-4 text-blue-600 mb-2" />
                            <div className="text-sm font-medium">File</div>
                            <div className="text-xs text-muted-foreground">Upload now</div>
                        </button>
                        <button
                            onClick={() => setMode("text")}
                            className={`rounded-xl border-2 p-3 text-left transition-colors ${mode === "text"
                                    ? "border-amber-500 bg-amber-50 dark:bg-amber-900/20"
                                    : "border-border hover:border-amber-400 hover:bg-amber-50/50 dark:hover:bg-amber-900/10"
                                }`}
                        >
                            <Type className="h-4 w-4 text-amber-600 mb-2" />
                            <div className="text-sm font-medium">Text</div>
                            <div className="text-xs text-muted-foreground">Paste content</div>
                        </button>
                    </div>

                    {mode === "recording" && (
                        <div className="mt-4 rounded-xl border bg-muted/30 p-4">
                            <p className="text-sm">
                                Direct microphone capture is not connected yet. Upload an audio file in File mode and it will be
                                processed immediately.
                            </p>
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="mt-3"
                                onClick={() => setMode("file")}
                            >
                                Switch to file upload
                            </Button>
                        </div>
                    )}

                    {mode === "file" && (
                        <div
                            className={`mt-4 rounded-xl border-2 border-dashed p-6 text-center transition-colors ${isDragOver ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20" : "border-border"
                                }`}
                            onDrop={(event) => {
                                void handleFileDrop(event)
                            }}
                            onDragEnter={handleFileDragEnter}
                            onDragOver={handleFileDragOver}
                            onDragLeave={handleFileDragLeave}
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                className="hidden"
                                accept=".wav,.mp3,.m4a,.txt,.md"
                                onChange={(event) => {
                                    void handleUploadFile(event.target.files?.[0] ?? null)
                                }}
                            />
                            <FileUp className="mx-auto h-7 w-7 text-muted-foreground" />
                            <p className="mt-2 text-sm text-muted-foreground">Drag and drop a file here</p>
                            <p className="mt-1 text-xs text-muted-foreground">or</p>
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="mt-2"
                                disabled={isSaving}
                                onClick={() => fileInputRef.current?.click()}
                            >
                                {isSaving ? "Uploading..." : "Browse files"}
                            </Button>
                            <p className="mt-3 text-[11px] text-muted-foreground">Allowed: .wav, .mp3, .m4a, .txt, .md</p>
                        </div>
                    )}

                    {mode === "text" && (
                        <div className="mt-4 space-y-3 rounded-xl border bg-muted/20 p-4">
                            <textarea
                                value={textValue}
                                onChange={(event) => setTextValue(event.target.value)}
                                placeholder="Paste your transcript, notes, or reflection..."
                                rows={8}
                                className="w-full rounded-lg border bg-background p-3 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                            />
                            <Button
                                type="button"
                                onClick={handleUploadText}
                                disabled={!textValue.trim() || isSaving}
                                className="bg-emerald-600 hover:bg-emerald-700"
                            >
                                {isSaving ? "Saving..." : "Save and process"}
                            </Button>
                        </div>
                    )}

                    {notice && (
                        <p className="mt-4 rounded-lg border bg-background p-3 text-sm text-muted-foreground">{notice}</p>
                    )}

                    {createdSource && (
                        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm dark:border-emerald-900/40 dark:bg-emerald-900/20">
                            <span className="text-emerald-700 dark:text-emerald-300">Saved source #{createdSource.id}</span>
                            <Link href={`/sources/${createdSource.id}`} className="font-medium text-emerald-700 underline underline-offset-2 dark:text-emerald-300">
                                Open source view
                            </Link>
                        </div>
                    )}
                </section>
            </main>
        </div>
    )
}
