"use client"

import { ShieldAlert, Terminal, X } from "lucide-react"
import type { AppLanguage } from "@/lib/api"

// Shown in the chat thread when the mandatory Llama Guard safety model isn't installed. The
// guard can't be bypassed (without it we can't ensure a safe environment), so instead of an
// answer the user gets this gentle, dismissible setup card with the exact install command.
type Copy = { title: string; body: string; footer: string; dismiss: string }

const COPY: Record<AppLanguage, Copy> = {
  en: {
    title: "Safety guard isn't set up yet",
    body: "Reflect runs every chat answer through a safety model first. It isn't installed yet, so answering is paused until you add it. Run this on the machine running the backend:",
    footer: "Once it's pulled, send your message again.",
    dismiss: "Dismiss",
  },
  nl: {
    title: "Veiligheidsfilter is nog niet ingesteld",
    body: "Reflect haalt elk chat-antwoord eerst door een veiligheidsmodel. Die is nog niet geïnstalleerd, dus antwoorden is gepauzeerd totdat je hem toevoegt. Voer dit uit op de machine waarop de backend draait:",
    footer: "Zodra hij is opgehaald, stuur je je bericht opnieuw.",
    dismiss: "Sluiten",
  },
}

interface GuardUnavailableCardProps {
  command: string
  onDismiss: () => void
  language?: AppLanguage
}

export function GuardUnavailableCard({ command, onDismiss, language = "en" }: GuardUnavailableCardProps) {
  const copy = COPY[language] ?? COPY.en

  return (
    <div
      role="status"
      aria-live="polite"
      className="relative rounded-2xl border border-amber-200 bg-amber-50/80 px-4 py-3.5 dark:border-amber-900/60 dark:bg-amber-950/40"
    >
      <button
        type="button"
        onClick={onDismiss}
        aria-label={copy.dismiss}
        className="absolute right-2.5 top-2.5 rounded-full p-1 text-amber-700/60 hover:bg-amber-100 hover:text-amber-900 dark:text-amber-300/60 dark:hover:bg-amber-900/50"
      >
        <X className="h-3.5 w-3.5" />
      </button>

      <div className="flex items-start gap-2.5 pr-6">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
        <div>
          <p className="text-[15px] font-medium text-amber-900 dark:text-amber-100">{copy.title}</p>
          <p className="mt-0.5 text-[13px] text-amber-800/90 dark:text-amber-200/80">{copy.body}</p>
        </div>
      </div>

      {command && (
        <div className="mt-3 flex items-center gap-2 rounded-lg border border-amber-200/70 bg-amber-100/60 px-3 py-2 dark:border-amber-900/50 dark:bg-amber-900/30">
          <Terminal className="h-3.5 w-3.5 shrink-0 text-amber-700 dark:text-amber-300" />
          <code className="select-all font-mono text-[13px] text-amber-900 dark:text-amber-100">{command}</code>
        </div>
      )}

      <p className="mt-3 text-[12px] text-amber-700/80 dark:text-amber-300/70">{copy.footer}</p>
    </div>
  )
}
