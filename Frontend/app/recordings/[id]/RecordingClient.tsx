"use client";

import * as React from "react";
import AudioPlayer from "@/app/components/AudioPlayer";
import RecordingActions from "@/app/components/RecordingActions";
import TranscriptTabs from "@/app/components/TranscriptTabs";
import EditableTitle from "@/app/components/TitleEditor";
import TranscriptEditor from "@/app/components/TranscriptEditor";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { formatDateTime } from "@/lib/format";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import AlignedTranscript from "@/app/components/AlignedTranscript";
import ProsodySummary from "@/app/components/ProsodySummary";

function badge(text: string, key?: React.Key) {
    return (
        <span
            key={key}
            className="text-xs px-2 py-1 rounded border border-zinc-200 dark:border-zinc-800 bg-white/60 dark:bg-zinc-900/40"
        >
      {text}
    </span>
    );
}


function normalizeTagsFromString(s: string): string[] {
    const raw = s
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean);

    // unique (case-insensitive), keep original casing of first occurrence
    const seen = new Set<string>();
    const out: string[] = [];
    for (const t of raw) {
        const key = t.toLowerCase();
        if (seen.has(key)) continue;
        seen.add(key);
        out.push(t);
    }
    return out;
}

function ConfidencePane({ words }: { words: any[] }) {
  const [onlyLow, setOnlyLow] = React.useState(false);

  if (!words?.length) {
    return <div className="text-sm text-zinc-500">No aligned words saved.</div>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-xs text-zinc-500">Highlight low-confidence words</div>
        <Switch checked={onlyLow} onCheckedChange={setOnlyLow} />
      </div>

      <div className="rounded border border-zinc-200 dark:border-zinc-800 p-3 bg-white/50 dark:bg-zinc-900/30 max-h-[320px] overflow-auto">
        <AlignedTranscript words={words} highlightBelow={0.8} onlyLow={onlyLow} />
      </div>

      <div className="text-xs text-zinc-500">
        Tip: low-confidence often signals mumbling, noise, or weird named entities.
      </div>
    </div>
  );
}


export default function RecordingClient({
                                            api,
                                            id,
                                            initialData,
                                        }: {
    api: string;
    id: string;
    initialData: any;
}) {
    const [data, setData] = React.useState(initialData);
    const [refreshKey, setRefreshKey] = React.useState(0);
    const [currentText, setCurrentText] = React.useState("");
    const [activeVersion, setActiveVersion] = React.useState<"original" | "edited" | "redacted" | null>(null);

    // --- tags editor state
    const [tagsInput, setTagsInput] = React.useState("");
    const [savingTags, setSavingTags] = React.useState(false);
    const [tagsError, setTagsError] = React.useState<string | null>(null);
    const [finalizing, setFinalizing] = React.useState(false);

    async function runProcessing() {
      try {
        setFinalizing(true);

        // pak currentText (die jij al bijhoudt via TranscriptTabs)
        const form = new FormData();
        form.append("recording_id", id);
        form.append("edited_transcript", currentText);

        const res = await fetch(`${api}/api/recordings/finalize`, {
          method: "POST",
          body: form,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err?.detail || "Finalize failed");
        }

        await refreshMeta();
        setRefreshKey((k) => k + 1);
      } catch (e: any) {
        alert(e?.message || "Finalize failed");
      } finally {
        setFinalizing(false);
      }
    }

    async function refreshMeta() {
        const r = await fetch(`${api}/api/recordings/${id}`, { cache: "no-store" });
        const d = await r.json();
        setData(d);
    }

    // keep input synced when data loads/changes
    React.useEffect(() => {
        const existing = Array.isArray(data?.tags) ? data.tags : [];
        setTagsInput(existing.join(", "));
    }, [data?.tags]);

    async function saveTags() {
        setTagsError(null);
        setSavingTags(true);

        try {
            const tags = normalizeTagsFromString(tagsInput);

            const res = await fetch(`${api}/api/recordings/${id}/meta`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tags }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err?.detail || "Failed to update tags");
            }

            const out = await res.json();

            // update local state immediately
            setData((prev: any) => ({
                ...prev,
                tags: out?.tags ?? tags,
            }));
        } catch (e: any) {
            setTagsError(e?.message || "Something went wrong");
        } finally {
            setSavingTags(false);
        }
    }

    async function downloadTranscript(version: "original" | "edited" | "redacted") {
        try {
            const res = await fetch(`${api}/api/recordings/${id}/transcript?version=${version}`, {
                cache: "no-store",
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err?.detail || `Failed to fetch ${version} transcript`);
            }

            const data = await res.json();
            const text: string = data?.text ?? "";

            if (!text.trim()) {
                throw new Error(`No ${version} transcript available`);
            }

            const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
            const url = URL.createObjectURL(blob);

            const a = document.createElement("a");
            a.href = url;
            a.download = `${id}_${version}.txt`;
            document.body.appendChild(a);
            a.click();
            a.remove();

            URL.revokeObjectURL(url);
        } catch (e: any) {
            alert(e?.message || "Download failed");
        }
    }

    const t = data?.transcripts || {};
    const hasOriginal = !!t.original;
    const hasEdited = !!t.edited;
    const hasRedacted = !!t.redacted;
    const piiCount = (data?.pii || []).length;

    return (
        <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
            <div className="mx-auto p-6 space-y-3">
                <Link
                    href="/recordings"
                    className="text-sm text-zinc-600 hover:underline dark:text-zinc-400"
                >
                    ← Back to library
                </Link>

                {/* Top bar */}
                <div className="flex flex-col gap-3 mt-3 md:flex-row md:items-start md:justify-between">
                    <div className="min-w-0">
                        <EditableTitle
                            api={api}
                            id={id}
                            initialTitle={data?.title || ""}
                            onSaved={() => refreshMeta()}
                        />
                        <div className="text-sm text-zinc-500 mt-2">{formatDateTime(data?.created_at)}</div>
                    </div>

                    <div className="flex shrink-0 justify-start md:justify-end">
                        <RecordingActions id={id} />
                    </div>
                </div>

                {/* Main grid */}
                <div className=" gap-6">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                      {/* Main content */}
                      <div className="lg:col-span-2 space-y-6">
                        <Card className="shadow-sm">
                          <CardHeader>
                            <CardTitle className="text-lg">Transcript</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            <TranscriptTabs
                              key={refreshKey}
                              api={api}
                              id={id}
                              transcripts={data?.transcripts}
                              piiOriginal={data?.pii_original || data?.pii || []}
                              piiEdited={data?.pii_edited || []}
                              segments={data?.segments || []}
                              onTextLoaded={({ text, version }) => {
                                if (version === "redacted") return;
                                setCurrentText(text);
                              }}
                            />

                            <div className="pt-2 border-t border-zinc-200 dark:border-zinc-800 space-y-3">
                              <div className="flex items-center justify-between gap-3">
                                <div className="text-xs text-zinc-500">
                                  Processing updates segments + PII from the current transcript.
                                </div>

                                <Button
                                  variant="secondary"
                                  size="sm"
                                  onClick={runProcessing}
                                  disabled={finalizing || !currentText.trim()}
                                >
                                  {finalizing ? "Running…" : "Run processing"}
                                </Button>
                              </div>

                              <TranscriptEditor
                                api={api}
                                id={id}
                                initialText={currentText}
                                onSaved={async () => {
                                  await refreshMeta();
                                  setRefreshKey((k) => k + 1);
                                }}
                              />
                            </div>
                          </CardContent>
                        </Card>

                        {/* ✅ Insights BELOW Transcript */}
                        <Card className="shadow-sm">
                          <CardHeader>
                            <CardTitle className="text-lg">Insights</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-3">
                            <Tabs defaultValue="confidence">
                              <TabsList className="grid w-full grid-cols-2">
                                <TabsTrigger value="confidence">Confidence</TabsTrigger>
                                <TabsTrigger value="prosody">Prosody</TabsTrigger>
                              </TabsList>

                              <TabsContent value="confidence" className="space-y-3">
                                <ConfidencePane words={data?.aligned_words || []} />
                              </TabsContent>

                              <TabsContent value="prosody" className="space-y-3">
                                <ProsodySummary prosody={data?.prosody || []} segments={data?.segments || []} />
                              </TabsContent>
                            </Tabs>
                          </CardContent>
                        </Card>
                      </div>

                      {/* Sidebar */}
                      <div className="space-y-6">
                        {/* Audio */}
                        <Card className="shadow-sm">
                          <CardHeader>
                            <CardTitle className="text-lg">Audio</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            <AudioPlayer src={`${api}/api/audio/${id}`} hasAudio={!!data?.has_audio} />
                            <div className="flex flex-wrap gap-2">
                              {hasOriginal && badge("original")}
                              {hasEdited && badge("edited")}
                              {hasRedacted && badge("redacted")}
                              {!!piiCount && badge(`${piiCount} pii`)}
                              {!piiCount && badge("no pii")}
                            </div>
                          </CardContent>
                        </Card>

                        {/* Segments */}
                        <Card className="shadow-sm">
                          <CardHeader>
                            <CardTitle className="text-lg">Segments</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-3">
                            {!!data?.segments?.length ? (
                              <div className="space-y-2 max-h-[420px] overflow-auto pr-1">
                                {data.segments.map((s: any, i: number) => (
                                  <div key={i} className="rounded border border-zinc-200 dark:border-zinc-800 p-3">
                                    <div className="text-sm font-semibold">{s.label || `Segment ${i + 1}`}</div>
                                    <div className="text-sm text-zinc-600 dark:text-zinc-300 mt-1 whitespace-pre-wrap">
                                      {s.text}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div className="text-sm text-zinc-500">No segments yet.</div>
                            )}
                          </CardContent>
                        </Card>

                        {/* Details */}
                        <Card className="shadow-sm">
                          <CardHeader>
                            <CardTitle className="text-lg">Details</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-3 text-sm">
                            <div className="flex items-center justify-between gap-3">
                                    <span className="text-zinc-500">Recording ID</span>
                                    <span className="font-mono text-xs">{id}</span>
                                </div>

                                <div className="flex items-center justify-between gap-3">
                                    <span className="text-zinc-500">Created</span>
                                    <span className="text-right">{formatDateTime(data?.created_at)}</span>
                                </div>

                                <div className="flex items-center justify-between gap-3">
                                    <span className="text-zinc-500">Segments</span>
                                    <span>{(data?.segments || []).length}</span>
                                </div>

                                <div className="flex items-center justify-between gap-3">
                                    <span className="text-zinc-500">PII hits</span>
                                    <span>{piiCount}</span>
                                </div>

                                {/* ✅ Tags editor */}
                                <div className="pt-2">
                                    <div className="text-zinc-500 mb-2">Tags</div>

                                    <div className="space-y-2">
                                        <Input
                                            value={tagsInput}
                                            onChange={(e) => setTagsInput(e.target.value)}
                                            placeholder="e.g. school, anxiety, plans"
                                        />

                                        <div className="flex gap-2">
                                            <Button onClick={saveTags} disabled={savingTags}>
                                                {savingTags ? "Saving..." : "Save tags"}
                                            </Button>
                                            <Button
                                                variant="secondary"
                                                onClick={() => setTagsInput((Array.isArray(data?.tags) ? data.tags : []).join(", "))}
                                                disabled={savingTags}
                                            >
                                                Reset
                                            </Button>
                                        </div>

                                        {tagsError && <div className="text-xs text-red-600">{tagsError}</div>}

                                        {!!data?.tags?.length && (
                                            <div className="flex flex-wrap gap-2 pt-1">
                                                {data.tags.map((tg: string) => badge(tg, tg))}
                                            </div>
                                        )}
                                        {!data?.tags?.length && (
                                            <div className="text-xs text-zinc-500">No tags yet.</div>
                                        )}
                                    </div>
                                </div>
                          </CardContent>
                        </Card>
                      </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
