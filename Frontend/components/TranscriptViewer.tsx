"use client";

import * as React from "react";
import {
    Popover,
    PopoverContent,
    PopoverTrigger
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Trash2, ShieldOff, Plus, Lock } from "lucide-react";

import type {
    PiiHit,
    RecordingSegment,
    TranscriptVersion,
} from "@/lib/recording.types";

type TranscriptViewerProps = {
    version?: TranscriptVersion | string;
    text?: string;
    pii?: PiiHit[];
    segments?: RecordingSegment[];
    readOnly?: boolean;
    onDeletePii?: (hit: PiiHit) => void;
    onAddPii?: (hit: PiiHit) => void;
    onObfuscatePii?: (hit: PiiHit) => void;
    id?: string;
};

type PiiCharRange = PiiHit & { start_char: number; end_char: number };

function hasCharRange(p: PiiHit): p is PiiCharRange {
    return typeof p.start_char === "number" && typeof p.end_char === "number";
}

export default function TranscriptViewer({
                                             version = "",
                                             id = "",
                                             text = "",
                                             pii = [],
                                             readOnly = false,
                                             onDeletePii,
                                             onAddPii,
                                             onObfuscatePii,
                                         }: TranscriptViewerProps) {
    const [selection, setSelection] = React.useState<{ start: number; end: number; text: string } | null>(null);
    const containerRef = React.useRef<HTMLDivElement>(null);

    const handleMouseUp = () => {
        if (readOnly) return;

        const sel = window.getSelection();
        if (!sel || sel.rangeCount === 0 || sel.isCollapsed || !containerRef.current) {
            setSelection(null);
            return;
        }

        const range = sel.getRangeAt(0);
        const selectedText = sel.toString();

        if (!containerRef.current.contains(range.commonAncestorContainer)) {
            setSelection(null);
            return;
        }

        const preSelectionRange = range.cloneRange();
        preSelectionRange.selectNodeContents(containerRef.current);
        preSelectionRange.setEnd(range.startContainer, range.startOffset);

        const start = preSelectionRange.toString().length;
        const end = start + selectedText.length;

        if (selectedText.trim()) {
            setSelection({ start, end, text: selectedText.trim() });
        }
    };

    if (!text) return <div className="mt-6 text-zinc-500 italic">No transcript content available.</div>;

    const shouldHighlightPII = version !== "redacted";
    const ranges: PiiCharRange[] = shouldHighlightPII
        ? pii.filter(hasCharRange).slice().sort((a, b) => a.start_char - b.start_char)
        : [];

    const parts: React.ReactNode[] = [];
    let cursor = 0;

    ranges.forEach((r, i) => {
        const start = Math.max(0, Math.min(text.length, r.start_char));
        const end = Math.max(0, Math.min(text.length, r.end_char));

        // 1. Text before the PII
        if (start > cursor) {
            parts.push(<span key={`text-${i}`}>{text.slice(cursor, start)}</span>);
        }

        // 2. The PII Highlight
        parts.push(
            <Popover key={`pop-${i}`}>
                <PopoverTrigger asChild>
                    <mark
                        className={`cursor-pointer rounded border-b-2 px-1 py-0.5 transition-all ${
                            readOnly
                                ? "border-zinc-300 bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:border-zinc-600 dark:text-zinc-400 cursor-default"
                                : "border-yellow-400 bg-yellow-100 hover:bg-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-100"
                        }`}
                    >
                        {text.slice(start, end)}
                    </mark>
                </PopoverTrigger>
                <PopoverContent className="w-56 p-2 shadow-xl" side="top">
                    <div className="flex flex-col gap-1">
                        <div className="flex items-center justify-between mb-1 px-2">
              <span className="text-[10px] font-bold uppercase text-zinc-400 tracking-wider">
                {r.label || "Detected PII"}
              </span>
                            {readOnly && <Lock className="h-3 w-3 text-zinc-400" />}
                        </div>

                        {!readOnly ? (
                            <>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="justify-start gap-2 text-xs text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/30"
                                    onClick={() => onDeletePii?.(r)}
                                >
                                    <Trash2 className="h-3.5 w-3.5" />
                                    Remove Highlight
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="justify-start gap-2 text-xs text-amber-600 hover:text-amber-700 hover:bg-amber-50 dark:hover:bg-amber-950/30"
                                    onClick={() => onObfuscatePii?.(r)}
                                >
                                    <ShieldOff className="h-3.5 w-3.5" />
                                    Obfuscate Text
                                </Button>
                            </>
                        ) : (
                            <div className="px-2 py-1 text-[11px] text-zinc-500 bg-zinc-50 dark:bg-zinc-900 rounded border border-zinc-100 dark:border-zinc-800">
                                Editing is disabled on the {version} tab.
                            </div>
                        )}
                    </div>
                </PopoverContent>
            </Popover>
        );

        cursor = end;
    });

    // 3. Final chunk of text
    if (cursor < text.length) {
        parts.push(<span key="text-end">{text.slice(cursor)}</span>);
    }

    return (
        <div className="relative mt-6" onMouseUp={handleMouseUp}>
            {/* Floating Selection Menu (Only if NOT readOnly) */}
            {!readOnly && selection && (
                <div
                    className="flex items-center gap-2 p-1.5 bg-zinc-900 text-white rounded-full shadow-2xl animate-in fade-in slide-in-from-bottom-2 duration-200 fixed z-50 border border-zinc-700"
                    style={{ top: '15%', left: '50%', transform: 'translateX(-50%)' }}
                >
          <span className="text-[11px] px-3 font-medium text-zinc-300 max-w-[120px] truncate border-r border-zinc-700">
            "{selection.text}"
          </span>
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-3 text-xs hover:bg-zinc-800 text-emerald-400 hover:text-emerald-300 gap-1.5 rounded-full"
                        onClick={() => {
                            onAddPii?.({
                                start_char: selection.start,
                                end_char: selection.end,
                                label: "MANUAL",
                                preview: selection.text,
                                recording_id: id
                            } as any);
                            setSelection(null);
                        }}
                    >
                        <Plus className="h-3.5 w-3.5" />
                        Tag PII
                    </Button>
                </div>
            )}

            {/* Main Text Display */}
            <div
                ref={containerRef}
                className={`whitespace-pre-wrap rounded-lg leading-7 text-zinc-800 dark:text-zinc-200 transition-opacity ${
                    readOnly ? "opacity-90 select-none" : "select-text"
                }`}
            >
                {parts.length ? parts : text}
            </div>

            {/* Footer Info */}
            <div className="mt-4 flex items-center justify-between border-t border-zinc-100 dark:border-zinc-800 pt-4">
                {shouldHighlightPII && (
                    <div className="flex items-center gap-2 text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                        <span className={`h-2 w-2 rounded-full ${readOnly ? 'bg-zinc-300' : 'bg-yellow-400 animate-pulse'}`} />
                        {pii.length} {version} detections
                    </div>
                )}
                {readOnly && (
                    <div className="flex items-center gap-1.5 text-[10px] font-medium text-zinc-400 bg-zinc-100 dark:bg-zinc-900 px-2 py-0.5 rounded">
                        <Lock className="h-3 w-3" /> READ ONLY
                    </div>
                )}
            </div>
        </div>
    );
}