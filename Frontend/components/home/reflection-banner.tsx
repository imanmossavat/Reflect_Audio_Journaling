"use client"

import { Sparkles } from "lucide-react"

interface ReflectionBannerProps {
  active: boolean
  onStart: () => void
}

// When a cycle is active the ring, step list and controls live in the right-hand
// GibbsPanel, so this banner only renders the entry point to start a reflection.
export function ReflectionBanner({ active, onStart }: ReflectionBannerProps) {
  if (active) return null

  return (
    <div className="border-b bg-muted/10 px-6 py-2 shrink-0">
      <button
        data-tour="reflect"
        onClick={onStart}
        className="flex items-center gap-2 rounded-md px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
      >
        <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
        Start guided reflection
        <span className="text-muted-foreground/60">(Gibbs cycle)</span>
      </button>
    </div>
  )
}
