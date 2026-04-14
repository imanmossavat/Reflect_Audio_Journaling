"use client"

import { useEffect, useMemo, useState } from "react"

export interface OnboardingProfile {
  name: string
  job: string
  age: number
}

type OnboardingModalProps = {
  open: boolean
  onSkip: () => void
  onSubmit: (profile: OnboardingProfile) => void
}

export function OnboardingModal({ open, onSkip, onSubmit }: OnboardingModalProps) {
  const [name, setName] = useState("")
  const [job, setJob] = useState("")
  const [ageInput, setAgeInput] = useState("")

  useEffect(() => {
    if (!open) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onSkip()
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [open, onSkip])

  const canContinue = useMemo(() => {
    if (!name.trim() || !job.trim() || !ageInput.trim()) return false
    const numericAge = Number(ageInput)
    if (!Number.isInteger(numericAge)) return false
    return numericAge > 0 && numericAge < 130
  }, [name, job, ageInput])

  if (!open) return null

  const handleContinue = () => {
    if (!canContinue) return

    onSubmit({
      name: name.trim(),
      job: job.trim(),
      age: Number(ageInput),
    })
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-3xl max-h-[88vh] overflow-y-auto rounded-2xl border bg-background p-8 shadow-xl md:p-10">
        <h2 className="text-2xl font-semibold tracking-tight">Welcome to Reflect</h2>
        <p className="mt-2 text-base text-muted-foreground">
          A quick setup helps personalize your reflection flow.
        </p>

        <div className="mt-8 space-y-5">
          <div className="space-y-1">
            <label htmlFor="onboarding-name" className="text-base font-medium">
              Name
            </label>
            <input
              id="onboarding-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Your name"
              className="w-full rounded-md border bg-background px-4 py-3 text-base outline-none focus:ring-2 focus:ring-emerald-500/30"
            />
          </div>

          <div className="space-y-1">
            <label htmlFor="onboarding-job" className="text-base font-medium">
              Job
            </label>
            <input
              id="onboarding-job"
              value={job}
              onChange={(event) => setJob(event.target.value)}
              placeholder="Student, Engineer, Designer..."
              className="w-full rounded-md border bg-background px-4 py-3 text-base outline-none focus:ring-2 focus:ring-emerald-500/30"
            />
          </div>

          <div className="space-y-1">
            <label htmlFor="onboarding-age" className="text-base font-medium">
              Age
            </label>
            <input
              id="onboarding-age"
              value={ageInput}
              onChange={(event) => setAgeInput(event.target.value.replace(/[^\d]/g, ""))}
              inputMode="numeric"
              placeholder="e.g. 24"
              className="w-full rounded-md border bg-background px-4 py-3 text-base outline-none focus:ring-2 focus:ring-emerald-500/30"
            />
          </div>
        </div>

        <div className="mt-8 flex flex-col gap-3">
          <button
            type="button"
            onClick={handleContinue}
            disabled={!canContinue}
            className="w-full rounded-md px-4 py-3 text-base font-medium text-white transition-colors disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground enabled:bg-emerald-600 enabled:hover:bg-emerald-700"
          >
            Continue
          </button>
          <button
            type="button"
            onClick={onSkip}
            className="w-full bg-transparent px-2 py-1 text-center text-sm text-muted-foreground underline-offset-4 hover:underline"
          >
            Skip
          </button>
        </div>
      </div>
    </div>
  )
}
