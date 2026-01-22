"use client";

import * as React from "react";
import { Switch } from "@/components/ui/switch";
import AlignedTranscript from "@/components/AlignedTranscript";
import type { AlignedWord } from "@/lib/recording.types";

export default function ConfidencePane({ words }: { words: AlignedWord[] }) {
    const [onlyLow, setOnlyLow] = React.useState(false);

    if (!words?.length) {
        return <div className="text-sm text-zinc-500">No aligned words saved.</div>;
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between bg-zinc-100/50 dark:bg-zinc-800/50 p-2 rounded-lg">
                <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
                    Show only low-confidence
                </div>
                <Switch checked={onlyLow} onCheckedChange={setOnlyLow} />
            </div>
            
            <div className="rounded-md border border-zinc-200 dark:border-zinc-800 p-4 bg-white dark:bg-zinc-950 max-h-[400px] overflow-y-auto shadow-inner">
                <div className="flex flex-wrap gap-x-1 gap-y-2 leading-relaxed">
                    <AlignedTranscript
                        words={words as any[]}
                        highlightBelow={0.8}
                        onlyLow={onlyLow}
                    />
                </div>
            </div>

            <div className="flex items-center gap-2 px-1">
                <div className="h-2 w-2 rounded-full bg-red-400 animate-pulse" />
                <div className="text-xs text-zinc-500 italic">
                    Confidence below 80% is highlighted.
                </div>
            </div>
        </div>
    );
}