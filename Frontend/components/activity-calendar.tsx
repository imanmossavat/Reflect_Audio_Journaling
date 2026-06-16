"use client"

import { useMemo, useState, useEffect } from "react"

interface ActivityCalendarProps {
  data: Record<string, number>
  onDateClick?: (date: string) => void
}

export function ActivityCalendar({ data, onDateClick }: ActivityCalendarProps) {
  const [mounted, setMounted] = useState(false)
  
  useEffect(() => {
    setMounted(true)
  }, [])

  const { weeks, months } = useMemo(() => {
    if (!mounted) {
      return { weeks: [], months: [] }
    }
    
    const today = new Date()
    const startDate = new Date(today)
    startDate.setDate(startDate.getDate() - 364)
    
    const dayOfWeek = startDate.getDay()
    startDate.setDate(startDate.getDate() - dayOfWeek)
    
    const weeks: { date: Date; count: number }[][] = []
    const months: { name: string; index: number }[] = []
    let currentWeek: { date: Date; count: number }[] = []
    let lastMonth = -1
    
    const current = new Date(startDate)
    let weekIndex = 0
    
    while (current <= today) {
      const dateStr = current.toISOString().split("T")[0]
      const count = data[dateStr] || 0
      
      if (current.getMonth() !== lastMonth) {
        months.push({
          name: current.toLocaleDateString("en-US", { month: "short" }),
          index: weekIndex,
        })
        lastMonth = current.getMonth()
      }
      
      currentWeek.push({ date: new Date(current), count })
      
      if (currentWeek.length === 7) {
        weeks.push(currentWeek)
        currentWeek = []
        weekIndex++
      }
      
      current.setDate(current.getDate() + 1)
    }
    
    if (currentWeek.length > 0) {
      weeks.push(currentWeek)
    }
    
    return { weeks, months }
  }, [data, mounted])

  // Green color scale like GitHub
  const getIntensity = (count: number) => {
    if (count === 0) return "bg-emerald-50 dark:bg-emerald-950/30"
    if (count === 1) return "bg-emerald-200 dark:bg-emerald-800"
    if (count === 2) return "bg-emerald-400 dark:bg-emerald-600"
    if (count === 3) return "bg-emerald-500 dark:bg-emerald-500"
    return "bg-emerald-600 dark:bg-emerald-400"
  }

  if (!mounted) {
    return (
      <div className="space-y-2">
        <div className="h-4" />
        <div className="flex gap-1">
          <div className="w-6" />
          <div className="h-[84px] flex-1 bg-muted/30 rounded animate-pulse" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {/* Month labels */}
      <div className="flex text-[10px] text-muted-foreground ml-7 gap-0">
        {months.map((month, i) => (
          <div
            key={i}
            className="flex-shrink-0"
            style={{ 
              marginLeft: i === 0 ? 0 : `${Math.max(0, (month.index - (months[i - 1]?.index || 0) - 1) * 11)}px`,
              minWidth: "24px"
            }}
          >
            {month.name}
          </div>
        ))}
      </div>
      
      <div className="flex gap-1">
        {/* Day labels */}
        <div className="flex flex-col gap-[3px] text-[10px] text-muted-foreground pt-0.5">
          <div className="h-[10px]" />
          <div className="h-[10px] flex items-center">M</div>
          <div className="h-[10px]" />
          <div className="h-[10px] flex items-center">W</div>
          <div className="h-[10px]" />
          <div className="h-[10px] flex items-center">F</div>
          <div className="h-[10px]" />
        </div>
        
        {/* Calendar grid */}
        <div className="flex gap-[3px] overflow-x-auto">
          {weeks.map((week, weekIndex) => (
            <div key={weekIndex} className="flex flex-col gap-[3px]">
              {week.map((day, dayIndex) => {
                const dateStr = day.date.toISOString().split("T")[0]
                return (
                  <button
                    key={dayIndex}
                    onClick={() => onDateClick?.(dateStr)}
                    className={`w-[10px] h-[10px] rounded-sm ${getIntensity(day.count)} hover:ring-1 hover:ring-emerald-500 transition-all`}
                    title={`${dateStr}: ${day.count} ${day.count === 1 ? 'entry' : 'entries'}`}
                  />
                )
              })}
            </div>
          ))}
        </div>
      </div>
      
      {/* Legend */}
      <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground justify-end pt-1">
        <span>Less</span>
        <div className="flex gap-[3px]">
          {[0, 1, 2, 3, 4].map((level) => (
            <div
              key={level}
              className={`w-[10px] h-[10px] rounded-sm ${getIntensity(level)}`}
            />
          ))}
        </div>
        <span>More</span>
      </div>
    </div>
  )
}
