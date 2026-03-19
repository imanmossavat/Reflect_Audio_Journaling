"use client";

import * as React from "react";
import { fmtNum, fmtPct01, fmtSeconds } from "../../lib/recording.utils";
import type { SpeechAnalysis } from "../../lib/recording.types";

export default function SpeechPane({
                                       speech,
                                   }: {
    speech: SpeechAnalysis | null | undefined;
}) {
    if (!speech || typeof speech !== "object" || Object.keys(speech).length === 0) {
        return <div className="text-sm text-zinc-500">No speech analysis saved.</div>;
    }

    const conf = speech.confidence ?? {};
    const pause = speech.pause ?? {};
    const fillers = speech.fillers ?? {};

    const hits = React.useMemo(() => {
        const raw = Array.isArray(fillers.hits) ? fillers.hits : [];
        return raw
            .map((h) => {
                if (typeof h === "string") return h;
                if (h && typeof h === "object" && typeof h.phrase === "string") return h.phrase;
                return null;
            })
            .filter(Boolean) as string[];
    }, [fillers.hits]);

    const lowWords = Array.isArray(conf.low) ? conf.low : [];

    return (
        <div className="space-y-4">
            {/* Confidence */}
            <div className="rounded border border-zinc-200 dark:border-zinc-800 p-3">
                <div className="text-sm font-semibold">Confidence</div>

                <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                    <div className="flex justify-between gap-2">
                        <span className="text-zinc-500">Mean</span>
                        <span className="font-mono">{fmtNum(conf.mean, 3)}</span>
                    </div>
                    <div className="flex justify-between gap-2">
                        <span className="text-zinc-500">Median</span>
                        <span className="font-mono">{fmtNum(conf.median, 3)}</span>
                    </div>
                    <div className="flex justify-between gap-2">
                        <span className="text-zinc-500">Std</span>
                        <span className="font-mono">{fmtNum(conf.std, 3)}</span>
                    </div>
                    <div className="flex justify-between gap-2">
                        <span className="text-zinc-500">Min</span>
                        <span className="font-mono">{fmtNum(conf.min, 3)}</span>
                    </div>
                    <div className="flex justify-between gap-2">
                        <span className="text-zinc-500">Max</span>
                        <span className="font-mono">{fmtNum(conf.max, 3)}</span>
                    </div>
                </div>

                {lowWords.length > 0 && (
                    <div className="mt-3">
                        <div className="text-xs text-zinc-500 mb-2">Low words (sample)</div>
                        <div className="flex flex-wrap gap-2">
                            {lowWords.slice(0, 30).map((w, i) => (
                                <span
                                    key={`${w.word}-${i}`}
                                    className="text-xs px-2 py-1 rounded border border-zinc-200 dark:border-zinc-800 bg-white/60 dark:bg-zinc-900/40"
                                    title={`prob=${w.prob ?? "?"} @ ${w.start_s ?? "?"}-${w.end_s ?? "?"}`}
                                >
                  {w.word} ({fmtNum(w.prob ?? undefined, 2)})
                </span>
                            ))}
                            {lowWords.length > 30 && (
                                <span className="text-xs text-zinc-500">+{lowWords.length - 30} more…</span>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* Pauses */}
            <div className="rounded border border-zinc-200 dark:border-zinc-800 p-3">
                <div className="text-sm font-semibold">Pauses</div>

                <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                    <div className="flex justify-between gap-2">
                        <span className="text-zinc-500">Avg pause</span>
                        <span className="font-mono">{fmtSeconds(pause.avg_pause_s)}</span>
                    </div>
                    <div className="flex justify-between gap-2">
                        <span className="text-zinc-500">Max pause</span>
                        <span className="font-mono">{fmtSeconds(pause.max_pause_s)}</span>
                    </div>
                    <div className="flex justify-between gap-2">
                        <span className="text-zinc-500">Total silence</span>
                        <span className="font-mono">{fmtSeconds(pause.total_silence_s)}</span>
                    </div>
                </div>
            </div>

            {/* Fillers */}
            <div className="rounded border border-zinc-200 dark:border-zinc-800 p-3">
                <div className="text-sm font-semibold">Fillers</div>

                <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                    <div className="flex justify-between gap-2">
                        <span className="text-zinc-500">Count</span>
                        <span className="font-mono">
              {typeof fillers.count === "number" ? fillers.count : "–"}
            </span>
                    </div>
                    <div className="flex justify-between gap-2">
                        <span className="text-zinc-500">Percent</span>
                        <span className="font-mono">{fmtPct01(fillers.percent)}</span>
                    </div>
                </div>

                <div className="mt-3">
                    <div className="text-xs text-zinc-500 mb-2">Hits</div>

                    {hits.length === 0 ? (
                        <div className="text-sm text-zinc-500">None detected.</div>
                    ) : (
                        <div className="flex flex-wrap gap-2">
                            {hits.slice(0, 40).map((h, i) => (
                                <span
                                    key={`${h}-${i}`}
                                    className="text-xs px-2 py-1 rounded border border-zinc-200 dark:border-zinc-800 bg-white/60 dark:bg-zinc-900/40"
                                >
                  {h}
                </span>
                            ))}
                            {hits.length > 40 && (
                                <span className="text-xs text-zinc-500">+{hits.length - 40} more…</span>
                            )}
                        </div>
                    )}
                </div>
            </div>

            <div className="text-xs text-zinc-500">
                Heads-up: if WhisperX probs are low on average (mean ~{fmtNum(conf.mean, 3)}), audio/noise or
                language mismatch is often the culprit.
            </div>
        </div>
    );
}
