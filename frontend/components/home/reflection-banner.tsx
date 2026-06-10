"use client"

import { ArrowRight, CheckCircle2, HelpCircle, Loader2, Sparkles, X } from "lucide-react"
import { GibbsWheel } from "@/components/home/gibbs-wheel"
import { GIBBS_STEPS, GIBBS_STEP_COUNT, getGibbsStep } from "@/lib/gibbs"

interface ReflectionBannerProps {
  active: boolean
  step: number
  generating: boolean
  onStart: () => void
  onAdvance: () => void
  onClarify: () => void
  onEnd: () => void
  onSelectStep?: (step: number) => void
}

export function ReflectionBanner({
  active,
  step,
  generating,
  onStart,
  onAdvance,
  onClarify,
  onEnd,
  onSelectStep,
}: ReflectionBannerProps) {
  if (!active) {
    return (
      <div className="border-b bg-muted/10 px-6 py-2 shrink-0">
        <button
          data-tour="reflect"
          onClick={onStart}
          className="flex items-center gap-2 rounded-md px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        >
          <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
          Start guided reflection
          <span className="text-muted-foreground/60">(Gibbs cycle)</span>
        </button>
      </div>
    )
  }

  const current = getGibbsStep(step)
  const isLastStep = step >= GIBBS_STEP_COUNT

  return (
    <div className="border-b bg-muted/10 px-6 py-3 shrink-0">
      <div className="flex items-center gap-4">
        <GibbsWheel currentStep={step} size={104} onSelectStep={onSelectStep} />

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Step {step} of {GIBBS_STEP_COUNT}
            </span>
            <span className="text-sm font-semibold text-foreground">{current.label}</span>
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">Reflecting on {current.blurb}.</p>

          {/* Progress dots mirror the wheel. */}
          <div className="mt-2 flex items-center gap-1.5">
            {GIBBS_STEPS.map((s) => (
              <span
                key={s.key}
                title={`${s.step}. ${s.label}`}
                className={`h-1.5 w-1.5 rounded-full transition-colors ${
                  s.step === step
                    ? "bg-emerald-600"
                    : s.step < step
                      ? "bg-emerald-600/40"
                      : "bg-muted-foreground/30"
                }`}
              />
            ))}
          </div>

          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            <button
              onClick={onAdvance}
              disabled={generating}
              className="flex items-center gap-1.5 rounded-md bg-emerald-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {generating ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : isLastStep ? (
                <CheckCircle2 className="h-3.5 w-3.5" />
              ) : (
                <ArrowRight className="h-3.5 w-3.5" />
              )}
              {isLastStep ? "Finish" : "Next stage"}
            </button>
            <button
              onClick={onClarify}
              disabled={generating}
              className="flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <HelpCircle className="h-3.5 w-3.5" />
              Ask about this stage
            </button>
            <button
              onClick={onEnd}
              className="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="h-3.5 w-3.5" />
              End
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
