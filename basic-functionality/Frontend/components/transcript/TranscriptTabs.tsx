"use client";

import * as React from "react";
import TranscriptViewer from "./TranscriptViewer";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

import type {
    PiiHit,
    TranscriptVersion,
    TranscriptBlob,
    RecordingSegment,
} from "@/lib/recording.types";

type OnTextLoadedPayload = { text: string; version: TranscriptVersion };

async function fetchTranscript(api: string, id: string, version: TranscriptVersion) {
    const r = await fetch(`${api}/api/recordings/${id}/transcript?version=${version}`, {
        cache: "no-store",
    });
    if (!r.ok) return { text: "", version };
    const data = await r.json();
    const v = (data?.version ?? version) as TranscriptVersion;
    return { text: data?.text ?? "", version: v };
}

function downloadTextFile(filename: string, text: string) {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

export default function TranscriptTabs({
    api,
    id,
    transcripts,
    piiOriginal,
    piiEdited,
    segments,
    onTextLoaded,
    // Add the new handlers passed from RecordingClient
    onDeletePii,
    onAddPii,
    onObfuscatePii,
}: {
    api: string;
    id: string;
    transcripts?: TranscriptBlob;
    piiOriginal?: PiiHit[];
    piiEdited?: PiiHit[];
    segments?: RecordingSegment[];
    onTextLoaded?: (payload: OnTextLoadedPayload) => void;
    onDeletePii: (hit: PiiHit) => void;
    onAddPii: (hit: PiiHit) => void;
    onObfuscatePii: (hit: PiiHit) => void;
}) {
    // Determine which tabs are actually available based on metadata
    const available = React.useMemo(() => {
        const t = transcripts || {};
        return [
            { key: "original" as const, label: "Original", enabled: !!t.original },
            { key: "edited" as const, label: "Edited", enabled: !!t.edited },
            { key: "redacted" as const, label: "Redacted", enabled: !!t.redacted },
        ].filter((o) => o.enabled);
    }, [transcripts]);

    // Initial tab selection logic
    const initialTab = React.useMemo<TranscriptVersion>(() => {
        const keys = available.map((a) => a.key);
        if (keys.includes("edited")) return "edited";
        if (keys.includes("original")) return "original";
        return "original";
    }, [available]);

    const [tab, setTab] = React.useState<TranscriptVersion>(initialTab);
    const [loading, setLoading] = React.useState(true);
    const [text, setText] = React.useState("");
    const [version, setVersion] = React.useState<TranscriptVersion>(tab);
    const [downloading, setDownloading] = React.useState(false);

    // Sync tab state if the initial calculation changes after data loads
    React.useEffect(() => {
        if (!tab && initialTab) setTab(initialTab);
    }, [initialTab, tab]);

    React.useEffect(() => {
        let alive = true;
        setLoading(true);

        fetchTranscript(api, id, tab)
            .then((t) => {
                if (!alive) return;
                const txt = t.text || "";
                setText(txt);
                setVersion(t.version || tab);
                onTextLoaded?.({
                    text: txt,
                    version: (t.version || tab) as TranscriptVersion,
                });
            })
            .finally(() => alive && setLoading(false));

        return () => { alive = false; };
    }, [api, id, tab, onTextLoaded]);

    // Choose which PII set to display based on the active tab
    const piiForView: PiiHit[] =
        tab === "redacted" ? [] : tab === "original" ? piiOriginal || [] : piiEdited || [];

    return (
        <Tabs value={tab} onValueChange={(v) => setTab(v as TranscriptVersion)} className="w-full">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <TabsList className="grid grid-cols-3 w-full max-w-md">
                    <TabsTrigger value="original" disabled={!available.find((a) => a.key === "original")?.enabled}>
                        Original
                    </TabsTrigger>
                    <TabsTrigger value="edited" disabled={!available.find((a) => a.key === "edited")?.enabled}>
                        Edited
                    </TabsTrigger>
                    <TabsTrigger value="redacted" disabled={!available.find((a) => a.key === "redacted")?.enabled}>
                        Redacted
                    </TabsTrigger>
                </TabsList>

                <div className="flex items-center justify-between sm:justify-end gap-3">
                    <div className="text-xs text-zinc-500 whitespace-nowrap">
                        {tab === "redacted"
                            ? "PII hidden"
                            : piiForView.length
                                ? `${piiForView.length} PII hits`
                                : "No PII hits"}
                    </div>

                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => downloadTextFile(`${id}_${tab}.txt`, text)}
                            disabled={!text?.trim() || loading}
                        >
                            Download
                        </Button>
                        <Button
                            variant="secondary"
                            size="sm"
                            onClick={async () => {
                                setDownloading(true);
                                for (const v of ["original", "edited", "redacted"] as const) {
                                    if (available.find(a => a.key === v)) {
                                        const t = await fetchTranscript(api, id, v);
                                        if (t.text) downloadTextFile(`${id}_${v}.txt`, t.text);
                                    }
                                }
                                setDownloading(false);
                            }}
                            disabled={downloading}
                        >
                            {downloading ? "Downloading..." : "Download all"}
                        </Button>
                    </div>
                </div>
            </div>

            <TabsContent value={tab} className="mt-4">
                {loading ? (
                    <div className="space-y-3">
                        <Skeleton className="h-4 w-2/3" /><Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-11/12" /><Skeleton className="h-4 w-4/5" />
                    </div>
                ) : (
                    <TranscriptViewer
                        id={id}
                        text={text}
                        version={version}
                        pii={piiForView}
                        readOnly={tab !== "edited"}
                        segments={segments ?? []}
                        onDeletePii={onDeletePii}
                        onAddPii={onAddPii}
                        onObfuscatePii={onObfuscatePii}
                    />
                )}
            </TabsContent>
        </Tabs>
    );
}