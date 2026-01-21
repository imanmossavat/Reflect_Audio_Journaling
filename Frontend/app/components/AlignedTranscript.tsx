"use client";

import * as React from "react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

type WordLike = {
  word?: string;
  text?: string;
  start_s?: number | null;
  end_s?: number | null;
  score?: number | null;
  prob?: number | null;
};

function getConf(w: WordLike) {
  const v = w.score ?? w.prob;
  return typeof v === "number" ? v : null;
}

function confClass(conf: number | null) {
  if (conf == null) return "opacity-70";
  if (conf < 0.3) return "bg-red-500/15 text-red-700 dark:text-red-300";
  if (conf < 0.5) return "bg-amber-500/15 text-amber-700 dark:text-amber-300";
  return "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300";
}

export default function AlignedTranscript({
  words,
  highlightBelow = 0.8,
  onlyLow = false,
}: {
  words: WordLike[];
  highlightBelow?: number;
  onlyLow?: boolean;
}) {
  return (
    <TooltipProvider>
      <div className="leading-7 text-sm">
        {words.map((w, i) => {
          const token = (w.word ?? w.text ?? "").trim();
          if (!token) return null;

          const conf = getConf(w);
          const low = conf != null && conf < highlightBelow;
          if (onlyLow && !low) {
            return <span key={i} className="mr-1 opacity-40">{token}</span>;
          }

          return (
            <Tooltip key={i}>
              <TooltipTrigger asChild>
                <span
                  className={[
                    "mr-1 px-1.5 py-0.5 rounded",
                    low ? confClass(conf) : "hover:bg-zinc-200/60 dark:hover:bg-zinc-800/60",
                  ].join(" ")}
                >
                  {token}
                </span>
              </TooltipTrigger>
              <TooltipContent className="text-xs">
                <div>conf: {conf == null ? "?" : conf.toFixed(3)}</div>
                <div>
                  t: {w.start_s == null ? "?" : w.start_s.toFixed(2)}s →{" "}
                  {w.end_s == null ? "?" : w.end_s.toFixed(2)}s
                </div>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </TooltipProvider>
  );
}
