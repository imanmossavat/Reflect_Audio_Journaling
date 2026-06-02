"use client"

import { useEffect, useMemo, useState } from "react"
import { GraphView } from "@/components/graph-view"
import { api } from "@/lib/api"

interface GraphSourceTag {
  name: string
  color: string
}

interface GraphSource {
  id: string
  type: "recording" | "file" | "text"
  name: string
  content?: string
  tags: GraphSourceTag[]
}

const tagPalette = ["#0ea5e9", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6", "#f97316"]

const getTagColor = (tagName: string) => {
  let hash = 0
  for (let index = 0; index < tagName.length; index += 1) {
    hash = (hash * 31 + tagName.charCodeAt(index)) >>> 0
  }
  return tagPalette[hash % tagPalette.length]
}

const mapSourceType = (fileType: string | null, filename: string | null): GraphSource["type"] => {
  const normalisedFileType = (fileType ?? "").toLowerCase()
  if (normalisedFileType.includes("audio")) return "recording"
  if (normalisedFileType.includes("text") || !filename) return "text"
  return "file"
}

interface GraphStageProps {
  mode?: "embedded" | "fullscreen"
}

export function GraphStage({ mode = "fullscreen" }: GraphStageProps) {
  const [sources, setSources] = useState<GraphSource[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadGraphSources = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const tagsWithSources = await api.getAllTagsWithSources()
        const sourceMap = new Map<string, GraphSource>()

        tagsWithSources.forEach((tag) => {
          const mappedTag: GraphSourceTag = { name: tag.name, color: getTagColor(tag.name) }
          tag.sources.forEach((source) => {
            const sourceId = String(source.id)
            const existingSource = sourceMap.get(sourceId)
            if (existingSource) {
              existingSource.tags.push(mappedTag)
              return
            }
            sourceMap.set(sourceId, {
              id: sourceId,
              type: mapSourceType(source.file_type, source.filename),
              name: source.filename || "Quick thought",
              tags: [mappedTag],
            })
          })
        })

        setSources(Array.from(sourceMap.values()))
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unknown error")
      } finally {
        setIsLoading(false)
      }
    }

    void loadGraphSources()
  }, [])

  const sourcesWithTags = useMemo(() => sources.filter((source) => source.tags.length > 0), [sources])

  if (isLoading) {
    return (
      <div className="flex-1 min-h-0 w-full flex items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading graph data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex-1 min-h-0 w-full flex items-center justify-center px-6">
        <p className="text-sm text-red-600">Could not load graph data: {error}</p>
      </div>
    )
  }

  if (sourcesWithTags.length === 0) {
    return (
      <div className="flex-1 min-h-0 w-full flex items-center justify-center px-6 text-center">
        <p className="text-sm text-muted-foreground">
          No tagged sources yet. Add tags to your sources to see how they connect.
        </p>
      </div>
    )
  }

  return (
    <div className="flex-1 min-h-0">
      <GraphView sources={sourcesWithTags} mode={mode} />
    </div>
  )
}
