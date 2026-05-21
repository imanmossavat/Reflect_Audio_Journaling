"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import {EllipsisVerticalIcon, Mic, FileUp, Pencil, Trash2, Type, Play, Pause, Search, Smartphone, X, File as FileIcon } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Skeleton } from "@/components/ui/skeleton"
import { PROCESSING_STATUSES, PROCESSING_STATUS_LABELS, OLLAMA_FAILURE_STATUSES } from "@/lib/api"
import type { RawSource, AddSourceMode } from "./types"

const formatRecordingDuration = (seconds: number) => {
  const m = Math.floor(seconds / 60).toString().padStart(2, "0")
  const s = (seconds % 60).toString().padStart(2, "0")
  return `${m}:${s}`
}

interface SourceListPanelProps {
  rawSources: RawSource[]
  includedSources: RawSource[]
  isLoadingSources: boolean
  addSourceMode: AddSourceMode
  setAddSourceMode: (mode: AddSourceMode) => void
  newSourceText: string
  setNewSourceText: (text: string) => void
  isSavingSource: boolean
  isDragOverUpload: boolean
  isRecording: boolean
  recordingSeconds: number
  fileInputRef: React.RefObject<HTMLInputElement | null>
  tagFilter: string[]
  onToggleTagFilter: (tag: string) => void
  onSetSourceIncluded: (id: string, included: boolean) => void
  onAddTextSource: () => void
  onAddFileSource: (file: File | null) => Promise<void>
  onFileDrop: (e: React.DragEvent<HTMLDivElement>) => Promise<void>
  onFileDragEnter: (e: React.DragEvent<HTMLDivElement>) => void
  onFileDragOver: (e: React.DragEvent<HTMLDivElement>) => void
  onFileDragLeave: (e: React.DragEvent<HTMLDivElement>) => void
  onToggleRecording: () => void
  onCloseRecordingPanel: () => void
  rawUploadUrl: string
  onDeleteSource: (id: string) => Promise<void>
  onRenameSource: (id: string, name: string) => Promise<void>
}

export function SourceListPanel({
  rawSources,
  includedSources,
  isLoadingSources,
  addSourceMode,
  setAddSourceMode,
  newSourceText,
  setNewSourceText,
  isSavingSource,
  isDragOverUpload,
  isRecording,
  recordingSeconds,
  fileInputRef,
  tagFilter,
  onToggleTagFilter,
  onSetSourceIncluded,
  onAddTextSource,
  onAddFileSource,
  onFileDrop,
  onFileDragEnter,
  onFileDragOver,
  onFileDragLeave,
  onToggleRecording,
  onCloseRecordingPanel,
  rawUploadUrl,
  onDeleteSource,
  onRenameSource,
}: SourceListPanelProps) {
  const [renamingSourceId, setRenamingSourceId] = useState<string | null>(null)
  const [renameDraft, setRenameDraft] = useState("")
  const renameInputRef = useRef<HTMLInputElement>(null)

  const commitRename = async (sourceId: string) => {
    const trimmed = renameDraft.trim()
    if (trimmed) await onRenameSource(sourceId, trimmed)
    setRenamingSourceId(null)
  }

  const allTags = useMemo(() => {
    const tagSet = new Set<string>()
    rawSources.forEach((s) => s.tags.forEach((t) => tagSet.add(t.name)))
    return Array.from(tagSet).sort()
  }, [rawSources])

  const [searchQuery, setSearchQuery] = useState("")
  const [isSearchFocused, setIsSearchFocused] = useState(false)
  const searchInputRef = useRef<HTMLInputElement>(null)
  const [tagAutocompleteIndex, setTagAutocompleteIndex] = useState(0)

  const tagSearchMatch = useMemo(() => {
    const m = searchQuery.match(/^\s*tag:\s*(?:"([^"]*)"?|(\S*))\s*$/i)
    if (!m) return null
    return (m[1] ?? m[2] ?? "").toLowerCase()
  }, [searchQuery])

  const tagSuggestions = useMemo(() => {
    if (tagSearchMatch === null) return []
    return allTags.filter(
      (t) => !tagFilter.includes(t) && t.toLowerCase().includes(tagSearchMatch)
    )
  }, [allTags, tagFilter, tagSearchMatch])

  useEffect(() => {
    setTagAutocompleteIndex(0)
  }, [searchQuery])

  const titleSearchTerm = tagSearchMatch === null ? searchQuery.trim().toLowerCase() : ""

  const filteredSources = useMemo(() => {
    return rawSources.filter((source) => {
      if (tagFilter.length > 0 && !tagFilter.every((tag) => source.tags.some((t) => t.name === tag))) {
        return false
      }
      if (titleSearchTerm && !source.name.toLowerCase().includes(titleSearchTerm)) {
        return false
      }
      return true
    })
  }, [rawSources, tagFilter, titleSearchTerm])

  const selectableSources = useMemo(
    () => filteredSources.filter((s) => !PROCESSING_STATUSES.has(s.status) && s.status !== "failed" && !OLLAMA_FAILURE_STATUSES.has(s.status)),
    [filteredSources],
  )
  const allSelected = selectableSources.length > 0 && selectableSources.every((s) => s.included)
  const handleToggleSelectAll = () => {
    const target = !allSelected
    selectableSources.forEach((s) => {
      if (s.included !== target) onSetSourceIncluded(s.id, target)
    })
  }

  const acceptTagSuggestion = (tag: string) => {
    onToggleTagFilter(tag)
    setSearchQuery("")
    searchInputRef.current?.blur()
  }

  return (
    <>
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium">Add Sources</h2>
        </div>

        {!addSourceMode ? (
          <div className="grid grid-cols-4 gap-1.5">
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
            <button
              onClick={() => setAddSourceMode("phone")}
              className="flex flex-col items-center gap-1 p-2 rounded-lg border border-dashed border-border hover:border-fuchsia-500 hover:bg-fuchsia-50 dark:hover:bg-fuchsia-900/20 transition-colors"
            >
              <Smartphone className="h-4 w-4 text-muted-foreground" />
              <span className="text-[10px] text-muted-foreground">Phone</span>
            </button>
          </div>
        ) : addSourceMode === "recording" ? (
          <div className="p-3 rounded-lg border bg-background space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium">Voice recording</span>
              <button
                onClick={onCloseRecordingPanel}
                className="p-1 rounded hover:bg-muted"
                disabled={isSavingSource}
              >
                <X className="h-3 w-3" />
              </button>
            </div>
            <div className="flex flex-col items-center gap-2">
              <button
                onClick={onToggleRecording}
                disabled={isSavingSource}
                className={`p-3 rounded-full transition-colors disabled:opacity-50 ${
                  isRecording
                    ? "bg-red-500 text-white animate-pulse"
                    : "bg-emerald-500 text-white hover:bg-emerald-600"
                }`}
              >
                {isRecording ? <Pause className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
              </button>
              {isRecording && (
                <span className="text-xs tabular-nums text-muted-foreground">{formatRecordingDuration(recordingSeconds)}</span>
              )}
            </div>
            {isSavingSource && (
              <p className="text-xs text-center text-muted-foreground">Uploading recording...</p>
            )}
            {!isRecording && !isSavingSource && (
              <p className="text-xs text-center text-muted-foreground">Tap to start recording</p>
            )}
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
              onClick={onAddTextSource}
              disabled={!newSourceText.trim() || isSavingSource}
              size="sm"
              className="w-full bg-emerald-600 hover:bg-emerald-700"
            >
              {isSavingSource ? "Saving..." : "Add + Process"}
            </Button>
          </div>
        ) : addSourceMode === "file" ? (
          <div className="p-3 rounded-lg border bg-background space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium">Upload file</span>
              <button
                onClick={() => setAddSourceMode(null)}
                className="p-1 rounded hover:bg-muted"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
            <div
              onDrop={(e) => { void onFileDrop(e) }}
              onDragEnter={onFileDragEnter}
              onDragOver={onFileDragOver}
              onDragLeave={onFileDragLeave}
              className={`border-2 border-dashed rounded-lg p-4 text-center space-y-3 transition-colors ${
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
              <FileUp className="h-6 w-6 mx-auto text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Drag and drop a file here</p>
              <p className="text-[10px] text-muted-foreground">or</p>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={isSavingSource}
                onClick={() => fileInputRef.current?.click()}
              >
                {isSavingSource ? "Uploading..." : "Browse files"}
              </Button>
              <p className="text-[10px] text-muted-foreground">Allowed: .wav, .mp3, .m4a, .txt, .md</p>
            </div>
          </div>
        ) : addSourceMode === "phone" ? (
          <div className="p-3 rounded-lg border bg-background space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium">Send from phone</span>
              <button onClick={() => setAddSourceMode(null)} className="p-1 rounded hover:bg-muted">
                <X className="h-3 w-3" />
              </button>
            </div>
            <div className="rounded-lg border bg-muted/30 p-3 space-y-3">
              <div className="mx-auto w-40 h-40 p-2 rounded-md border bg-white">
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(rawUploadUrl)}`}
                  alt="QR code to open raw upload on phone"
                  className="w-full h-full"
                />
              </div>
              <p className="text-xs text-center text-muted-foreground">Scan to open unprocessed upload on your phone</p>
              {(rawUploadUrl.includes("localhost") || rawUploadUrl.includes("127.0.0.1")) && (
                <p className="text-[10px] text-amber-600 text-center">
                  If your phone cannot open this link, replace localhost with your computer&apos;s LAN IP.
                </p>
              )}
            </div>
          </div>
        ) : null}
      </div>

      <div className="px-3 py-2 border-b space-y-1.5">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground pointer-events-none" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setIsSearchFocused(true)}
            onBlur={() => setIsSearchFocused(false)}
            onKeyDown={(e) => {
              if (tagSearchMatch !== null && tagSuggestions.length > 0) {
                if (e.key === "ArrowDown") {
                  e.preventDefault()
                  setTagAutocompleteIndex((i) => (i + 1) % tagSuggestions.length)
                } else if (e.key === "ArrowUp") {
                  e.preventDefault()
                  setTagAutocompleteIndex((i) => (i - 1 + tagSuggestions.length) % tagSuggestions.length)
                } else if (e.key === "Enter" || e.key === "Tab") {
                  e.preventDefault()
                  acceptTagSuggestion(tagSuggestions[tagAutocompleteIndex])
                } else if (e.key === "Escape") {
                  setSearchQuery("")
                }
              } else if (e.key === "Escape") {
                setSearchQuery("")
              }
            }}
            placeholder="Search title..."
            className="w-full pl-7 pr-7 py-1 text-xs rounded border bg-background focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-muted text-muted-foreground"
              aria-label="Clear search"
            >
              <X className="h-3 w-3" />
            </button>
          )}
          {tagSearchMatch !== null && tagSuggestions.length > 0 ? (
            <div className="absolute z-20 left-0 right-0 top-full mt-1 rounded-md border bg-popover shadow-md p-1 max-h-48 overflow-y-auto">
              {tagSuggestions.map((tag, idx) => (
                <button
                  key={tag}
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault()
                    acceptTagSuggestion(tag)
                  }}
                  onMouseEnter={() => setTagAutocompleteIndex(idx)}
                  className={`w-full flex items-center gap-2 px-2 py-1 text-xs rounded text-left ${
                    idx === tagAutocompleteIndex ? "bg-muted" : "hover:bg-muted"
                  }`}
                >
                  <span className="text-[10px] text-muted-foreground">tag:</span>
                  <span className="truncate">{tag}</span>
                </button>
              ))}
            </div>
          ) : isSearchFocused && searchQuery.length === 0 && allTags.length > 0 ? (
            <div className="absolute z-20 left-0 right-0 top-full mt-1 rounded-md border bg-popover shadow-md p-1">
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault()
                  setSearchQuery("tag:")
                  searchInputRef.current?.focus()
                }}
                className="w-full flex items-center gap-2 px-2 py-1 text-xs rounded text-left hover:bg-muted"
              >
                <span className="text-[10px] text-muted-foreground">tag:</span>
                <span className="text-muted-foreground">filter by tag</span>
              </button>
            </div>
          ) : null}
        </div>
        {tagFilter.length > 0 && (
          <div className="flex flex-wrap items-center gap-1">
            {tagFilter.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => onToggleTagFilter(tag)}
                className="inline-flex items-center gap-0.5 text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-300 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-700 transition-colors hover:bg-emerald-200"
              >
                {tag}
                <X className="h-2.5 w-2.5 ml-0.5" />
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto no-scrollbar p-2 space-y-1">
        <div className="flex items-center justify-between px-2.5 pb-1">
          <span className="text-xs text-muted-foreground">{includedSources.length}/{rawSources.length}</span>
          {selectableSources.length > 0 && (
            <label className="flex items-center gap-1.5 text-[12px] text-muted-foreground cursor-pointer select-none">
              <span>{allSelected ? "Deselect all" : "Select all"}</span>
              <Checkbox
                checked={allSelected}
                onCheckedChange={handleToggleSelectAll}
                aria-label={allSelected ? "Deselect all sources" : "Select all sources"}
              />
            </label>
          )}
        </div>
        {isLoadingSources ? (
          Array.from({ length: 3 }).map((_, index) => (
            <div key={`source-skeleton-${index}`} className="p-2.5 rounded-lg bg-background/40">
              <div className="flex items-start gap-2.5">
                <Skeleton className="h-6 w-6 rounded-md shrink-0" />
                <div className="flex-1 min-w-0">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-3 w-36 mt-0.5" />
                  <div className="flex items-center gap-2 mt-1">
                    <Skeleton className="h-2.5 w-16" />
                    <Skeleton className="h-2.5 w-10 rounded-full" />
                  </div>
                </div>
                <Skeleton className="h-4 w-4 rounded self-center shrink-0" />
              </div>
            </div>
          ))
        ) : filteredSources.length === 0 && (tagFilter.length > 0 || titleSearchTerm) ? (
          <p className="text-xs text-muted-foreground px-2 py-4 text-center">No sources match the current filter.</p>
        ) : (
          filteredSources.map((source) => {
            const isInProgress = PROCESSING_STATUSES.has(source.status)
            const isFailed = source.status === "failed"
            const isOllamaFailure = OLLAMA_FAILURE_STATUSES.has(source.status)
            const isAnyFailure = isFailed || isOllamaFailure
            return (
              <div
                key={source.id}
                className={`p-2.5 rounded-lg transition-all group ${
                  isInProgress
                    ? "border border-emerald-400/50 bg-emerald-50/40 dark:bg-emerald-900/10"
                    : isAnyFailure
                      ? "border border-red-200 bg-red-50/30 dark:bg-red-900/10 opacity-70"
                      : `hover:bg-muted/50 ${source.included ? "" : "opacity-60"}`
                }`}
              >
                <div className="flex items-start gap-2.5">
                  <div className={`p-1.5 rounded-md shrink-0 ${
                    isInProgress
                      ? "bg-emerald-100 dark:bg-emerald-900/40 animate-pulse"
                      : source.type === "recording"
                        ? "bg-emerald-100 dark:bg-emerald-900/30"
                        : source.type === "file"
                          ? "bg-blue-100 dark:bg-blue-900/30"
                          : "bg-amber-100 dark:bg-amber-900/30"
                  }`}>
                    {source.type === "recording" ? (
                      <Mic className={`h-3 w-3 ${isInProgress ? "text-emerald-500" : "text-emerald-600"}`} />
                    ) : source.type === "file" ? (
                      <FileIcon className="h-3 w-3 text-blue-600" />
                    ) : (
                      <Type className="h-3 w-3 text-amber-600" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    {renamingSourceId === source.id ? (
                      <input
                        ref={renameInputRef}
                        autoFocus
                        value={renameDraft}
                        onChange={(e) => setRenameDraft(e.target.value)}
                        onBlur={() => void commitRename(source.id)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") void commitRename(source.id)
                          else if (e.key === "Escape") setRenamingSourceId(null)
                        }}
                        onClick={(e) => e.stopPropagation()}
                        className="w-full text-sm font-medium bg-background border rounded px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                      />
                    ) : (
                      <Link
                        href={`/sources/${source.id}`}
                        className="block rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium truncate">{source.name}</span>
                        </div>
                        {isInProgress ? (
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <span className="flex gap-0.5">
                              <span className="inline-block w-1 h-1 rounded-full bg-emerald-500 animate-bounce [animation-delay:0ms]" />
                              <span className="inline-block w-1 h-1 rounded-full bg-emerald-500 animate-bounce [animation-delay:150ms]" />
                              <span className="inline-block w-1 h-1 rounded-full bg-emerald-500 animate-bounce [animation-delay:300ms]" />
                            </span>
                            <span className="text-xs text-emerald-600">
                              {PROCESSING_STATUS_LABELS[source.status] ?? "Processing..."}
                            </span>
                          </div>
                        ) : isOllamaFailure ? (
                          <div className="mt-0.5">
                            <p className="text-xs text-orange-500 font-medium">
                              {source.status === "failed_ollama_not_installed"
                                ? "Ollama not installed"
                                : "Ollama not running"}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {source.status === "failed_ollama_not_installed"
                                ? "Install Ollama to enable indexing"
                                : "Start Ollama, then reprocess"}
                            </p>
                          </div>
                        ) : isFailed ? (
                          <p className="text-xs text-red-500 mt-0.5">Processing failed</p>
                        ) : (
                          <>
                            {source.type === "recording" && (
                              <div className="flex items-center gap-2 mt-0.5">
                                <Play className="h-3 w-3 text-muted-foreground" />
                                <span className="text-xs text-muted-foreground">{source.duration}</span>
                              </div>
                            )}
                            {source.type === "text" && source.content && (
                              <p className="text-xs text-muted-foreground truncate mt-0.5">{source.content}</p>
                            )}
                          </>
                        )}
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-[10px] text-muted-foreground">{source.timestamp}</span>
                          {source.tags.map((tag) => (
                            <span key={tag.name} className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted">
                              {tag.name}
                            </span>
                          ))}
                        </div>
                      </Link>
                    )}
                  </div>
                  <div className="flex items-center gap-1 self-center shrink-0">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button
                          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-muted text-muted-foreground transition-opacity"
                          aria-label="Source options"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <EllipsisVerticalIcon className="h-3.5 w-3.5" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-36">
                        <DropdownMenuItem
                          onSelect={() => {
                            setRenameDraft(source.name)
                            setRenamingSourceId(source.id)
                          }}
                          className="gap-2"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                          Rename
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onSelect={() => void onDeleteSource(source.id)}
                          className="gap-2 text-destructive focus:text-destructive"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                    <Checkbox
                      checked={source.included}
                      onCheckedChange={(checked) => onSetSourceIncluded(source.id, checked === true)}
                      aria-label={`Include ${source.name}`}
                      disabled={isInProgress}
                    />
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </>
  )
}
