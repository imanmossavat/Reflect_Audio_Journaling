"use client"

import { GIBBS_STEPS, getGibbsStep } from "@/lib/gibbs"

interface GibbsWheelProps {
  /** The stage currently in focus (1-6). */
  currentStep: number
  /** Optional: make segments clickable to revisit a stage. */
  onSelectStep?: (step: number) => void
  /** Pixel size of the wheel. Defaults to 120. */
  size?: number
}

const CENTER = 50
const R_OUTER = 46
const R_INNER = 29
const GAP_DEG = 5

function polar(angleDeg: number, radius: number) {
  // -90 so 0° sits at the top of the circle.
  const a = ((angleDeg - 90) * Math.PI) / 180
  return { x: CENTER + radius * Math.cos(a), y: CENTER + radius * Math.sin(a) }
}

/** Path for a donut segment between two angles. */
function arcPath(startAngle: number, endAngle: number): string {
  const startOuter = polar(endAngle, R_OUTER)
  const endOuter = polar(startAngle, R_OUTER)
  const startInner = polar(startAngle, R_INNER)
  const endInner = polar(endAngle, R_INNER)
  const largeArc = endAngle - startAngle <= 180 ? 0 : 1
  return [
    `M ${startOuter.x} ${startOuter.y}`,
    `A ${R_OUTER} ${R_OUTER} 0 ${largeArc} 0 ${endOuter.x} ${endOuter.y}`,
    `L ${startInner.x} ${startInner.y}`,
    `A ${R_INNER} ${R_INNER} 0 ${largeArc} 1 ${endInner.x} ${endInner.y}`,
    "Z",
  ].join(" ")
}

export function GibbsWheel({ currentStep, onSelectStep, size = 120 }: GibbsWheelProps) {
  const sweep = 360 / GIBBS_STEPS.length
  const active = getGibbsStep(currentStep)
  const interactive = typeof onSelectStep === "function"

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" width={size} height={size} role="img" aria-label={`Gibbs reflection cycle, step ${currentStep} of ${GIBBS_STEPS.length}: ${active.label}`}>
        {GIBBS_STEPS.map((s, i) => {
          const start = i * sweep + GAP_DEG / 2
          const end = (i + 1) * sweep - GAP_DEG / 2
          const isCurrent = s.step === currentStep
          const isDone = s.step < currentStep

          const fillClass = isCurrent
            ? "fill-emerald-600"
            : isDone
              ? "fill-emerald-600/40"
              : "fill-[var(--color-muted)]"

          return (
            <path
              key={s.key}
              d={arcPath(start, end)}
              className={`${fillClass} ${interactive ? "cursor-pointer" : ""} transition-[fill] duration-300`}
              stroke={isCurrent ? "var(--color-emerald-500, #10b981)" : "transparent"}
              strokeWidth={isCurrent ? 1.5 : 0}
              onClick={interactive ? () => onSelectStep!(s.step) : undefined}
            >
              <title>{`${s.step}. ${s.label}`}</title>
            </path>
          )
        })}
      </svg>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="text-2xl font-semibold leading-none text-foreground tabular-nums">{currentStep}</span>
        <span className="mt-0.5 px-2 text-[10px] font-medium leading-tight text-muted-foreground">
          {active.label}
        </span>
      </div>
    </div>
  )
}
