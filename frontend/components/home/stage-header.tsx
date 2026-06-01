"use client"

import { ArrowLeft, X } from "lucide-react"
import type { ReactNode } from "react"

interface StageHeaderProps {
  title: string
  icon?: ReactNode
  onClose: () => void
  children?: ReactNode
}

export function StageHeader({ title, icon, onClose, children }: StageHeaderProps) {
  return (
    <div className="border-b flex h-12 shrink-0 items-center gap-2 px-3">
      <button
        onClick={onClose}
        aria-label="Back to chat"
        title="Back to chat"
        className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Chat
      </button>
      <div className="mx-1 h-4 w-px bg-border" />
      <div className="flex min-w-0 items-center gap-1.5 text-sm font-medium">
        {icon}
        <span className="truncate">{title}</span>
      </div>
      <div className="ml-auto flex items-center gap-1.5">
        {children}
        <button
          onClick={onClose}
          aria-label="Close"
          title="Close"
          className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
