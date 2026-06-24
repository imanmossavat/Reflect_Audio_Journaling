"use client"

import { useEffect, useState } from "react"
import { Sparkles, Loader2, RefreshCw } from "lucide-react"
import { toast } from "sonner"

import { api } from "@/lib/api"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"

export type EnrichMode = "summary" | "tags"

type Suggestion = { name: string; reason: string }

interface EnrichSourceModalProps {
  sourceId: number | null
  // `null` keeps the modal closed; a mode opens it focused on that one task.
  mode: EnrichMode | null
  sourceName?: string
  // Tags already attached, so we don't re-suggest them.
  attachedTagNames?: string[]
  onOpenChange: (open: boolean) => void
  onSummaryConfirmed?: (sourceId: number) => void
  onTagsConfirmed?: (sourceId: number) => void
}

// A small, focused pop-up for one enrichment task at a time (summary OR tags).
// Generation runs automatically on open — the click that opened it is the intent
// — and nothing is persisted until the user saves the summary / confirms tags.
export function EnrichSourceModal({
  sourceId,
  mode,
  sourceName,
  attachedTagNames = [],
  onOpenChange,
  onSummaryConfirmed,
  onTagsConfirmed,
}: EnrichSourceModalProps) {
  const [summaryDraft, setSummaryDraft] = useState<string | null>(null)
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false)
  const [isSavingSummary, setIsSavingSummary] = useState(false)

  const [suggestions, setSuggestions] = useState<Suggestion[] | null>(null)
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set())
  const [isSuggesting, setIsSuggesting] = useState(false)
  const [isConfirmingTags, setIsConfirmingTags] = useState(false)

  const generateSummary = async () => {
    if (sourceId === null) return
    setIsGeneratingSummary(true)
    try {
      const { summary } = await api.previewSummary(sourceId)
      setSummaryDraft(summary ?? "")
    } catch (err) {
      toast.error(`Could not generate summary: ${err instanceof Error ? err.message : "Unknown error"}`)
    } finally {
      setIsGeneratingSummary(false)
    }
  }

  const generateTags = async () => {
    if (sourceId === null) return
    setIsSuggesting(true)
    try {
      const { suggestions: suggested } = await api.suggestTags(sourceId)
      const attached = new Set(attachedTagNames.map((n) => n.toLowerCase()))
      const fresh = suggested.filter((s) => !attached.has(s.name.toLowerCase()))
      setSuggestions(fresh)
      setSelectedTags(new Set(fresh.map((s) => s.name)))
    } catch (err) {
      toast.error(`Could not suggest tags: ${err instanceof Error ? err.message : "Unknown error"}`)
    } finally {
      setIsSuggesting(false)
    }
  }

  // Reset state and auto-run generation whenever the modal opens (or retargets).
  useEffect(() => {
    if (mode === null || sourceId === null) return
    setSummaryDraft(null)
    setIsSavingSummary(false)
    setSuggestions(null)
    setSelectedTags(new Set())
    setIsConfirmingTags(false)
    if (mode === "summary") void generateSummary()
    else void generateTags()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, sourceId])

  const handleSaveSummary = async () => {
    if (sourceId === null || summaryDraft === null || isSavingSummary) return
    setIsSavingSummary(true)
    try {
      const text = summaryDraft.trim()
      await api.patchSource(sourceId, {
        summary: text,
        summary_html: text ? `<p>${escapeHtml(text)}</p>` : "",
      })
      onSummaryConfirmed?.(sourceId)
      toast.success("Summary saved.")
      onOpenChange(false)
    } catch (err) {
      toast.error(`Could not save summary: ${err instanceof Error ? err.message : "Unknown error"}`)
    } finally {
      setIsSavingSummary(false)
    }
  }

  const toggleTag = (name: string) => {
    setSelectedTags((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  const handleConfirmTags = async () => {
    if (sourceId === null || isConfirmingTags) return
    const names = [...selectedTags]
    if (names.length === 0) return
    setIsConfirmingTags(true)
    try {
      await api.confirmTags(sourceId, names)
      onTagsConfirmed?.(sourceId)
      toast.success(names.length === 1 ? "Tag added." : `${names.length} tags added.`)
      onOpenChange(false)
    } catch (err) {
      toast.error(`Could not add tags: ${err instanceof Error ? err.message : "Unknown error"}`)
    } finally {
      setIsConfirmingTags(false)
    }
  }

  return (
    <Dialog open={mode !== null} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-emerald-600" />
            {mode === "summary" ? "Summary" : "Tags"}
          </DialogTitle>
          <DialogDescription>
            {sourceName ? `For "${sourceName}". ` : ""}
            {mode === "summary"
              ? "Review and edit before saving — nothing is saved until you confirm."
              : "Tick the tags to keep — nothing is added until you confirm."}
          </DialogDescription>
        </DialogHeader>

        {mode === "summary" && (
          <div className="space-y-3">
            {isGeneratingSummary && summaryDraft === null ? (
              <p className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Generating summary...
              </p>
            ) : (
              <>
                <Textarea
                  value={summaryDraft ?? ""}
                  onChange={(e) => setSummaryDraft(e.target.value)}
                  rows={5}
                  placeholder="Edit the summary before saving..."
                  disabled={isGeneratingSummary}
                />
                <div className="flex items-center justify-between gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => void generateSummary()}
                    disabled={isGeneratingSummary || isSavingSummary}
                  >
                    {isGeneratingSummary ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                    Regenerate
                  </Button>
                  <div className="flex gap-2">
                    <Button type="button" size="sm" variant="ghost" onClick={() => onOpenChange(false)} disabled={isSavingSummary}>
                      Discard
                    </Button>
                    <Button type="button" size="sm" onClick={() => void handleSaveSummary()} disabled={isSavingSummary || isGeneratingSummary || !summaryDraft?.trim()}>
                      {isSavingSummary && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                      Save summary
                    </Button>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {mode === "tags" && (
          <div className="space-y-3">
            {isSuggesting && suggestions === null ? (
              <p className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Finding tags...
              </p>
            ) : suggestions && suggestions.length === 0 ? (
              <div className="space-y-3">
                <p className="py-4 text-sm text-muted-foreground">No new tags to suggest.</p>
                <div className="flex justify-end gap-2">
                  <Button type="button" size="sm" variant="ghost" onClick={() => onOpenChange(false)}>Close</Button>
                  <Button type="button" size="sm" variant="outline" onClick={() => void generateTags()} disabled={isSuggesting}>
                    {isSuggesting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                    Suggest again
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <div className="space-y-1.5">
                  {suggestions?.map((s) => (
                    <label
                      key={s.name}
                      className="flex cursor-pointer items-start gap-2 rounded-lg px-2 py-1.5 hover:bg-muted/40"
                    >
                      <Checkbox
                        checked={selectedTags.has(s.name)}
                        onCheckedChange={() => toggleTag(s.name)}
                        className="mt-0.5"
                      />
                      <span className="min-w-0">
                        <span className="text-sm font-medium">{s.name}</span>
                        {s.reason && <span className="block text-xs text-muted-foreground">{s.reason}</span>}
                      </span>
                    </label>
                  ))}
                </div>
                <div className="flex items-center justify-between gap-2">
                  <Button type="button" size="sm" variant="ghost" onClick={() => void generateTags()} disabled={isSuggesting || isConfirmingTags}>
                    {isSuggesting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                    Suggest again
                  </Button>
                  <div className="flex gap-2">
                    <Button type="button" size="sm" variant="ghost" onClick={() => onOpenChange(false)} disabled={isConfirmingTags}>
                      Cancel
                    </Button>
                    <Button type="button" size="sm" onClick={() => void handleConfirmTags()} disabled={isConfirmingTags || selectedTags.size === 0}>
                      {isConfirmingTags && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                      Add selected ({selectedTags.size})
                    </Button>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

const escapeHtml = (value: string) =>
  value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
