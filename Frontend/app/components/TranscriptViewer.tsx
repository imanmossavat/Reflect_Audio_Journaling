"use client";

export default function TranscriptViewer({ text = "", pii = [], segments = [] }) {
    if (!text) return <div className="mt-6 text-zinc-500">No transcript.</div>;

    const ranges = (pii || [])
        .filter((p: any) => typeof p.start_char === "number" && typeof p.end_char === "number")
        .sort((a: any, b: any) => a.start_char - b.start_char);

    const merged: any[] = [];
    for (const r of ranges) {
        const last = merged[merged.length - 1];
        if (!last || r.start_char > last.end_char) merged.push({ ...r });
        else last.end_char = Math.max(last.end_char, r.end_char);
    }

    const parts: React.ReactNode[] = [];
    let cursor = 0;

    merged.forEach((r, i) => {
        const start = Math.max(0, Math.min(text.length, r.start_char));
        const end = Math.max(0, Math.min(text.length, r.end_char));

        if (start > cursor) parts.push(<span key={`t-${i}-a`}>{text.slice(cursor, start)}</span>);

        parts.push(
            <mark
                key={`t-${i}-m`}
                className="rounded px-1 py-0.5 bg-yellow-200 text-zinc-900"
                title={r.label || "PII"}
            >
                {text.slice(start, end)}
            </mark>
        );

        cursor = end;
    });

    if (cursor < text.length) parts.push(<span key="t-end">{text.slice(cursor)}</span>);

    return (
        <div className="mt-6 space-y-6">
            <div className="whitespace-pre-wrap leading-7 text-zinc-800 dark:text-zinc-200">
                {parts.length ? parts : text}
            </div>

            {!!segments?.length && (
                <div className="space-y-3">
                    <div className="font-semibold">Segments</div>
                    {segments.map((s: any, i: number) => (
                        <div
                            key={i}
                            className="rounded border border-zinc-200 dark:border-zinc-800 p-3"
                        >
                            <div className="text-sm font-semibold">{s.label || `Segment ${i + 1}`}</div>
                            <div className="text-sm text-zinc-600 dark:text-zinc-300 mt-1">
                                {s.text}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {!!pii?.length && (
                <div className="text-xs text-zinc-500">Highlighted items: {pii.length}</div>
            )}
        </div>
    );
}
