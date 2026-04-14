"use client"

import { useEffect, useMemo, useRef, useState } from "react"

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

interface Node {
  id: string
  label: string
  x: number
  y: number
  vx: number
  vy: number
  color: string
  size: number
}

interface Edge {
  source: string
  target: string
  weight: number
}

interface GraphViewProps {
  sources: GraphSource[]
}

const fallbackTypeColors: Record<GraphSource["type"], string> = {
  recording: "#10b981",
  file: "#3b82f6",
  text: "#f59e0b",
}

export function GraphView({ sources }: GraphViewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const nodesRef = useRef<Node[]>([])
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const animationRef = useRef<number | null>(null)
  const hoveredRef = useRef<string | null>(null)

  const graphData = useMemo(() => {
    const nodeMap = new Map<string, { id: string; label: string; color: string; count: number }>()
    const edgeMap = new Map<string, Edge>()

    sources.forEach((source) => {
      const sourceNodeIds = new Set<string>()
      const tags = source.tags.length > 0
        ? source.tags
        : [{ name: source.type, color: fallbackTypeColors[source.type] }]

      tags.forEach((tag) => {
        const nodeId = `node-${tag.name.toLowerCase()}`
        sourceNodeIds.add(nodeId)

        const existingNode = nodeMap.get(nodeId)
        if (existingNode) {
          existingNode.count += 1
          return
        }

        nodeMap.set(nodeId, {
          id: nodeId,
          label: tag.name,
          color: tag.color,
          count: 1,
        })
      })

      const ids = Array.from(sourceNodeIds)
      for (let i = 0; i < ids.length; i++) {
        for (let j = i + 1; j < ids.length; j++) {
          const sourceId = ids[i]
          const targetId = ids[j]
          const edgeKey = sourceId < targetId
            ? `${sourceId}|${targetId}`
            : `${targetId}|${sourceId}`
          const existingEdge = edgeMap.get(edgeKey)

          if (existingEdge) {
            existingEdge.weight += 1
            continue
          }

          edgeMap.set(edgeKey, {
            source: sourceId,
            target: targetId,
            weight: 1,
          })
        }
      }
    })

    const nodes = Array.from(nodeMap.values()).map((node) => ({
      id: node.id,
      label: node.label,
      color: node.color,
      size: Math.min(34, 14 + node.count * 4),
    }))

    return {
      nodes,
      edges: Array.from(edgeMap.values()),
    }
  }, [sources])

  useEffect(() => {
    hoveredRef.current = hoveredNode
  }, [hoveredNode])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height

    if (graphData.nodes.length === 0) {
      nodesRef.current = []
      ctx.clearRect(0, 0, width, height)
      return
    }

    nodesRef.current = graphData.nodes.map((node) => ({
      ...node,
      x: width / 2 + (Math.random() - 0.5) * 100,
      y: height / 2 + (Math.random() - 0.5) * 100,
      vx: 0,
      vy: 0,
    }))

    const simulate = () => {
      const nodes = nodesRef.current

      for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i]
        let fx = 0
        let fy = 0

        fx += (width / 2 - node.x) * 0.001
        fy += (height / 2 - node.y) * 0.001

        for (let j = 0; j < nodes.length; j++) {
          if (i === j) continue
          const other = nodes[j]
          const dx = node.x - other.x
          const dy = node.y - other.y
          const dist = Math.sqrt(dx * dx + dy * dy) || 1
          const force = 500 / (dist * dist)
          fx += (dx / dist) * force
          fy += (dy / dist) * force
        }

        graphData.edges.forEach((edge) => {
          let other: Node | undefined
          if (edge.source === node.id) {
            other = nodes.find((candidate) => candidate.id === edge.target)
          } else if (edge.target === node.id) {
            other = nodes.find((candidate) => candidate.id === edge.source)
          }

          if (other) {
            const dx = other.x - node.x
            const dy = other.y - node.y
            fx += dx * 0.01
            fy += dy * 0.01
          }
        })

        node.vx = (node.vx + fx) * 0.9
        node.vy = (node.vy + fy) * 0.9
        node.x = Math.max(20, Math.min(width - 20, node.x + node.vx))
        node.y = Math.max(20, Math.min(height - 20, node.y + node.vy))
      }
    }

    const draw = () => {
      const nodes = nodesRef.current
      const hovered = hoveredRef.current

      ctx.clearRect(0, 0, width, height)

      ctx.strokeStyle = "rgba(148, 163, 184, 0.3)"
      graphData.edges.forEach((edge) => {
        const source = nodes.find((node) => node.id === edge.source)
        const target = nodes.find((node) => node.id === edge.target)

        if (source && target) {
          ctx.beginPath()
          ctx.lineWidth = 1 + edge.weight * 0.2
          ctx.moveTo(source.x, source.y)
          ctx.lineTo(target.x, target.y)
          ctx.stroke()
        }
      })

      nodes.forEach((node) => {
        const isHovered = node.id === hovered

        ctx.beginPath()
        ctx.arc(node.x, node.y, node.size / 2 + (isHovered ? 2 : 0), 0, Math.PI * 2)
        ctx.fillStyle = node.color
        ctx.fill()

        if (isHovered) {
          ctx.strokeStyle = node.color
          ctx.lineWidth = 2
          ctx.stroke()
        }

        ctx.fillStyle = "#64748b"
        ctx.font = "10px system-ui, sans-serif"
        ctx.textAlign = "center"
        ctx.fillText(node.label, node.x, node.y + node.size / 2 + 12)
      })

      simulate()
      animationRef.current = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [graphData])

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    const nodes = nodesRef.current
    let found: string | null = null
    for (const node of nodes) {
      const dx = x - node.x
      const dy = y - node.y
      if (Math.sqrt(dx * dx + dy * dy) < node.size / 2 + 5) {
        found = node.id
        break
      }
    }

    setHoveredNode(found)
  }

  if (sources.length === 0) {
    return (
      <div className="relative w-full h-64 rounded-lg border bg-background overflow-hidden flex items-center justify-center p-4">
        <p className="text-xs text-muted-foreground text-center">
          Include at least one source to generate a graph.
        </p>
      </div>
    )
  }

  return (
    <div className="relative w-full h-64 rounded-lg border bg-background overflow-hidden">
      <canvas
        ref={canvasRef}
        width={240}
        height={256}
        className="w-full h-full cursor-pointer"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredNode(null)}
      />
      <div className="absolute bottom-2 left-2 right-2">
        <p className="text-[10px] text-muted-foreground text-center">
          Nodes represent included themes, lines show connections
        </p>
      </div>
    </div>
  )
}
