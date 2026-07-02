"use client"

import { Heart, Phone, MessageCircle, AlertTriangle, X } from "lucide-react"
import type { SafetyKind, AppLanguage } from "@/lib/api"

// these are crisis/support resources — the contact details are hard-coded
type Line = { icon: "phone" | "chat" | "alert"; label: string }
type Copy = { title: string; body: string; lines: Line[]; footer: string; dismiss: string }

const COPY: Record<SafetyKind, Record<AppLanguage, Copy>> = {
  self_harm: {
    en: {
      title: "You don't have to face this alone",
      body: "It sounds like you're carrying something really heavy right now. Reaching out can help.",
      lines: [
        { icon: "phone", label: "113 Suicide Prevention — call 0800-0113 (free, 24/7)" },
        { icon: "chat", label: "Chat anonymously at 113.nl" },
        { icon: "alert", label: "In immediate danger? Call 112." },
      ],
      footer: "You can keep reflecting whenever you're ready.",
      dismiss: "Dismiss",
    },
    nl: {
      title: "Je hoeft dit niet alleen te doen",
      body: "Het klinkt alsof je op dit moment iets zwaars met je meedraagt. Erover praten kan helpen.",
      lines: [
        { icon: "phone", label: "113 Zelfmoordpreventie — bel 0800-0113 (gratis, 24/7)" },
        { icon: "chat", label: "Chat anoniem via 113.nl" },
        { icon: "alert", label: "In direct gevaar? Bel 112." },
      ],
      footer: "Je kunt verder reflecteren wanneer je er klaar voor bent.",
      dismiss: "Sluiten",
    },
  },
  support: {
    en: {
      title: "It's okay to reach out",
      body: "It sounds like there's a lot going on and the feelings are running high.",
      lines: [
        { icon: "chat", label: "Talking it through can help — someone you trust, or your GP" },
        { icon: "phone", label: "de Luisterlijn — call 088 0767 000 for a listening ear (24/7)" },
      ],
      footer: "You can keep reflecting whenever you're ready.",
      dismiss: "Dismiss",
    },
    nl: {
      title: "Het is oké om hulp te zoeken",
      body: "Het klinkt alsof er veel speelt en de emoties hoog zitten.",
      lines: [
        { icon: "chat", label: "Erover praten kan helpen — met iemand die je vertrouwt of je huisarts" },
        { icon: "phone", label: "de Luisterlijn — bel 088 0767 000 voor een luisterend oor (24/7)" },
      ],
      footer: "Je kunt verder reflecteren wanneer je er klaar voor bent.",
      dismiss: "Sluiten",
    },
  },
}

const LINE_ICON = { phone: Phone, chat: MessageCircle, alert: AlertTriangle }

interface CrisisSupportCardProps {
  kind: SafetyKind
  onDismiss: () => void
  language?: AppLanguage
}

/** A gentle, dismissible support card shown when the guardrail detects distress. It never
 *  blocks the user — it sits alongside the conversation and offers vetted resources. */
export function CrisisSupportCard({ kind, onDismiss, language = "en" }: CrisisSupportCardProps) {
  const copy = COPY[kind][language] ?? COPY[kind].en

  return (
    <div
      role="status"
      aria-live="polite"
      className="relative rounded-2xl border border-emerald-200 bg-emerald-50/80 px-4 py-3.5 dark:border-emerald-900/60 dark:bg-emerald-950/40"
    >
      <button
        type="button"
        onClick={onDismiss}
        aria-label={copy.dismiss}
        className="absolute right-2.5 top-2.5 rounded-full p-1 text-emerald-700/60 hover:bg-emerald-100 hover:text-emerald-900 dark:text-emerald-300/60 dark:hover:bg-emerald-900/50"
      >
        <X className="h-3.5 w-3.5" />
      </button>

      <div className="flex items-start gap-2.5 pr-6">
        <Heart className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
        <div>
          <p className="text-[15px] font-medium text-emerald-900 dark:text-emerald-100">{copy.title}</p>
          <p className="mt-0.5 text-[13px] text-emerald-800/90 dark:text-emerald-200/80">{copy.body}</p>
        </div>
      </div>

      <ul className="mt-3 space-y-1.5 pl-1">
        {copy.lines.map((line, i) => {
          const Icon = LINE_ICON[line.icon]
          return (
            <li key={i} className="flex items-center gap-2 text-[13px] text-emerald-900 dark:text-emerald-100">
              <Icon className="h-3.5 w-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
              <span>{line.label}</span>
            </li>
          )
        })}
      </ul>

      <p className="mt-3 text-[12px] text-emerald-700/80 dark:text-emerald-300/70">{copy.footer}</p>
    </div>
  )
}
