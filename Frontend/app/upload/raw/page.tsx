"use client"

import { useRef, useState } from "react"
import Link from "next/link"
import { FileUp, Mic, Pause, Smartphone, Type } from "lucide-react"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"

type RawUploadMode = "file" | "text" | "recording"

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

export default function RawUploadPage() {
    const fileInputRef = useRef<HTMLInputElement>(null)
    const mediaRecorderRef = useRef<MediaRecorder | null>(null)
    const audioChunksRef = useRef<Blob[]>([])
    const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

    const [mode, setMode] = useState<RawUploadMode>("file")
    const [textValue, setTextValue] = useState("")
    const [isSaving, setIsSaving] = useState(false)
    const [isDragOver, setIsDragOver] = useState(false)
    const [isRecording, setIsRecording] = useState(false)
    const [recordingSeconds, setRecordingSeconds] = useState(0)
    const [notice, setNotice] = useState<string | null>(null)
    const [queued, setQueued] = useState(false)

    const formatDuration = (seconds: number) => {
        const m = Math.floor(seconds / 60).toString().padStart(2, "0")
        const s = (seconds % 60).toString().padStart(2, "0")
        return `${m}:${s}`
    }

    const handleToggleRecording = () => {
        if (isRecording) {
            if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
                mediaRecorderRef.current.stop()
            }
            if (recordingTimerRef.current) {
                clearInterval(recordingTimerRef.current)
                recordingTimerRef.current = null
            }
            setIsRecording(false)
            return
        }

        if (!window.isSecureContext) {
            setNotice("Recording requires HTTPS or localhost. Open the app on localhost, or set up HTTPS.")
            return
        }

        if (!navigator.mediaDevices?.getUserMedia) {
            setNotice("Microphone recording is not supported in this browser.")
            return
        }

        navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
            const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
                ? "audio/webm;codecs=opus"
                : MediaRecorder.isTypeSupported("audio/webm")
                    ? "audio/webm"
                    : "audio/ogg"

            const mediaRecorder = new MediaRecorder(stream, { mimeType })
            mediaRecorderRef.current = mediaRecorder
            audioChunksRef.current = []

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data)
                }
            }

            mediaRecorder.onstop = () => {
                stream.getTracks().forEach((track) => track.stop())
                const baseMime = mimeType.split(";")[0]
                const extension = baseMime.includes("ogg") ? ".ogg" : ".webm"
                const audioBlob = new Blob(audioChunksRef.current, { type: baseMime })
                // Human-facing name; the backend strips the extension and dedupes
                // same-day recordings as "... (1)". Long month/day avoids ":" which
                // is illegal in filenames.
                const recordedOn = new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })
                const audioFile = new File([audioBlob], `Voice recording of ${recordedOn}${extension}`, { type: baseMime })

                setIsSaving(true)
                api.dropFileToInbox(audioFile)
                    .then(() => {
                        setQueued(true)
                        setRecordingSeconds(0)
                        setNotice("Recording queued for processing.")
                    })
                    .catch((error) => {
                        setNotice(`Recording upload failed: ${error instanceof Error ? error.message : "Unknown error"}`)
                    })
                    .finally(() => {
                        setIsSaving(false)
                    })
            }

            mediaRecorder.start()
            setIsRecording(true)
            setRecordingSeconds(0)
            recordingTimerRef.current = setInterval(() => {
                setRecordingSeconds((prev) => prev + 1)
            }, 1000)
        }).catch((error) => {
            setNotice(`Microphone access denied: ${error instanceof Error ? error.message : "Unknown error"}`)
        })
    }

    const handleUploadFile = async (selectedFile: File | null) => {
        if (!selectedFile || isSaving) return

        const validationError = validateUploadFile(selectedFile)
        if (validationError) {
            setNotice(validationError)
            return
        }

        setIsSaving(true)
        try {
            await api.dropFileToInbox(selectedFile)
            setQueued(true)
            setNotice(`${selectedFile.name} queued for processing.`)
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
            await api.dropTextToInbox(textValue)
            setQueued(true)
            setTextValue("")
            setNotice("Text note queued for processing.")
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
            <main className="mx-auto w-full max-w-xl px-4 py-8 sm:px-6">

                <section className="mt-4 rounded-2xl border bg-card p-5 shadow-sm sm:p-6">
                    <div className="flex items-center gap-2 text-emerald-600">
                        <Smartphone className="h-4 w-4" />
                        <p className="text-xs font-semibold uppercase tracking-[0.18em]">Phone upload</p>
                    </div>
                    <h1 className="mt-2 text-2xl font-semibold tracking-tight">Upload raw source</h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Perfect for fast capture from your phone. These uploads stay unprocessed, with no immediate transcription or chunk processing.
                    </p>

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
                            <div className="text-xs text-muted-foreground">Voice memo</div>
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
                            <div className="text-xs text-muted-foreground">Audio or text file</div>
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
                            <div className="text-xs text-muted-foreground">Quick note</div>
                        </button>
                    </div>

                    {mode === "recording" && (
                        <div className="mt-4 rounded-xl border bg-muted/20 p-5 space-y-4 text-center">
                            <div className="flex flex-col items-center gap-3">
                                <button
                                    onClick={handleToggleRecording}
                                    disabled={isSaving}
                                    className={`p-5 rounded-full transition-colors disabled:opacity-50 ${isRecording
                                        ? "bg-red-500 text-white animate-pulse"
                                        : "bg-emerald-500 text-white hover:bg-emerald-600"
                                        }`}
                                >
                                    {isRecording ? <Pause className="h-6 w-6" /> : <Mic className="h-6 w-6" />}
                                </button>
                                {isRecording && (
                                    <span className="text-lg font-mono tabular-nums text-muted-foreground">{formatDuration(recordingSeconds)}</span>
                                )}
                            </div>
                            {isSaving && <p className="text-sm text-muted-foreground">Uploading recording...</p>}
                            {!isRecording && !isSaving && <p className="text-sm text-muted-foreground">Tap to start recording</p>}
                            {isRecording && <p className="text-sm text-muted-foreground">Tap to stop and save</p>}
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
                            <p className="mt-2 text-sm text-muted-foreground">Tap below to select a file</p>
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="mt-3"
                                disabled={isSaving}
                                onClick={() => fileInputRef.current?.click()}
                            >
                                {isSaving ? "Uploading..." : "Choose file"}
                            </Button>
                            <p className="mt-3 text-[11px] text-muted-foreground">Allowed: .wav, .mp3, .m4a, .txt, .md</p>
                        </div>
                    )}

                    {mode === "text" && (
                        <div className="mt-4 space-y-3 rounded-xl border bg-muted/20 p-4">
                            <textarea
                                value={textValue}
                                onChange={(event) => setTextValue(event.target.value)}
                                placeholder="Write a quick thought..."
                                rows={7}
                                className="w-full rounded-lg border bg-background p-3 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                            />
                            <Button
                                type="button"
                                onClick={handleUploadText}
                                disabled={!textValue.trim() || isSaving}
                                className="bg-emerald-600 hover:bg-emerald-700"
                            >
                                {isSaving ? "Saving..." : "Save raw source"}
                            </Button>
                        </div>
                    )}

                    {notice && (
                        <p className="mt-4 rounded-lg border bg-background p-3 text-sm text-muted-foreground">{notice}</p>
                    )}

                    {queued && (
                        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm dark:border-emerald-900/40 dark:bg-emerald-900/20">
                            <span className="text-emerald-700 dark:text-emerald-300">Queued — transcription and indexing will run automatically on the device that runs the server.</span>
                        </div>
                    )}
                </section>
            </main>
        </div>
    )
}
