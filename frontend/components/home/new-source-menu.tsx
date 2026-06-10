"use client"

import { Mic, FileUp, Pencil, Smartphone, Plus, Pause } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { AddSourceMode } from "./types"

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
  isRecording: boolean
  recordingSeconds: number
  fileInputRef: React.RefObject<HTMLInputElement | null>
  onAddFileSource: (file: File | null) => Promise<void>
  onFileDrop: (e: React.DragEvent<HTMLDivElement>) => Promise<void>
  onFileDragEnter: (e: React.DragEvent<HTMLDivElement>) => void
  onFileDragOver: (e: React.DragEvent<HTMLDivElement>) => void
  onFileDragLeave: (e: React.DragEvent<HTMLDivElement>) => void
  onToggleRecording: () => void
  onCloseRecordingPanel: () => void
  rawUploadUrl: string
}

export function NewSourceMenu({
  addSourceMode,
  setAddSourceMode,
  onNewNote,
  isSavingSource,
  isDragOverUpload,
  isRecording,
  recordingSeconds,
  fileInputRef,
  onAddFileSource,
  onFileDrop,
  onFileDragEnter,
  onFileDragOver,
  onFileDragLeave,
  onToggleRecording,
  onCloseRecordingPanel,
  rawUploadUrl,
}: NewSourceMenuProps) {
  const dialogMode = addSourceMode === "recording" || addSourceMode === "file" || addSourceMode === "phone"
    ? addSourceMode
    : null

  const closeDialog = () => {
    if (addSourceMode === "recording") {
      onCloseRecordingPanel()
    } else {
      setAddSourceMode(null)
    }
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button data-tour="new" className="flex items-center gap-1.5 rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 transition-colors">
            <Plus className="h-3.5 w-3.5" />
            New
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

      <Dialog open={dialogMode !== null} onOpenChange={(open) => { if (!open) closeDialog() }}>
        <DialogContent className="sm:max-w-md">
          {dialogMode === "recording" ? (
            <>
              <DialogHeader>
                <DialogTitle>Voice recording</DialogTitle>
              </DialogHeader>
              <div className="flex flex-col items-center gap-3 py-2">
                <button
                  onClick={onToggleRecording}
                  disabled={isSavingSource}
                  className={`p-4 rounded-full transition-colors disabled:opacity-50 ${
                    isRecording
                      ? "bg-red-500 text-white animate-pulse"
                      : "bg-emerald-500 text-white hover:bg-emerald-600"
                  }`}
                >
                  {isRecording ? <Pause className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
                </button>
                {isRecording && (
                  <span className="text-sm tabular-nums text-muted-foreground">{formatRecordingDuration(recordingSeconds)}</span>
                )}
                {isSavingSource ? (
                  <p className="text-xs text-muted-foreground">Uploading recording...</p>
                ) : isRecording ? (
                  <p className="text-xs text-muted-foreground">Recording... Tap to stop</p>
                ) : (
                  <p className="text-xs text-muted-foreground">Tap to start recording</p>
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
    </>
  )
}
