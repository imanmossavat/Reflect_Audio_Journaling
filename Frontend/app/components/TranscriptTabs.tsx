"use client";

import * as React from "react";
import TranscriptViewer from "@/app/components/TranscriptViewer";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

type PiiHit = {
    start_char: number;
    end_char: number;
    label?: string;
};

async function fetchTranscript(api: string, id: string, version: string) {
    const r = await fetch(`${api}/api/recordings/${id}/transcript?version=${version}`, {
        cache: "no-store",
    });
    if (!r.ok) return { text: "", version };
    const data = await r.json();
    return { text: data?.text ?? "", version: data?.version ?? version };
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
                                       }: {
    api: string;
    id: string;
    transcripts?: { original?: string | null; edited?: string | null; redacted?: string | null };
    piiOriginal?: PiiHit[];
    piiEdited?: PiiHit[];
    segments?: any[];
    onTextLoaded?: (payload: { text: string; version: string }) => void;
}) {
    const available = React.useMemo(() => {
        const t = transcripts || {};
        const options = [
            { key: "original", label: "Original", enabled: !!t.original },
            { key: "edited", label: "Edited", enabled: !!t.edited },
            { key: "redacted", label: "Redacted", enabled: !!t.redacted },
        ].filter((o) => o.enabled);

        return options.length
            ? options
            : [
                { key: "original", label: "Original", enabled: true },
                { key: "edited", label: "Edited", enabled: true },
                { key: "redacted", label: "Redacted", enabled: true },
            ];
    }, [transcripts]);

    const defaultTab = React.useMemo(() => {
        const keys = available.map((a) => a.key);
        if (keys.includes("edited")) return "edited";
        if (keys.includes("original")) return "original";
        return keys[0] || "original";
    }, [available]);

    const [tab, setTab] = React.useState(defaultTab);
    const [loading, setLoading] = React.useState(true);
    const [text, setText] = React.useState("");
    const [version, setVersion] = React.useState(tab);
    const [downloading, setDownloading] = React.useState(false);

    // if defaultTab changes because transcripts loaded later, sync it once
    React.useEffect(() => {
        setTab((prev) => (prev ? prev : defaultTab));
    }, [defaultTab]);

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
                    version: t.version || tab,
                });
            })
            .finally(() => alive && setLoading(false));

        return () => {
            alive = false;
        };
    }, [api, id, tab, onTextLoaded]);

    const piiForView =
        tab === "redacted" ? [] : tab === "original" ? piiOriginal || [] : piiEdited || [];

    async function handleDownloadCurrent() {
        // use already loaded text to avoid extra fetch
        if (!text?.trim()) return;
        downloadTextFile(`${id}_${tab}.txt`, text);
    }

    async function handleDownloadAll() {
        setDownloading(true);
        try {
            // sequential fetches so you don't DDOS yourself locally
            for (const v of ["original", "edited", "redacted"] as const) {
                // only download if enabled/available
                const isEnabled = !!available.find((a) => a.key === v)?.enabled;
                if (!isEnabled) continue;

                const t = await fetchTranscript(api, id, v);
                if (t.text?.trim()) {
                    downloadTextFile(`${id}_${v}.txt`, t.text);
                }
            }
        } finally {
            setDownloading(false);
        }
    }

    const canDownloadCurrent = !!text?.trim() && !loading;

    return (
        <Tabs value={tab} onValueChange={setTab} className="w-full">
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
                            onClick={handleDownloadCurrent}
                            disabled={!canDownloadCurrent}
                        >
                            Download
                        </Button>

                        <Button
                            variant="secondary"
                            size="sm"
                            onClick={handleDownloadAll}
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
                        <Skeleton className="h-4 w-2/3" />
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-11/12" />
                        <Skeleton className="h-4 w-4/5" />
                    </div>
                ) : (
                    <TranscriptViewer text={text} version={version} pii={piiForView} segments={segments} />
                )}
            </TabsContent>
        </Tabs>
    );
}
