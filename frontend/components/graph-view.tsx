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
  mode?: "embedded" | "fullscreen"
}

const DEFAULT_CANVAS_WIDTH = 240
const DEFAULT_CANVAS_HEIGHT = 224
const NODE_REPULSION_FORCE = 760
const NODE_PERSONAL_SPACE = 100
const NODE_COLLISION_PUSH = 0.03
const CENTERING_FORCE = 0.0008
const LINK_FORCE = 0.008

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

export function GraphView({ sources, mode = "embedded" }: GraphViewProps) {
  const isFullscreen = mode === "fullscreen"
  const canvasContainerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const nodesRef = useRef<Node[]>([])
  const previousCanvasSizeRef = useRef<{ width: number; height: number } | null>(null)
  const draggedNodeIdRef = useRef<string | null>(null)
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const [isDraggingNode, setIsDraggingNode] = useState(false)
  const [canvasSize, setCanvasSize] = useState({ width: DEFAULT_CANVAS_WIDTH, height: DEFAULT_CANVAS_HEIGHT })
  const animationRef = useRef<number | null>(null)
  const hoveredRef = useRef<string | null>(null)

  const graphData = useMemo(() => {
    const nodeMap = new Map<string, { id: string; label: string; color: string; count: number }>()
    const edgeMap = new Map<string, Edge>()

    sources.forEach((source) => {
      const sourceNodeIds = new Set<string>()
      const tags = source.tags

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

    const edges = Array.from(edgeMap.values())
    const adjacency = new Map<string, Set<string>>()

    nodes.forEach((node) => {
      adjacency.set(node.id, new Set())
    })

    edges.forEach((edge) => {
      adjacency.get(edge.source)?.add(edge.target)
      adjacency.get(edge.target)?.add(edge.source)
    })

    return {
      nodes,
      edges,
      adjacency,
    }
  }, [sources])

  useEffect(() => {
    hoveredRef.current = hoveredNode
  }, [hoveredNode])

  useEffect(() => {
    const container = canvasContainerRef.current
    if (!container) return

    const updateCanvasSize = () => {
      const rect = container.getBoundingClientRect()
      setCanvasSize({
        width: Math.max(1, Math.floor(rect.width)),
        height: Math.max(1, Math.floor(rect.height)),
      })
    }

    updateCanvasSize()

    const observer = new ResizeObserver(() => {
      updateCanvasSize()
    })
    observer.observe(container)

    return () => {
      observer.disconnect()
    }
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const width = canvasSize.width
    const height = canvasSize.height
    const dpr = window.devicePixelRatio || 1

    canvas.width = Math.floor(width * dpr)
    canvas.height = Math.floor(height * dpr)
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

    if (graphData.nodes.length === 0) {
      nodesRef.current = []
      previousCanvasSizeRef.current = { width, height }
      ctx.clearRect(0, 0, width, height)
      return
    }

    const previousNodes = new Map(nodesRef.current.map((node) => [node.id, node]))
    const previousCanvasSize = previousCanvasSizeRef.current
    const widthScale = previousCanvasSize?.width ? width / previousCanvasSize.width : 1
    const heightScale = previousCanvasSize?.height ? height / previousCanvasSize.height : 1

    nodesRef.current = graphData.nodes.map((node) => {
      const existingNode = previousNodes.get(node.id)
      if (!existingNode) {
        return {
          ...node,
          x: width / 2 + (Math.random() - 0.5) * 100,
          y: height / 2 + (Math.random() - 0.5) * 100,
          vx: 0,
          vy: 0,
        }
      }

      const padding = node.size / 2 + 8
      return {
        ...node,
        x: clamp(existingNode.x * widthScale, padding, width - padding),
        y: clamp(existingNode.y * heightScale, padding, height - padding),
        vx: existingNode.vx,
        vy: existingNode.vy,
      }
    })

    previousCanvasSizeRef.current = { width, height }

    const simulate = () => {
      const nodes = nodesRef.current
      const draggedNodeId = draggedNodeIdRef.current

      for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i]
        if (node.id === draggedNodeId) {
          node.vx = 0
          node.vy = 0
          continue
        }

        let fx = 0
        let fy = 0

        fx += (width / 2 - node.x) * CENTERING_FORCE
        fy += (height / 2 - node.y) * CENTERING_FORCE

        for (let j = 0; j < nodes.length; j++) {
          if (i === j) continue
          const other = nodes[j]
          const dx = node.x - other.x
          const dy = node.y - other.y
          const dist = Math.sqrt(dx * dx + dy * dy) || 0.001
          const force = NODE_REPULSION_FORCE / (dist * dist)
          fx += (dx / dist) * force
          fy += (dy / dist) * force

          const preferredDistance = node.size / 2 + other.size / 2 + NODE_PERSONAL_SPACE
          if (dist < preferredDistance) {
            const overlapPush = (preferredDistance - dist) * NODE_COLLISION_PUSH
            fx += (dx / dist) * overlapPush
            fy += (dy / dist) * overlapPush
          }
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
            fx += dx * LINK_FORCE
            fy += dy * LINK_FORCE
          }
        })

        node.vx = (node.vx + fx) * 0.9
        node.vy = (node.vy + fy) * 0.9
        const padding = node.size / 2 + 8
        node.x = clamp(node.x + node.vx, padding, width - padding)
        node.y = clamp(node.y + node.vy, padding, height - padding)
      }
    }

    const draw = () => {
      const nodes = nodesRef.current
      const hovered = hoveredRef.current
      const nodeById = new Map(nodes.map((node) => [node.id, node]))
      const connectedToHovered = hovered ? graphData.adjacency.get(hovered) ?? new Set<string>() : null
      const hoveredColor = hovered ? nodeById.get(hovered)?.color ?? "#22c55e" : null

      ctx.clearRect(0, 0, width, height)

      graphData.edges.forEach((edge) => {
        const source = nodeById.get(edge.source)
        const target = nodeById.get(edge.target)

        if (source && target) {
          const isDirectHoveredEdge = Boolean(hovered && (edge.source === hovered || edge.target === hovered))
          const dx = target.x - source.x
          const dy = target.y - source.y
          const dist = Math.sqrt(dx * dx + dy * dy) || 1
          const directionX = dx / dist
          const directionY = dy / dist
          const startOffset = source.size / 2 + 1
          const endOffset = target.size / 2 + 1
          const startX = source.x + directionX * startOffset
          const startY = source.y + directionY * startOffset
          const endX = target.x - directionX * endOffset
          const endY = target.y - directionY * endOffset

          ctx.beginPath()
          if (!hovered) {
            ctx.strokeStyle = "rgba(148, 163, 184, 0.3)"
            ctx.lineWidth = 1 + edge.weight * 0.2
          } else if (isDirectHoveredEdge) {
            ctx.strokeStyle = hoveredColor ?? "rgba(16, 185, 129, 0.9)"
            ctx.lineWidth = 1.4 + edge.weight * 0.35
          } else {
            ctx.strokeStyle = "rgba(148, 163, 184, 0.1)"
            ctx.lineWidth = 0.8 + edge.weight * 0.1
          }
          ctx.moveTo(startX, startY)
          ctx.lineTo(endX, endY)
          ctx.stroke()
        }
      })

      nodes.forEach((node) => {
        const isHovered = node.id === hovered
        const isDirectlyConnected = Boolean(hovered && connectedToHovered?.has(node.id))
        const isDimmed = Boolean(hovered && !isHovered && !isDirectlyConnected)

        const nodeFillColor = isHovered
          ? node.color
          : isDimmed
            ? "rgba(148, 163, 184, 0.22)"
            : "rgba(148, 163, 184, 0.9)"

        const labelColor = isHovered
          ? "rgba(30, 41, 59, 0.95)"
          : isDimmed
            ? "rgba(100, 116, 139, 0.35)"
            : "rgba(100, 116, 139, 0.9)"

        ctx.beginPath()
        ctx.arc(node.x, node.y, node.size / 2 + (isHovered ? 2 : 0), 0, Math.PI * 2)
        ctx.fillStyle = nodeFillColor
        ctx.fill()

        if (isHovered) {
          ctx.strokeStyle = node.color
          ctx.lineWidth = 2
          ctx.stroke()
        }

        ctx.fillStyle = labelColor
        ctx.font = "10px system-ui, sans-serif"
        ctx.textAlign = "center"
        ctx.fillText(node.label, node.x, node.y - node.size / 2 - 6)
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
  }, [canvasSize, graphData])

  useEffect(() => {
    const handleWindowMouseUp = () => {
      draggedNodeIdRef.current = null
      setIsDraggingNode(false)
    }

    window.addEventListener("mouseup", handleWindowMouseUp)

    return () => {
      window.removeEventListener("mouseup", handleWindowMouseUp)
    }
  }, [])

  const getCanvasPoint = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return null

    const rect = canvas.getBoundingClientRect()
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    }
  }

  const getNodeAtPoint = (x: number, y: number) => {
    const nodes = nodesRef.current
    for (let index = nodes.length - 1; index >= 0; index -= 1) {
      const node = nodes[index]
      const dx = x - node.x
      const dy = y - node.y
      if (Math.sqrt(dx * dx + dy * dy) < node.size / 2 + 6) {
        return node
      }
    }
    return null
  }

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const point = getCanvasPoint(e)
    if (!point) return

    const node = getNodeAtPoint(point.x, point.y)
    if (!node) return

    draggedNodeIdRef.current = node.id
    node.vx = 0
    node.vy = 0
    setIsDraggingNode(true)
    setHoveredNode(node.id)
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const point = getCanvasPoint(e)
    if (!point) return

    const draggedNodeId = draggedNodeIdRef.current
    if (draggedNodeId) {
      const node = nodesRef.current.find((candidate) => candidate.id === draggedNodeId)
      if (!node) return

      const padding = node.size / 2 + 8
      node.x = clamp(point.x, padding, canvasSize.width - padding)
      node.y = clamp(point.y, padding, canvasSize.height - padding)
      node.vx = 0
      node.vy = 0
      setHoveredNode(node.id)
      return
    }

    const foundNode = getNodeAtPoint(point.x, point.y)
    setHoveredNode(foundNode?.id ?? null)
  }

  const handleMouseUp = () => {
    draggedNodeIdRef.current = null
    setIsDraggingNode(false)
  }

  if (sources.length === 0) {
    return (
      <div
        className={
          isFullscreen
            ? "relative w-full h-full bg-background overflow-hidden flex items-center justify-center p-4"
            : "relative w-full h-64 rounded-lg border bg-background overflow-hidden flex items-center justify-center p-4"
        }
      >
        <p className="text-xs text-muted-foreground text-center">
          Include at least one source to generate a graph.
        </p>
      </div>
    )
  }

  if (isFullscreen) {
    return (
      <div className="w-full h-full bg-background overflow-hidden">
        <div ref={canvasContainerRef} className="w-full h-full">
          <canvas
            ref={canvasRef}
            className={`w-full h-full ${isDraggingNode ? "cursor-grabbing" : "cursor-grab"}`}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={() => {
              setHoveredNode(null)
              handleMouseUp()
            }}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="w-full rounded-lg border bg-background overflow-hidden">
      <div className="border-b px-3 py-2">
        <p className="text-[10px] text-muted-foreground text-center">
          Nodes represent included themes, lines show connections. Drag nodes to explore.
        </p>
      </div>
      <div ref={canvasContainerRef} className="w-full h-56">
        <canvas
          ref={canvasRef}
          className={`w-full h-full ${isDraggingNode ? "cursor-grabbing" : "cursor-grab"}`}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={() => {
            setHoveredNode(null)
            handleMouseUp()
          }}
        />
      </div>
    </div>
  )
}
