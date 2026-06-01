"use client"

import { ArrowLeft } from "lucide-react"
import Link from "next/link"
import { GraphStage } from "@/components/home/graph-stage"
import { TopNav } from "@/components/top-nav"

export default function GraphPage() {
  return (
    <div className="h-screen bg-background flex flex-col">
      <TopNav activePath="/" />

      <main className="flex-1 min-h-0 flex flex-col">
        <div className="px-8 md:px-12 lg:px-32 pt-8 pb-4 shrink-0">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to home
          </Link>
          <h1 className="text-xl font-semibold mt-2">Graph View</h1>
          <p className="text-sm text-muted-foreground mt-1">Explore direct relationships between your source tags.</p>
        </div>

        <GraphStage mode="fullscreen" />
      </main>
    </div>
  )
}
