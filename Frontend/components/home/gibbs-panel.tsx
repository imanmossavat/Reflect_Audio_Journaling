"use client"

import {
  ArrowRight,
  BookmarkPlus,
  Check,
  CheckCircle2,
  FileText,
  Loader2,
  PanelRightClose,
  RotateCcw,
  X,
} from "lucide-react"
import { GIBBS_STEPS, GIBBS_STEP_COUNT, getGibbsStep } from "@/lib/gibbs"

interface GibbsPanelProps {
  /** Current stage in focus (1-6). */
  step: number
  /** True while the facilitator is generating a question/reply. */
  generating: boolean
  /** True once the final stage is finished — shows the wrap-up. */
  complete: boolean
  /** True during the pre-reflection setup phase; the interactive setup (pick sources +
   *  write a goal) lives in the center column, so this panel only shows status. */
  setup: boolean
  /** The user's goal/topic for this reflection, shown read-only during setup. */
  goal: string
  /** Number of sources currently included for this reflection. */
  includedCount: number
  /** Whether the active chat is being promoted to a source. */
  isPromotingChat: boolean
  onAdvance: () => void
  onClarify: () => void
  onEnd: () => void
  onSelectStep: (step: number) => void
  onSaveToSources: () => void
  onBeginNewCycle: () => void
  onCollapse: () => void
}

const pad = (n: number) => String(n).padStart(2, "0")

/** Segmented progress ring, mirroring the Claude Design "Segmented Ring" mockup:
 *  six rounded arcs, one per Gibbs stage. */
function SegmentedRing({ step, complete }: { step: number; complete: boolean }) {
  return (
    <div className="relative mx-auto" style={{ width: 168, height: 168 }}>
      <svg width={168} height={168} viewBox="0 0 196 196" role="img" aria-label={`Gibbs cycle, step ${step} of ${GIBBS_STEP_COUNT}`}>
        {GIBBS_STEPS.map((s, i) => {
          const done = complete || s.step < step
          const isCurrent = !complete && s.step === step
          const strokeClass = done
            ? "stroke-emerald-600/45"
            : isCurrent
              ? "stroke-emerald-600"
              : "stroke-muted-foreground/20"
          return (
            <circle
              key={s.key}
              cx={98}
              cy={98}
              r={78}
              fill="none"
              strokeWidth={13}
              strokeLinecap="round"
              strokeDasharray="54 436"
              transform={`rotate(${i * 60 - 110} 98 98)`}
              className={`${strokeClass} transition-[stroke] duration-300`}
            >
              <title>{`${s.step}. ${s.label}`}</title>
            </circle>
          )
        })}
      </svg>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
        {complete ? (
          <span className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-600 text-white">
            <Check className="h-7 w-7" />
          </span>
        ) : (
          <>
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-emerald-600">
              {getGibbsStep(step).label.split(" ")[0]}
            </span>
            <span className="text-4xl font-semibold leading-none text-foreground tabular-nums">{pad(step)}</span>
            <span className="mt-1 font-mono text-[10px] tracking-[0.16em] text-muted-foreground">
              of {pad(GIBBS_STEP_COUNT)}
            </span>
          </>
        )}
      </div>
    </div>
  )
}

export function GibbsPanel({
  step,
  generating,
  complete,
  setup,
  goal,
  includedCount,
  isPromotingChat,
  onAdvance,
  onClarify,
  onEnd,
  onSelectStep,
  onSaveToSources,
  onBeginNewCycle,
  onCollapse,
}: GibbsPanelProps) {
  const current = getGibbsStep(step)
  const isLastStep = step >= GIBBS_STEP_COUNT
  const nextLabel = isLastStep ? null : getGibbsStep(step + 1).label

  return (
    <div className="flex h-full flex-col bg-muted/10">
      {/* Header */}
      <div className="flex h-12 shrink-0 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">reflect</span>
          {setup ? (
            <span className="font-mono text-[11px] tracking-[0.16em] text-emerald-600">setup</span>
          ) : complete ? (
            <span className="font-mono text-[11px] tracking-[0.16em] text-emerald-600">
              {pad(GIBBS_STEP_COUNT)} / {pad(GIBBS_STEP_COUNT)} ✓
            </span>
          ) : (
            <span className="font-mono text-[11px] tracking-[0.16em] text-muted-foreground/70">
              {pad(step)} / {pad(GIBBS_STEP_COUNT)}
            </span>
          )}
        </div>
        <button
          onClick={onCollapse}
          aria-label="Hide panel"
          title="Hide panel"
          className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors"
        >
          <PanelRightClose className="h-3.5 w-3.5" />
        </button>
      </div>

      {setup ? (
        <SetupView goal={goal} includedCount={includedCount} onEnd={onEnd} />
      ) : complete ? (
        <CompletionView
          isPromotingChat={isPromotingChat}
          onSaveToSources={onSaveToSources}
          onBeginNewCycle={onBeginNewCycle}
        />
      ) : (
        <div className="flex-1 min-h-0 overflow-y-auto no-scrollbar px-4 py-5">
          <SegmentedRing step={step} complete={false} />

          {/* Focus block */}
          <div className="mt-5">
            <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-emerald-600">
              {current.label} · now
            </div>
            <p className="mt-2 text-base font-medium leading-snug text-foreground">
              Reflecting on {current.blurb}.
            </p>
            <p className="mt-1.5 text-xs text-muted-foreground">
              Reply in the chat in your own words — take your time.
            </p>
          </div>

          {/* Actions — kept above the step list so they stay reachable without scrolling */}
          <div className="mt-6 flex flex-col gap-2">
            <button
              onClick={onAdvance}
              disabled={generating}
              className="flex items-center justify-center gap-2 rounded-full bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {generating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : isLastStep ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : (
                <ArrowRight className="h-4 w-4" />
              )}
              {isLastStep ? "Finish reflection" : `Continue to ${nextLabel}`}
            </button>
            <button
              onClick={onClarify}
              disabled={generating}
              className="flex items-center justify-center gap-2 rounded-full border border-emerald-600/40 bg-emerald-600/10 px-4 py-2 text-sm font-medium text-emerald-700 transition-colors hover:bg-emerald-600/20 hover:border-emerald-600/60 dark:text-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Ask another question
            </button>
          </div>

          {/* Step list */}
          <div className="mt-6 flex flex-col gap-0.5">
            {GIBBS_STEPS.map((s) => {
              const isDone = s.step < step
              const isCurrent = s.step === step
              const isFuture = s.step > step
              const selectable = s.step <= step
              return (
                <button
                  key={s.key}
                  onClick={selectable ? () => onSelectStep(s.step) : undefined}
                  disabled={!selectable || generating}
                  className={`flex w-full items-start gap-3 rounded-lg px-2.5 py-2 text-left transition-colors ${
                    isCurrent ? "bg-emerald-600/10" : "hover:bg-muted/50"
                  } ${selectable ? "cursor-pointer" : "cursor-default"} disabled:cursor-not-allowed`}
                >
                  <span
                    className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] ${
                      isDone
                        ? "bg-emerald-600/50 text-white"
                        : isCurrent
                          ? "bg-emerald-600 text-white"
                          : "border border-muted-foreground/30 text-transparent"
                    }`}
                  >
                    {isDone ? <Check className="h-3 w-3" /> : ""}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-baseline gap-2">
                      <span className="font-mono text-[10px] text-muted-foreground">{pad(s.step)}</span>
                      <span
                        className={`text-sm ${
                          isFuture ? "text-muted-foreground" : "text-foreground"
                        } ${isCurrent ? "font-semibold" : ""}`}
                      >
                        {s.label}
                      </span>
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                      {isDone ? s.blurb : isCurrent ? "In progress…" : "Not yet"}
                    </span>
                  </span>
                </button>
              )
            })}
          </div>

          {/* End reflection — secondary, stays at the bottom */}
          <div className="mt-6 flex flex-col gap-2">
            <button
              onClick={onEnd}
              className="mt-1 flex items-center justify-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
              End reflection
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

/** During setup the interactive form lives in the center column; this panel just shows
 *  the cycle is being set up, mirroring the live source count and goal. */
function SetupView({
  goal,
  includedCount,
  onEnd,
}: {
  goal: string
  includedCount: number
  onEnd: () => void
}) {
  return (
    <div className="flex flex-1 flex-col min-h-0">
      <div className="flex-1 min-h-0 overflow-y-auto no-scrollbar px-4 py-5">
        <SegmentedRing step={1} complete={false} />

        <div className="mt-5 text-center">
          <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-emerald-600">Setting up</div>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Choose your sources and a goal in the center, then begin.
          </p>
        </div>

        <div className="mt-6 flex flex-col gap-3">
          <div className="rounded-xl border bg-background/60 p-3">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 shrink-0 text-emerald-600" />
              <span className="text-sm text-foreground">
                {includedCount === 0
                  ? "No sources included yet"
                  : `${includedCount} source${includedCount === 1 ? "" : "s"} included`}
              </span>
            </div>
          </div>
          <div className="rounded-xl border bg-background/60 p-3">
            <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Goal</div>
            <p className="mt-1.5 text-sm leading-snug text-foreground">
              {goal.trim() ? goal : <span className="text-muted-foreground/60">Not set yet</span>}
            </p>
          </div>
        </div>
      </div>

      <div className="shrink-0 border-t p-4">
        <button
          onClick={onEnd}
          className="flex w-full items-center justify-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" />
          End reflection
        </button>
      </div>
    </div>
  )
}

function CompletionView({
  isPromotingChat,
  onSaveToSources,
  onBeginNewCycle,
}: {
  isPromotingChat: boolean
  onSaveToSources: () => void
  onBeginNewCycle: () => void
}) {
  return (
    <div className="flex flex-1 flex-col min-h-0">
      <div className="flex-1 min-h-0 overflow-y-auto no-scrollbar px-4 py-5">
        <SegmentedRing step={GIBBS_STEP_COUNT} complete />

        <div className="mt-5 text-center">
          <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-emerald-600">Cycle complete</div>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Six steps, one thread. Here&apos;s the shape of your reflection.
          </p>
        </div>

        {/* Placeholder per-step summary — real per-step distillation is a future step. */}
        <div className="mt-6 flex flex-col">
          {GIBBS_STEPS.slice(0, GIBBS_STEP_COUNT - 1).map((s) => (
            <div key={s.key} className="flex items-baseline gap-3 border-b py-2.5">
              <span className="w-5 shrink-0 font-mono text-[11px] text-emerald-600">{pad(s.step)}</span>
              <span className="w-20 shrink-0 text-[10px] uppercase tracking-wide text-muted-foreground">
                {s.label}
              </span>
              <span className="text-sm text-muted-foreground/60">—</span>
            </div>
          ))}
        </div>

        {/* Action plan card */}
        <div className="mt-4 rounded-xl border border-emerald-600/40 bg-emerald-600/10 p-4">
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-emerald-600">
            {pad(GIBBS_STEP_COUNT)} · Action plan
          </div>
          <p className="mt-2 text-base leading-snug text-muted-foreground/70">
            Your action plan from this cycle will live here.
          </p>
        </div>
      </div>

      {/* Wrap-up actions */}
      <div className="shrink-0 border-t p-4">
        <div className="flex flex-col gap-2">
          <button
            onClick={onSaveToSources}
            disabled={isPromotingChat}
            className="flex items-center justify-center gap-2 rounded-full bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isPromotingChat ? <Loader2 className="h-4 w-4 animate-spin" /> : <BookmarkPlus className="h-4 w-4" />}
            {isPromotingChat ? "Saving…" : "Save to sources"}
          </button>
          <button
            onClick={onBeginNewCycle}
            className="flex items-center justify-center gap-2 rounded-full border px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Begin a new cycle
          </button>
        </div>
      </div>
    </div>
  )
}
