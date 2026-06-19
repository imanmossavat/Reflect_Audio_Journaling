"use client"

import { useEffect, useRef, useState } from "react"

const LEFT_SIDEBAR_DEFAULT_WIDTH = 384
const LEFT_SIDEBAR_MIN_WIDTH = 300
const LEFT_SIDEBAR_MAX_WIDTH = 560
const RIGHT_SIDEBAR_DEFAULT_WIDTH = 256
const RIGHT_SIDEBAR_MIN_WIDTH = 220
const RIGHT_SIDEBAR_MAX_WIDTH = 420
const leftSidebarWidthStorageKey = "reflect_left_sidebar_width"
const rightSidebarWidthStorageKey = "reflect_right_sidebar_width"
const leftSidebarCollapsedStorageKey = "reflect_left_sidebar_collapsed"
const rightSidebarCollapsedStorageKey = "reflect_right_sidebar_collapsed"

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

export function useSidebarResize() {
  const [leftSidebarWidth, setLeftSidebarWidth] = useState(LEFT_SIDEBAR_DEFAULT_WIDTH)
  const [rightSidebarWidth, setRightSidebarWidth] = useState(RIGHT_SIDEBAR_DEFAULT_WIDTH)
  const [isLeftCollapsed, setIsLeftCollapsed] = useState(false)
  const [isRightCollapsed, setIsRightCollapsed] = useState(false)
  const [isResizingSidebar, setIsResizingSidebar] = useState<"left" | "right" | null>(null)
  const resizeStartRef = useRef<{ startX: number; startWidth: number } | null>(null)
  const leftSidebarWidthRef = useRef(LEFT_SIDEBAR_DEFAULT_WIDTH)
  const rightSidebarWidthRef = useRef(RIGHT_SIDEBAR_DEFAULT_WIDTH)

  useEffect(() => {
    if (typeof window === "undefined") return
    const savedLeft = Number(window.localStorage.getItem(leftSidebarWidthStorageKey))
    const savedRight = Number(window.localStorage.getItem(rightSidebarWidthStorageKey))
    if (Number.isFinite(savedLeft) && savedLeft > 0)
      setLeftSidebarWidth(clamp(savedLeft, LEFT_SIDEBAR_MIN_WIDTH, LEFT_SIDEBAR_MAX_WIDTH))
    if (Number.isFinite(savedRight) && savedRight > 0)
      setRightSidebarWidth(clamp(savedRight, RIGHT_SIDEBAR_MIN_WIDTH, RIGHT_SIDEBAR_MAX_WIDTH))
    setIsLeftCollapsed(window.localStorage.getItem(leftSidebarCollapsedStorageKey) === "true")
    setIsRightCollapsed(window.localStorage.getItem(rightSidebarCollapsedStorageKey) === "true")
  }, [])

  useEffect(() => {
    if (!isResizingSidebar || !resizeStartRef.current) return

    const handleMouseMove = (event: MouseEvent) => {
      const resizeStart = resizeStartRef.current
      if (!resizeStart) return
      const deltaX = event.clientX - resizeStart.startX
      if (isResizingSidebar === "left") {
        const next = clamp(resizeStart.startWidth + deltaX, LEFT_SIDEBAR_MIN_WIDTH, LEFT_SIDEBAR_MAX_WIDTH)
        leftSidebarWidthRef.current = next
        setLeftSidebarWidth(next)
      } else {
        const next = clamp(resizeStart.startWidth - deltaX, RIGHT_SIDEBAR_MIN_WIDTH, RIGHT_SIDEBAR_MAX_WIDTH)
        rightSidebarWidthRef.current = next
        setRightSidebarWidth(next)
      }
    }

    const handleMouseUp = () => {
      setIsResizingSidebar(null)
      resizeStartRef.current = null
      if (typeof window !== "undefined") {
        window.localStorage.setItem(leftSidebarWidthStorageKey, String(leftSidebarWidthRef.current))
        window.localStorage.setItem(rightSidebarWidthStorageKey, String(rightSidebarWidthRef.current))
      }
    }

    document.body.style.cursor = "col-resize"
    document.body.style.userSelect = "none"
    window.addEventListener("mousemove", handleMouseMove)
    window.addEventListener("mouseup", handleMouseUp)

    return () => {
      document.body.style.cursor = ""
      document.body.style.userSelect = ""
      window.removeEventListener("mousemove", handleMouseMove)
      window.removeEventListener("mouseup", handleMouseUp)
    }
  }, [isResizingSidebar])

  useEffect(() => { leftSidebarWidthRef.current = leftSidebarWidth }, [leftSidebarWidth])
  useEffect(() => { rightSidebarWidthRef.current = rightSidebarWidth }, [rightSidebarWidth])

  const handleSidebarResizeStart = (side: "left" | "right", event: React.MouseEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsResizingSidebar(side)
    resizeStartRef.current = {
      startX: event.clientX,
      startWidth: side === "left" ? leftSidebarWidth : rightSidebarWidth,
    }
  }

  const toggleLeftCollapsed = () => {
    setIsLeftCollapsed((prev) => {
      const next = !prev
      if (typeof window !== "undefined")
        window.localStorage.setItem(leftSidebarCollapsedStorageKey, String(next))
      return next
    })
  }

  const toggleRightCollapsed = () => {
    setIsRightCollapsed((prev) => {
      const next = !prev
      if (typeof window !== "undefined")
        window.localStorage.setItem(rightSidebarCollapsedStorageKey, String(next))
      return next
    })
  }

  // Force the right panel open (used when a feature needs to surface there, e.g. the
  // guided-reflection panel on start). No-op if it's already expanded.
  const openRight = () => {
    setIsRightCollapsed(false)
    if (typeof window !== "undefined")
      window.localStorage.setItem(rightSidebarCollapsedStorageKey, "false")
  }

  return {
    leftSidebarWidth,
    rightSidebarWidth,
    isLeftCollapsed,
    isRightCollapsed,
    toggleLeftCollapsed,
    toggleRightCollapsed,
    openRight,
    handleSidebarResizeStart,
  }
}
