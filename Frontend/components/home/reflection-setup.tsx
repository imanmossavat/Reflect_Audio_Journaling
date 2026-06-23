"use client"

import { useState } from "react"
import { ArrowLeft, ArrowRight, Check, FileText, Loader2, Pencil, Sparkles, X } from "lucide-react"
import type { TopicGroup } from "@/lib/api"

interface ReflectionSetupProps {
  includedSourceNames: string[]
  goal: string
  scopeItemCount: number
  onChangeGoal: (value: string) => void
  /** Fetch grouped topics from the included sources (may be slow / may return []). */
  onGroupTopics: () => Promise<TopicGroup[]>
  /** Adopt a chosen topic as the goal + scope. */
  onSelectTopic: (topic: TopicGroup) => void
  /** Drop any chosen topic's excerpts (when writing a free-text goal or skipping). */
  onClearScope: () => void
  /** Begin the reflection (ask the first question) with the current goal/scope. */
  onBegin: () => void
  /** Abandon setup and leave reflection mode. */
  onCancel: () => void
}

type SetupStage = "sources" | "topic" | "ready"

/** The pre-reflection setup, shown in the center column above the chat. Three sequential
 *  stages: pick sources, choose a topic (grouped from those sources, or write your own),
 *  then a Ready launch pad. Both input stages are optional; the reflection only begins
 *  from Ready. */
export function ReflectionSetup({
  includedSourceNames,
  goal,
  scopeItemCount,
  onChangeGoal,
  onGroupTopics,
  onSelectTopic,
  onClearScope,
  onBegin,
  onCancel,
}: ReflectionSetupProps) {
  const [stage, setStage] = useState<SetupStage>("sources")
  const includedCount = includedSourceNames.length

  return (
    <div className="flex flex-1 min-h-0 flex-col items-center overflow-y-auto no-scrollbar px-6 py-8">
      <div className="w-full max-w-xl">
        {/* Header + stage indicator */}
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-emerald-600" />
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            Set up your reflection
          </span>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <StagePill label="01 · Sources" active={stage === "sources"} done={stage !== "sources"} />
          <span className="h-px w-4 bg-border" />
          <StagePill label="02 · Topic" active={stage === "topic"} done={stage === "ready"} />
          <span className="h-px w-4 bg-border" />
          <StagePill label="03 · Ready" active={stage === "ready"} done={false} />
        </div>

        {stage === "sources" ? (
          <div className="mt-6">
            <h2 className="text-lg font-semibold text-foreground">Pick what to reflect on</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Choose the entries this reflection should draw from in the Sources panel on the left.
              You can change your selection later.
            </p>

            <div className="mt-4 flex items-center gap-2 rounded-lg border bg-background/60 px-4 py-3">
              <FileText className="h-4 w-4 shrink-0 text-emerald-600" />
              <span className="text-sm text-foreground">
                {includedCount === 0
                  ? "No sources included yet"
                  : `${includedCount} source${includedCount === 1 ? "" : "s"} included`}
              </span>
            </div>

            <div className="mt-6 flex items-center justify-between">
              <button
                onClick={onCancel}
                className="flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
                Cancel
              </button>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    onChangeGoal("")
                    onClearScope()
                    setStage("ready")
                  }}
                  className="rounded-full px-4 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                >
                  Skip setup
                </button>
                <button
                  onClick={() => setStage("topic")}
                  className="flex items-center gap-2 rounded-full bg-emerald-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-emerald-700"
                >
                  Next
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        ) : stage === "topic" ? (
          <TopicStage
            goal={goal}
            onChangeGoal={onChangeGoal}
            onGroupTopics={onGroupTopics}
            onSelectTopic={(t) => {
              onSelectTopic(t)
              setStage("ready")
            }}
            onClearScope={onClearScope}
            onBack={() => setStage("sources")}
            onSkip={() => {
              onChangeGoal("")
              onClearScope()
              setStage("ready")
            }}
            onContinue={() => setStage("ready")}
          />
        ) : (
          <div className="mt-6">
            <h2 className="text-lg font-semibold text-foreground">Ready to begin</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Here&apos;s what this reflection will work from. Begin when you&apos;re ready.
            </p>

            {/* Sources summary */}
            <div className="mt-4 rounded-lg border bg-background/60 p-3">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Sources</div>
              {includedCount === 0 ? (
                <p className="mt-1.5 text-sm text-muted-foreground/70">No sources selected</p>
              ) : (
                <ul className="mt-2 flex flex-col gap-1">
                  {includedSourceNames.map((name, i) => (
                    <li key={`${name}-${i}`} className="flex items-center gap-2 text-sm text-foreground">
                      <FileText className="h-3.5 w-3.5 shrink-0 text-emerald-600" />
                      <span className="truncate">{name}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Topic / goal summary */}
            <div className="mt-3 rounded-lg border bg-background/60 p-3">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Topic</div>
              <p className="mt-1.5 text-sm leading-snug text-foreground">
                {goal.trim() ? goal : <span className="text-muted-foreground/70">No specific topic</span>}
              </p>
              {scopeItemCount > 0 && (
                <p className="mt-1 text-xs text-muted-foreground">
                  Scoped to {scopeItemCount} excerpt{scopeItemCount === 1 ? "" : "s"}.
                </p>
              )}
            </div>

            <div className="mt-6 flex items-center justify-between">
              <button
                onClick={() => setStage("topic")}
                className="flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Back
              </button>
              <button
                onClick={onBegin}
                className="flex items-center gap-2 rounded-full bg-emerald-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-emerald-700"
              >
                Begin with Description
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function TopicStage({
  goal,
  onChangeGoal,
  onGroupTopics,
  onSelectTopic,
  onClearScope,
  onBack,
  onSkip,
  onContinue,
}: {
  goal: string
  onChangeGoal: (value: string) => void
  onGroupTopics: () => Promise<TopicGroup[]>
  onSelectTopic: (topic: TopicGroup) => void
  onClearScope: () => void
  onBack: () => void
  onSkip: () => void
  onContinue: () => void
}) {
  // Default to the free-text path; grouping is opt-in via the action below so we don't
  // fire an LLM call unless the user asks for suggestions.
  const [mode, setMode] = useState<"write" | "suggest">("write")
  const [topics, setTopics] = useState<TopicGroup[] | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSuggest = () => {
    onClearScope()
    setMode("suggest")
    if (topics !== null) return // already fetched this session
    setLoading(true)
    onGroupTopics().then((result) => {
      setTopics(result)
      setLoading(false)
    })
  }

  return (
    <div className="mt-6">
      <h2 className="text-lg font-semibold text-foreground">What do you want to look into?</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Name the topic or question for this reflection — or let the app suggest themes from your sources.
        It keeps the facilitator focused.
      </p>

      {mode === "write" ? (
        <div className="mt-4">
          <textarea
            autoFocus
            value={goal}
            onChange={(e) => onChangeGoal(e.target.value)}
            rows={5}
            placeholder="e.g. why I keep avoiding deep work, and what I want to do about it."
            className="w-full resize-none rounded-lg border bg-background px-3.5 py-3 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
          <button
            onClick={handleSuggest}
            className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-emerald-600/40 bg-emerald-600/10 px-3.5 py-2 text-xs font-medium text-emerald-700 transition-colors hover:bg-emerald-600/20 dark:text-emerald-400"
          >
            <Sparkles className="h-3.5 w-3.5" />
            Suggest themes from my sources
          </button>
        </div>
      ) : loading ? (
        <div className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin text-emerald-600" />
          Grouping your sources into themes…
        </div>
      ) : topics && topics.length > 0 ? (
        <div className="mt-4 flex flex-col gap-2">
          {topics.map((topic, i) => (
            <button
              key={`${topic.name}-${i}`}
              onClick={() => onSelectTopic(topic)}
              className={`rounded-lg border px-4 py-3 text-left transition-colors ${
                goal === topic.name ? "border-emerald-600/50 bg-emerald-600/5" : "hover:bg-muted/50"
              }`}
            >
              <div className="flex items-center gap-2">
                {goal === topic.name && <Check className="h-3.5 w-3.5 shrink-0 text-emerald-600" />}
                <span className="text-sm font-medium text-foreground">{topic.name}</span>
              </div>
              {topic.summary && <p className="mt-1 text-xs text-muted-foreground">{topic.summary}</p>}
              {topic.items.length > 0 && (
                <p className="mt-1 text-[11px] text-muted-foreground/70">
                  {topic.items.length} excerpt{topic.items.length === 1 ? "" : "s"}
                </p>
              )}
            </button>
          ))}
          <button
            onClick={() => setMode("write")}
            className="mt-1 flex items-center gap-1.5 self-start text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            <Pencil className="h-3.5 w-3.5" />
            Write my own instead
          </button>
        </div>
      ) : (
        <div className="mt-4">
          <p className="text-sm text-muted-foreground">
            No distinct themes were found in your sources. Write your own topic instead.
          </p>
          <button
            onClick={() => setMode("write")}
            className="mt-2 flex items-center gap-1.5 text-xs text-emerald-700 transition-colors hover:underline dark:text-emerald-400"
          >
            <Pencil className="h-3.5 w-3.5" />
            Write my own
          </button>
        </div>
      )}

      <div className="mt-6 flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back
        </button>
        <div className="flex items-center gap-2">
          <button
            onClick={onSkip}
            className="rounded-full px-4 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            Skip topic
          </button>
          <button
            onClick={onContinue}
            className="flex items-center gap-2 rounded-full bg-emerald-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-emerald-700"
          >
            Next
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

function StagePill({ label, active, done }: { label: string; active: boolean; done: boolean }) {
  return (
    <span
      className={`font-mono text-[10px] uppercase tracking-[0.18em] ${
        active ? "text-emerald-600" : done ? "text-emerald-600/60" : "text-muted-foreground/50"
      }`}
    >
      {label}
    </span>
  )
}
