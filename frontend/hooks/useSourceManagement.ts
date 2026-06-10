"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { api, type SourceRecord, PROCESSING_STATUSES } from "@/lib/api"
import { formatListTimestamp } from "@/lib/utils"
import type { RawSource, AddSourceMode } from "@/components/home/types"
import type { OnboardingProfile } from "@/components/onboarding-modal"
import { toast } from "sonner"

const profileStorageKey = "reflect_profile"
const onboardingSkippedStorageKey = "reflect_onboarding_skipped"
const mobileOriginStorageKey = "reflect_mobile_origin"

// idle → recording ⇄ paused. Pausing drops into the review screen (playback +
// upload + continue); there is no separate "recorded" step.
export type RecordingState = "idle" | "recording" | "paused"

const allowedUploadExtensions = new Set([".wav", ".mp3", ".m4a", ".webm", ".ogg", ".txt", ".md"])
const allowedUploadMimeTypes = new Set(["audio/mpeg", "audio/wav", "audio/webm", "audio/ogg", "text/plain", "text/markdown"])
const allowedM4aMimeTypes = new Set(["audio/mp4", "audio/x-m4a"])

const tagPalette = ["#0ea5e9", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6", "#f97316"]

const getFileExtension = (filename: string) => {
  const dotIndex = filename.lastIndexOf(".")
  return dotIndex === -1 ? "" : filename.slice(dotIndex).toLowerCase()
}

const validateUploadFile = (file: File) => {
  const extension = getFileExtension(file.name)
  if (!allowedUploadExtensions.has(extension))
    return "Unsupported file type. Use .wav, .mp3, .m4a, .txt, or .md."
  const mimeType = file.type.toLowerCase()
  if (!mimeType) return null
  const isM4aMime = extension === ".m4a" && allowedM4aMimeTypes.has(mimeType)
  if (!allowedUploadMimeTypes.has(mimeType) && !isM4aMime)
    return "Unsupported file format. Please upload .wav, .mp3, .m4a, .txt, or .md files."
  return null
}

const getTagColor = (tagName: string) => {
  let hash = 0
  for (let index = 0; index < tagName.length; index += 1)
    hash = (hash * 31 + tagName.charCodeAt(index)) >>> 0
  return tagPalette[hash % tagPalette.length]
}

const mapSourceType = (source: SourceRecord): RawSource["type"] => {
  const fileType = (source.file_type ?? "").toLowerCase()
  if (fileType.includes("audio")) return "recording"
  if (fileType.includes("text") || !source.filename) return "text"
  return "file"
}

// Title shown in the sources tab. Text notes have no filename; everything
// else shows its raw filename as-is.
const displaySourceName = (source: SourceRecord): string => {
  if (!source.filename) return "Quick thought"
  return source.filename
}

// Newest first; numeric id breaks ties for sources sharing a timestamp.
export const compareSourcesNewestFirst = (a: RawSource, b: RawSource): number =>
  b.createdAt.localeCompare(a.createdAt) || Number(b.id) - Number(a.id)

export const mapBackendSource = (source: SourceRecord): RawSource => ({
  id: String(source.id),
  type: mapSourceType(source),
  name: displaySourceName(source),
  content: source.text ?? undefined,
  createdAt: source.created_at,
  timestamp: formatListTimestamp(source.created_at),
  included: true,
  tags: [],
  status: source.status,
})

export function useSourceManagement() {
  const [rawSources, setRawSources] = useState<RawSource[]>([])
  const [isLoadingSources, setIsLoadingSources] = useState(true)
  const [isSavingSource, setIsSavingSource] = useState(false)
  const [isDragOverUpload, setIsDragOverUpload] = useState(false)
  const [addSourceMode, setAddSourceMode] = useState<AddSourceMode>(null)
  const [newSourceText, setNewSourceText] = useState("")
  // Recording lifecycle: idle → recording ⇄ paused → recorded (review). The
  // audio is only uploaded once the user explicitly saves from the review step.
  const [recordingState, setRecordingState] = useState<RecordingState>("idle")
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const [recordedAudioUrl, setRecordedAudioUrl] = useState<string | null>(null)
  const [processingSources, setProcessingSources] = useState<Set<number>>(new Set())
  const [rawUploadUrl, setRawUploadUrl] = useState("/upload/raw")
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const recordingStreamRef = useRef<MediaStream | null>(null)
  const recordingMimeRef = useRef<string>("audio/webm")
  // Set just before stop() so the shared onstop handler knows whether to upload
  // the finalised clip (Upload) or simply discard it (delete/close).
  const uploadPendingRef = useRef(false)
  const rawSourcesRef = useRef<RawSource[]>([])
  const maxSourceIdRef = useRef(0)

  useEffect(() => { rawSourcesRef.current = rawSources }, [rawSources])

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const newOnes = await api.getSources(maxSourceIdRef.current)
        if (newOnes.length === 0) return
        const maxId = Math.max(...newOnes.map((s) => s.id ?? 0))
        if (maxId > maxSourceIdRef.current) maxSourceIdRef.current = maxId
        const existingIds = new Set(rawSourcesRef.current.map((s) => s.id))
        const mapped = newOnes
          .map(mapBackendSource)
          .filter((s) => !existingIds.has(s.id))
        if (mapped.length === 0) return
        setRawSources((prev) => {
          const prevIds = new Set(prev.map((s) => s.id))
          const additions = mapped.filter((s) => !prevIds.has(s.id))
          if (additions.length === 0) return prev
          return [...additions, ...prev].sort(compareSourcesNewestFirst)
        })
        const processingIds = mapped
          .filter((s) => PROCESSING_STATUSES.has(s.status))
          .map((s) => Number(s.id))
          .filter((id) => Number.isInteger(id) && id > 0)
        if (processingIds.length > 0) {
          setProcessingSources((prev) => {
            const next = new Set(prev)
            processingIds.forEach((id) => next.add(id))
            return next
          })
        }
      } catch { /* ignore transient errors */ }
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (processingSources.size === 0) return
    const interval = setInterval(async () => {
      const done: number[] = []
      await Promise.all(
        [...processingSources].map(async (sourceId) => {
          try {
            const updated = await api.getSourceById(sourceId)
            setRawSources((prev) =>
              prev.map((s) =>
                s.id === String(sourceId)
                  ? { ...s, status: updated.status, content: updated.text ?? s.content }
                  : s
              )
            )
            if (!PROCESSING_STATUSES.has(updated.status)) done.push(sourceId)
          } catch { /* ignore transient errors */ }
        })
      )
      if (done.length > 0) {
        setProcessingSources((prev) => {
          const next = new Set(prev)
          done.forEach((id) => next.delete(id))
          return next
        })
      }
    }, 2500)
    return () => clearInterval(interval)
  }, [processingSources])

  useEffect(() => {
    const loadSources = async () => {
      setIsLoadingSources(true)
      try {
        const sources = await api.getSources()
        const mappedSources = sources.map(mapBackendSource)
        const mappedWithTags = await Promise.all(
          mappedSources.map(async (source) => {
            const numericId = Number(source.id)
            if (!Number.isInteger(numericId) || numericId <= 0) return source
            try {
              const loadedTags = await api.getSourceTags(numericId)
              return { ...source, tags: loadedTags.map((tag) => ({ name: tag.name, color: getTagColor(tag.name) })) }
            } catch { return source }
          })
        )
        const mapped = mappedWithTags.sort(compareSourcesNewestFirst)
        setRawSources(mapped)
        maxSourceIdRef.current = Math.max(0, ...sources.map((s) => s.id ?? 0))
        const inProgress = new Set(
          mapped
            .filter((s) => PROCESSING_STATUSES.has(s.status))
            .map((s) => Number(s.id))
            .filter((id) => Number.isInteger(id) && id > 0)
        )
        if (inProgress.size > 0) setProcessingSources(inProgress)
        // Onboard on the profile alone: a fresh install now ships a seeded
        // example note, so "no sources" can no longer stand in for "new user".
        const hasProfile = Boolean(window.localStorage.getItem(profileStorageKey))
        const hasSkipped = Boolean(window.localStorage.getItem(onboardingSkippedStorageKey))
        setIsOnboardingOpen(!hasProfile && !hasSkipped)
      } catch (error) {
        toast.error(`Could not load sources: ${error instanceof Error ? error.message : "Unknown error"}`)
      } finally {
        setIsLoadingSources(false)
      }
    }
    void loadSources()
  }, [])

  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedOrigin = window.localStorage.getItem(mobileOriginStorageKey)
      if (savedOrigin) {
        setRawUploadUrl(`${savedOrigin.replace(/\/$/, "")}/upload/raw`)
      } else {
        setRawUploadUrl(`${window.location.origin}/upload/raw`)
      }
    }
  }, [])

  const includedSources = useMemo(() => rawSources.filter((s) => s.included), [rawSources])

  const handleSetAddSourceMode = (mode: AddSourceMode) => {
    setIsDragOverUpload(false)
    setAddSourceMode(mode)
  }

  const handleSetSourceIncluded = (sourceId: string, included: boolean) => {
    setRawSources((prev) => prev.map((s) => (s.id === sourceId ? { ...s, included } : s)))
  }

  const handleAddTextSource = async () => {
    if (!newSourceText.trim()) return
    setIsSavingSource(true)
    try {
      const created = await api.uploadTextSource(newSourceText, true)
      if (created.id > maxSourceIdRef.current) maxSourceIdRef.current = created.id
      setRawSources((prev) => (prev.some((s) => s.id === String(created.id)) ? prev : [mapBackendSource(created), ...prev].sort(compareSourcesNewestFirst)))
      setProcessingSources((prev) => new Set([...prev, created.id]))
      setNewSourceText("")
      setAddSourceMode(null)
      toast("Text source added — processing in background.")
    } catch (error) {
      toast.error(`Could not save source: ${error instanceof Error ? error.message : "Unknown error"}`)
    } finally {
      setIsSavingSource(false)
    }
  }

  const handleSaveNote = async (content: string, title?: string) => {
    if (!content.trim() || isSavingSource) return
    setIsSavingSource(true)
    try {
      // `content` is rich HTML from the note editor; send it as source_html so the
      // backend keeps it for display and derives the plain text used for RAG.
      const created = await api.uploadTextSource(content, true, content)
      const trimmedTitle = title?.trim()
      if (trimmedTitle) {
        try {
          await api.patchSource(created.id, { filename: trimmedTitle })
          created.filename = trimmedTitle
        } catch { /* keep default title if rename fails */ }
      }
      if (created.id > maxSourceIdRef.current) maxSourceIdRef.current = created.id
      setRawSources((prev) => (prev.some((s) => s.id === String(created.id)) ? prev : [mapBackendSource(created), ...prev].sort(compareSourcesNewestFirst)))
      setProcessingSources((prev) => new Set([...prev, created.id]))
      toast("Note saved — processing in background.")
    } catch (error) {
      toast.error(`Could not save note: ${error instanceof Error ? error.message : "Unknown error"}`)
      throw error
    } finally {
      setIsSavingSource(false)
    }
  }

  const handleAddFileSource = async (selectedFile: File | null) => {
    if (!selectedFile || isSavingSource) return
    const validationError = validateUploadFile(selectedFile)
    if (validationError) { toast.error(validationError); return }
    setIsSavingSource(true)
    try {
      const created = await api.uploadFileSource(selectedFile, true)
      if (created.id > maxSourceIdRef.current) maxSourceIdRef.current = created.id
      setRawSources((prev) => (prev.some((s) => s.id === String(created.id)) ? prev : [mapBackendSource(created), ...prev].sort(compareSourcesNewestFirst)))
      setProcessingSources((prev) => new Set([...prev, created.id]))
      setAddSourceMode(null)
      toast(`${selectedFile.name} uploaded — processing in background.`)
    } catch (error) {
      toast.error(`Upload failed: ${error instanceof Error ? error.message : "Unknown error"}`)
    } finally {
      setIsSavingSource(false)
      setIsDragOverUpload(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  const handleFileDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragOverUpload(false)
    await handleAddFileSource(event.dataTransfer.files?.[0] ?? null)
  }

  const handleFileDragEnter = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    if (!isSavingSource) setIsDragOverUpload(true)
  }

  const handleFileDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    if (!isSavingSource) setIsDragOverUpload(true)
  }

  const handleFileDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    const nextTarget = event.relatedTarget
    if (!(nextTarget instanceof Node) || !event.currentTarget.contains(nextTarget))
      setIsDragOverUpload(false)
  }

  const stopRecordingTimer = () => {
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current)
      recordingTimerRef.current = null
    }
  }

  const startRecordingTimer = () => {
    stopRecordingTimer()
    recordingTimerRef.current = setInterval(() => { setRecordingSeconds((prev) => prev + 1) }, 1000)
  }

  const clearRecordedAudioUrl = () => {
    setRecordedAudioUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return null
    })
  }

  // Build a playable clip from the chunks captured so far. Because the recorder
  // runs with a timeslice, those chunks form a valid (if slightly truncated)
  // clip we can preview while paused, without ending the recording.
  const refreshPausedPreview = () => {
    if (audioChunksRef.current.length === 0) return
    const blob = new Blob(audioChunksRef.current, { type: recordingMimeRef.current })
    setRecordedAudioUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return URL.createObjectURL(blob)
    })
  }

  const uploadRecordedFile = async (audioFile: File) => {
    try {
      const created = await api.uploadFileSource(audioFile, true)
      if (created.id > maxSourceIdRef.current) maxSourceIdRef.current = created.id
      setRawSources((prev) => (prev.some((s) => s.id === String(created.id)) ? prev : [mapBackendSource(created), ...prev].sort(compareSourcesNewestFirst)))
      setProcessingSources((prev) => new Set([...prev, created.id]))
      toast("Recording saved — transcribing in background.")
      audioChunksRef.current = []
      clearRecordedAudioUrl()
      setRecordingSeconds(0)
      setRecordingState("idle")
      setAddSourceMode(null)
    } catch (error) {
      toast.error(`Recording upload failed: ${error instanceof Error ? error.message : "Unknown error"}`)
    } finally {
      setIsSavingSource(false)
    }
  }

  // Tear down the active recorder/stream and drop any captured audio without
  // uploading. Used for an explicit delete and when closing the panel.
  const teardownRecording = () => {
    stopRecordingTimer()
    uploadPendingRef.current = false
    const recorder = mediaRecorderRef.current
    if (recorder && recorder.state !== "inactive") recorder.stop()
    mediaRecorderRef.current = null
    if (recordingStreamRef.current) {
      recordingStreamRef.current.getTracks().forEach((track) => track.stop())
      recordingStreamRef.current = null
    }
    audioChunksRef.current = []
    clearRecordedAudioUrl()
    setRecordingSeconds(0)
    setRecordingState("idle")
  }

  const handleStartRecording = () => {
    if (!window.isSecureContext) {
      toast.error("Microphone unavailable", { description: "Recording requires HTTPS or localhost." })
      return
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      toast.error("Microphone recording is not supported in this browser.")
      return
    }

    navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
      recordingStreamRef.current = stream
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "audio/ogg"
      const baseMime = mimeType.split(";")[0]
      const extension = baseMime.includes("ogg") ? ".ogg" : ".webm"
      recordingMimeRef.current = baseMime

      const mediaRecorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []
      uploadPendingRef.current = false

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data)
        // A flush that lands after pausing refines the preview clip.
        if (mediaRecorderRef.current?.state === "paused") refreshPausedPreview()
      }

      // stop() finalises the clip. Upload only when the user asked to (Upload);
      // a delete/close stops with uploadPending false and the audio is dropped.
      mediaRecorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
        recordingStreamRef.current = null
        if (!uploadPendingRef.current) return
        uploadPendingRef.current = false
        const audioBlob = new Blob(audioChunksRef.current, { type: baseMime })
        const audioFile = new File([audioBlob], `recording-${Date.now()}${extension}`, { type: baseMime })
        void uploadRecordedFile(audioFile)
      }

      // Timeslice so chunks accumulate during recording, enabling pause preview.
      mediaRecorder.start(1000)
      setRecordingState("recording")
      setRecordingSeconds(0)
      startRecordingTimer()
    }).catch((error) => {
      toast.error(`Microphone access denied: ${error instanceof Error ? error.message : "Unknown error"}`)
    })
  }

  // The red button: pause recording and drop into the review screen.
  const handlePauseRecording = () => {
    const recorder = mediaRecorderRef.current
    if (!recorder || recorder.state !== "recording") return
    stopRecordingTimer()
    try { recorder.requestData() } catch { /* best-effort flush */ }
    recorder.pause()
    setRecordingState("paused")
    refreshPausedPreview()
  }

  // Continue recording from the review screen.
  const handleResumeRecording = () => {
    const recorder = mediaRecorderRef.current
    if (!recorder || recorder.state !== "paused") return
    clearRecordedAudioUrl()
    recorder.resume()
    startRecordingTimer()
    setRecordingState("recording")
  }

  // Upload from the review screen: finalise the clip, then send it. onstop
  // builds the complete file (including any tail after the last timeslice).
  const handleSaveRecording = () => {
    const recorder = mediaRecorderRef.current
    if (!recorder || isSavingSource) return
    setIsSavingSource(true)
    uploadPendingRef.current = true
    if (recorder.state !== "inactive") {
      recorder.stop()
    } else {
      const extension = recordingMimeRef.current.includes("ogg") ? ".ogg" : ".webm"
      const audioBlob = new Blob(audioChunksRef.current, { type: recordingMimeRef.current })
      uploadPendingRef.current = false
      void uploadRecordedFile(new File([audioBlob], `recording-${Date.now()}${extension}`, { type: recordingMimeRef.current }))
    }
  }

  // Delete the recording and close the panel. The panel's close (X) button
  // confirms before calling this; the captured audio is dropped, not uploaded.
  const handleCloseRecordingPanel = () => {
    teardownRecording()
    setAddSourceMode(null)
  }

  const handleDeleteSource = async (sourceId: string) => {
    const numericId = Number(sourceId)
    try {
      await api.deleteSource(numericId)
      setRawSources((prev) => prev.filter((s) => s.id !== sourceId))
      toast("Source deleted.")
    } catch (error) {
      toast.error(`Could not delete source: ${error instanceof Error ? error.message : "Unknown error"}`)
    }
  }

  const handleRetryProcessing = async (sourceId: string) => {
    const numericId = Number(sourceId)
    if (!Number.isInteger(numericId) || numericId <= 0) return
    try {
      const updated = await api.processSource(numericId)
      setRawSources((prev) =>
        prev.map((s) => (s.id === sourceId ? { ...s, status: updated.status } : s))
      )
      setProcessingSources((prev) => new Set([...prev, numericId]))
      toast("Reprocessing — running in the background.")
    } catch (error) {
      toast.error(`Could not retry: ${error instanceof Error ? error.message : "Unknown error"}`)
    }
  }

  const handleRenameSource = async (sourceId: string, newName: string) => {
    const numericId = Number(sourceId)
    try {
      await api.patchSource(numericId, { filename: newName })
      setRawSources((prev) => prev.map((s) => (s.id === sourceId ? { ...s, name: newName } : s)))
    } catch (error) {
      toast.error(`Could not rename source: ${error instanceof Error ? error.message : "Unknown error"}`)
    }
  }

  const handleOnboardingSkip = () => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(onboardingSkippedStorageKey, "1")
    }
    setIsOnboardingOpen(false)
  }

  const handleOnboardingSubmit = (nextProfile: OnboardingProfile) => {
    window.localStorage.setItem(profileStorageKey, JSON.stringify(nextProfile))
    setIsOnboardingOpen(false)
    toast(`Welcome ${nextProfile.name} — your profile is saved.`)
  }

  return {
    rawSources, includedSources, isLoadingSources, isSavingSource, isDragOverUpload,
    addSourceMode, newSourceText, recordingState, recordingSeconds, recordedAudioUrl, rawUploadUrl,
    isOnboardingOpen, fileInputRef,
    setNewSourceText, setAddSourceMode: handleSetAddSourceMode,
    setRawSources, setProcessingSources,
    handleSetSourceIncluded, handleAddTextSource, handleSaveNote, handleAddFileSource,
    handleFileDrop, handleFileDragEnter, handleFileDragOver, handleFileDragLeave,
    handleStartRecording, handlePauseRecording, handleResumeRecording,
    handleSaveRecording, handleCloseRecordingPanel,
    handleOnboardingSkip, handleOnboardingSubmit,
    handleDeleteSource, handleRenameSource, handleRetryProcessing,
  }
}
