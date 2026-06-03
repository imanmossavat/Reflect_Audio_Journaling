// Metadata for the six stages of the Gibbs reflective cycle. This mirrors the
// backend `step_questions` map in
// Backend/app/prompts/simpler_dictionary_question_prompt.py — keep the two in sync.

export interface GibbsStep {
  step: number
  key: string
  label: string
  /** Short hint shown in the reflection banner describing what this stage explores. */
  blurb: string
}

export const GIBBS_STEPS: readonly GibbsStep[] = [
  { step: 1, key: "description", label: "Description", blurb: "the concrete moment or situation" },
  { step: 2, key: "feelings", label: "Feelings", blurb: "what you felt in that moment" },
  { step: 3, key: "evaluation", label: "Evaluation", blurb: "what went well and what was hard" },
  { step: 4, key: "analysis", label: "Analysis", blurb: "the patterns you notice" },
  { step: 5, key: "conclusion", label: "Conclusion", blurb: "the insights emerging" },
  { step: 6, key: "actionPlan", label: "Action Plan", blurb: "what to explore or try next" },
] as const

export const GIBBS_STEP_COUNT = GIBBS_STEPS.length

export function getGibbsStep(step: number): GibbsStep {
  return GIBBS_STEPS.find((s) => s.step === step) ?? GIBBS_STEPS[0]
}
