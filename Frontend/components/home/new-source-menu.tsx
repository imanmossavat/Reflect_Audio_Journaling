"use client"

import { useState } from "react"
import { Mic, FileUp, Pencil, Smartphone, Plus, Pause, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { AddSourceMode } from "./types"
import type { RecordingState } from "@/hooks/useSourceManagement"

const formatRecordingDuration = (seconds: number) => {
  const m = Math.floor(seconds / 60).toString().padStart(2, "0")
  const s = (seconds % 60).toString().padStart(2, "0")
  return `${m}:${s}`
}

interface NewSourceMenuProps {
  addSourceMode: AddSourceMode
  setAddSourceMode: (mode: AddSourceMode) => void
  onNewNote: () => void
  isSavingSource: boolean
  isDragOverUpload: boolean
  recordingState: RecordingState
  recordingSeconds: number
  recordedAudioUrl: string | null
  fileInputRef: React.RefObject<HTMLInputElement | null>
  onAddFileSource: (file: File | null) => Promise<void>
  onFileDrop: (e: React.DragEvent<HTMLDivElement>) => Promise<void>
  onFileDragEnter: (e: React.DragEvent<HTMLDivElement>) => void
  onFileDragOver: (e: React.DragEvent<HTMLDivElement>) => void
  onFileDragLeave: (e: React.DragEvent<HTMLDivElement>) => void
  onStartRecording: () => void
  onPauseRecording: () => void
  onResumeRecording: () => void
  onSaveRecording: () => void
  onCloseRecordingPanel: () => void
  rawUploadUrl: string
}

export function NewSourceMenu({
  addSourceMode,
  setAddSourceMode,
  onNewNote,
  isSavingSource,
  isDragOverUpload,
  recordingState,
  recordingSeconds,
  recordedAudioUrl,
  fileInputRef,
  onAddFileSource,
  onFileDrop,
  onFileDragEnter,
  onFileDragOver,
  onFileDragLeave,
  onStartRecording,
  onPauseRecording,
  onResumeRecording,
  onSaveRecording,
  onCloseRecordingPanel,
  rawUploadUrl,
}: NewSourceMenuProps) {
  const [confirmDiscardOpen, setConfirmDiscardOpen] = useState(false)

  const dialogMode = addSourceMode === "recording" || addSourceMode === "file" || addSourceMode === "phone"
    ? addSourceMode
    : null

  // Closing the recording panel while audio is captured (recording or paused)
  // is destructive, so confirm first. Other panels close freely.
  const handleDialogOpenChange = (open: boolean) => {
    if (open) return
    if (addSourceMode === "recording" && recordingState !== "idle") {
      setConfirmDiscardOpen(true)
    } else {
      setAddSourceMode(null)
    }
  }

  const isRecording = recordingState === "recording"
  // Pausing drops into the review screen: playback + continue + upload.
  const isReviewing = recordingState === "paused"

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button data-tour="new" className="flex items-center gap-1.5 rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 transition-colors">
            <Plus className="h-3.5 w-3.5" />
            New Source
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-44">
          <DropdownMenuItem onSelect={onNewNote} className="gap-2">
            <Pencil className="h-3.5 w-3.5 text-amber-600" />
            Note
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => setAddSourceMode("recording")} className="gap-2">
            <Mic className="h-3.5 w-3.5 text-emerald-600" />
            Record
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => setAddSourceMode("file")} className="gap-2">
            <FileUp className="h-3.5 w-3.5 text-blue-600" />
            Upload file
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => setAddSourceMode("phone")} className="gap-2">
            <Smartphone className="h-3.5 w-3.5 text-fuchsia-600" />
            From phone
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={dialogMode !== null} onOpenChange={handleDialogOpenChange}>
        <DialogContent className="sm:max-w-md">
          {dialogMode === "recording" ? (
            <>
              <DialogHeader>
                <DialogTitle>Voice recording</DialogTitle>
              </DialogHeader>
              <div className="flex flex-col items-center gap-4 py-2">
                {isReviewing ? (
                  <>
                    <audio
                      controls
                      src={recordedAudioUrl ?? undefined}
                      className="w-full"
                    />
                    <span className="text-sm tabular-nums text-muted-foreground">
                      {formatRecordingDuration(recordingSeconds)}
                    </span>
                    <div className="flex items-end gap-8">
                      <div className="flex flex-col items-center gap-1.5">
                        <button
                          onClick={onResumeRecording}
                          disabled={isSavingSource}
                          className="p-4 rounded-full bg-red-500 text-white transition-colors hover:bg-red-600 disabled:opacity-50"
                          title="Continue recording"
                        >
                          <Mic className="h-5 w-5" />
                        </button>
                        <span className="text-xs text-muted-foreground">Continue</span>
                      </div>
                      <div className="flex flex-col items-center gap-1.5">
                        <button
                          onClick={onSaveRecording}
                          disabled={isSavingSource}
                          className="p-4 rounded-full bg-blue-600 text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
                          title="Upload recording"
                        >
                          <Upload className="h-5 w-5" />
                        </button>
                        <span className="text-xs text-muted-foreground">{isSavingSource ? "Uploading..." : "Upload"}</span>
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <button
                      onClick={isRecording ? onPauseRecording : onStartRecording}
                      disabled={isSavingSource}
                      className={`p-5 rounded-full bg-red-500 text-white transition-colors hover:bg-red-600 disabled:opacity-50 ${
                        isRecording ? "animate-pulse" : ""
                      }`}
                      title={isRecording ? "Pause" : "Start recording"}
                    >
                      {isRecording ? <Pause className="h-6 w-6" /> : <Mic className="h-6 w-6" />}
                    </button>
                    {isRecording && (
                      <span className="text-sm tabular-nums text-muted-foreground">{formatRecordingDuration(recordingSeconds)}</span>
                    )}
                    <p className="text-xs text-muted-foreground">
                      {isRecording ? "Recording... tap to pause" : "Tap to start recording"}
                    </p>
                  </>
                )}
              </div>
            </>
          ) : dialogMode === "file" ? (
            <>
              <DialogHeader>
                <DialogTitle>Upload file</DialogTitle>
              </DialogHeader>
              <div
                onDrop={(e) => { void onFileDrop(e) }}
                onDragEnter={onFileDragEnter}
                onDragOver={onFileDragOver}
                onDragLeave={onFileDragLeave}
                className={`border-2 border-dashed rounded-lg p-6 text-center space-y-3 transition-colors ${
                  isDragOverUpload ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20" : "border-border"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept=".wav,.mp3,.m4a,.txt,.md"
                  onChange={(e) => { void onAddFileSource(e.target.files?.[0] ?? null) }}
                />
                <FileUp className="h-7 w-7 mx-auto text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Drag and drop a file here</p>
                <p className="text-xs text-muted-foreground">or</p>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={isSavingSource}
                  onClick={() => fileInputRef.current?.click()}
                >
                  {isSavingSource ? "Uploading..." : "Browse files"}
                </Button>
                <p className="text-xs text-muted-foreground">Allowed: .wav, .mp3, .m4a, .txt, .md</p>
              </div>
            </>
          ) : dialogMode === "phone" ? (
            <>
              <DialogHeader>
                <DialogTitle>Send from phone</DialogTitle>
              </DialogHeader>
              <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
                <div className="mx-auto w-44 h-44 p-2 rounded-md border bg-white">
                  <img
                    src={`https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(rawUploadUrl)}`}
                    alt="QR code to open raw upload on phone"
                    className="w-full h-full"
                  />
                </div>
                <p className="text-xs text-center text-muted-foreground">Scan to open unprocessed upload on your phone</p>
                {(rawUploadUrl.includes("localhost") || rawUploadUrl.includes("127.0.0.1")) && (
                  <p className="text-[11px] text-amber-600 text-center">
                    If your phone cannot open this link, replace localhost with your computer&apos;s LAN IP.
                  </p>
                )}
              </div>
            </>
          ) : null}
        </DialogContent>
      </Dialog>

      <AlertDialog open={confirmDiscardOpen} onOpenChange={setConfirmDiscardOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this recording?</AlertDialogTitle>
            <AlertDialogDescription>
              The audio will not be saved. This can&apos;t be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700"
              onClick={() => {
                setConfirmDiscardOpen(false)
                onCloseRecordingPanel()
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
