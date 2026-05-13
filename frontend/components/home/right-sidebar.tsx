"use client"

import { FileText, MessageCircle, Sparkles } from "lucide-react"
import Link from "next/link"

interface RightSidebarProps {
  hasIncludedSources: boolean
  isRunningSearch: boolean
  onExportMarkdown: () => void
  onAISearch: () => Promise<void>
}

export function RightSidebar({
  hasIncludedSources,
  isRunningSearch,
  onExportMarkdown,
  onAISearch,
}: RightSidebarProps) {
  return (
    <>
      <div className="border-b px-4 py-3">
        <h2 className="text-sm font-medium">Tools</h2>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto no-scrollbar p-4 space-y-4">
        <div>
          <h3 className="text-sm font-medium mb-3">Export</h3>
          <button
            onClick={onExportMarkdown}
            disabled={!hasIncludedSources}
            className="w-full flex items-center gap-3 p-3 rounded-lg border hover:bg-muted transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FileText className="h-4 w-4 text-muted-foreground" />
            <div>
              <div className="text-sm font-medium">Export to Markdown</div>
              <div className="text-xs text-muted-foreground">Download included sources</div>
            </div>
          </button>
        </div>

        <div>
          <h3 className="text-sm font-medium mb-3">AI Search</h3>
          <button
            onClick={() => void onAISearch()}
            disabled={!hasIncludedSources || isRunningSearch}
            className="w-full flex items-center gap-3 p-3 rounded-lg border hover:bg-muted transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <MessageCircle className="h-4 w-4 text-muted-foreground" />
            <div>
              <div className="text-sm font-medium">{isRunningSearch ? "Searching..." : "Ask about your sources"}</div>
              <div className="text-xs text-muted-foreground">Search included sources only</div>
            </div>
          </button>
        </div>

        <div>
          <h3 className="text-sm font-medium mb-3">Graph</h3>
          <Link
            href="/graph"
            className="w-full flex items-center gap-3 p-3 rounded-lg border hover:bg-muted transition-colors text-left"
          >
            <Sparkles className="h-4 w-4 text-muted-foreground" />
            <div>
              <div className="text-sm font-medium">Open Graph View</div>
              <div className="text-xs text-muted-foreground">Explore source tag relationships</div>
            </div>
          </Link>
        </div>
      </div>
    </>
  )
}
