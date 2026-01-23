"use client";

import * as React from "react";
import Link from "next/link";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";

import ServerStatus from "@/components/shared/ServerStatus";
import AudioPlayer from "@/components/shared/AudioPlayer";
import RecordingActions from "@/components/recording/RecordingActions";
import TranscriptTabs from "@/components/transcript/TranscriptTabs";
import EditableTitle from "@/components/recording/TitleEditor";
import TranscriptEditor from "@/components/transcript/TranscriptEditor";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { formatDateTime } from "@/lib/format";

import BadgePill from "@/components/shared/BadgePill";
import TagsEditor from "@/components/recording/TagsEditor";
import ConfidencePane from "@/components/insights/ConfidencePane";
import SpeechPane from "@/components/insights/SpeechPane";

import type {
  RecordingData,
  TranscriptBlob,
  RecordingSegment,
  PiiHit,
} from "@/lib/recording.types";
import { Api } from "@/lib/api";

function asArray<T>(v: unknown): T[] { return Array.isArray(v) ? (v as T[]) : []; }
function asObject<T extends object>(v: unknown, fallback: T): T { return v && typeof v === "object" ? (v as T) : fallback; }

export default function RecordingClient({ api, id, initialData }: { api: string; id: string; initialData: RecordingData }) {
  const [data, setData] = React.useState<RecordingData>(initialData);
  const [refreshKey, setRefreshKey] = React.useState(0);
  const [currentText, setCurrentText] = React.useState("");
  const [processing, setProcessing] = React.useState(false);

  const [isObfuscateOpen, setIsObfuscateOpen] = React.useState(false);
  const [activePii, setActivePii] = React.useState<PiiHit | null>(null);
  const [replacementValue, setReplacementValue] = React.useState("");

  if (!data || !data.recording_id) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen text-center bg-zinc-50 dark:bg-zinc-950 p-6">
        <h1 className="text-2xl font-bold mb-2">Recording Not Found</h1>
        <p className="text-zinc-500 mb-6">The recording you are looking for does not exist or has been removed.</p>
        <Link href="/recordings">
          <Button variant="default">Return to Library</Button>
        </Link>
      </div>
    );
  }

  const transcripts: TranscriptBlob = asObject<TranscriptBlob>(data?.transcripts, {});
  const segments: RecordingSegment[] = asArray<RecordingSegment>(data?.segments);
  const piiList: PiiHit[] = asArray<PiiHit>(data?.pii_edited);
  const tags = asArray<string>(data?.tags);
  const piiCount = piiList.length;

  const refreshMeta = React.useCallback(async () => {
    try {
      const d = await Api.getRecording(id);
      if (!d || !d.recording_id) {
        setData({} as any);
        return;
      }
      setData(d);
    } catch (err) {
      toast.error("Failed to refresh recording data");
    }
  }, [id]);

  const syncPii = React.useCallback(async (newPii: PiiHit[]) => {
    try {
      await Api.syncPii(id, newPii);
      await refreshMeta();
    } catch (e) {
      throw new Error("Failed to sync PII");
    }
  }, [id, refreshMeta]);

  const saveTranscriptText = React.useCallback(async (text: string) => {
    try {
      await Api.saveEditedTranscript(id, text);
      setCurrentText(text);
      await refreshMeta();
    } catch (e) {
      throw new Error("Failed to save transcript");
    }
  }, [id, refreshMeta]);

  const onDeletePii = (hit: PiiHit) => {
    const next = piiList.filter(h => !(h.start_char === hit.start_char && h.end_char === hit.end_char));
    syncPii(next).then(() => setRefreshKey(k => k + 1)).catch(() => toast.error("Delete failed"));
  };

  const onAddPii = (newHit: PiiHit) => {
    const hitWithId = { ...newHit, recording_id: id };
    syncPii([...piiList, hitWithId]).then(() => setRefreshKey(k => k + 1)).catch(() => toast.error("Add failed"));
  };

  const onObfuscateClick = (hit: PiiHit) => {
    setActivePii(hit);
    setReplacementValue(hit.preview || "[REDACTED]");
    setIsObfuscateOpen(true);
  };

  const handleConfirmObfuscation = async () => {
    if (!activePii) return;
    setProcessing(true);

    const start = activePii.start_char ?? 0;
    const end = activePii.end_char ?? 0;
    const originalLength = end - start;
    const delta = replacementValue.length - originalLength;

    const before = currentText.slice(0, start);
    const after = currentText.slice(end);
    const updatedText = before + replacementValue + after;

    const nextPii = piiList
      .filter(h => !(h.start_char === start && h.end_char === end))
      .map(h => {
        if (h.start_char !== undefined && (h.start_char ?? 0) >= end) {
          return {
            ...h,
            start_char: (h.start_char ?? 0) + delta,
            end_char: (h.end_char ?? 0) + delta
          };
        }
        return h;
      });

    try {
      await saveTranscriptText(updatedText);
      await syncPii(nextPii);

      await Api.finalizeRecording(id, updatedText);

      toast.success("Text obfuscated and processed");
      await refreshMeta();
      setRefreshKey(k => k + 1);
    } catch (e) {
      toast.error("Obfuscation sync failed");
    } finally {
      setProcessing(false);
      setIsObfuscateOpen(false);
      setActivePii(null);
    }
  };

  const runProcessing = async () => {
    try {
      setProcessing(true);
      await Api.finalizeRecording(id, currentText);

      await refreshMeta();
      setRefreshKey((k) => k + 1);
      toast.success("Pipeline complete");
    } catch (e) {
      toast.error("Pipeline failed");
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <div className="mx-auto p-6 space-y-6">
        <div className="flex items-center justify-between">
          <Link
            href="/recordings"
            className="flex items-center gap-2 text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" /> Back to library
          </Link>
          <ServerStatus />
        </div>

        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <EditableTitle api={api} id={id} initialTitle={data?.title || ""} onSaved={refreshMeta} />
            <div className="text-sm text-zinc-500 mt-2">{formatDateTime(data?.created_at ?? undefined)}</div>
          </div>
          <div className="flex shrink-0 justify-start md:justify-end"><RecordingActions id={id} /></div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card className="shadow-sm border-zinc-200 dark:border-zinc-800">
              <CardHeader><CardTitle className="text-lg">Transcript</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <TranscriptTabs
                  key={refreshKey}
                  api={api}
                  id={id}
                  transcripts={transcripts}
                  piiOriginal={asArray<PiiHit>(data?.pii_original)}
                  piiEdited={asArray<PiiHit>(data?.pii_edited)}
                  segments={segments}
                  onTextLoaded={({ text }) => setCurrentText(text)}
                  onDeletePii={onDeletePii}
                  onAddPii={onAddPii}
                  onObfuscatePii={onObfuscateClick}
                />

                <div className="pt-4 border-t border-zinc-200 dark:border-zinc-800 space-y-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-xs text-zinc-500 max-w-md">
                      Manually editing the text? Run processing to update segments, prosody, and PII highlights.
                    </div>
                    <Button variant="secondary" size="sm" onClick={runProcessing} disabled={processing || !currentText.trim()}>
                      {processing ? "Processing…" : "Run Pipeline"}
                    </Button>
                  </div>
                  <TranscriptEditor api={api} id={id} initialText={currentText} onSaved={refreshMeta} />
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-sm border-zinc-200 dark:border-zinc-800">
              <CardHeader><CardTitle className="text-lg">Insights</CardTitle></CardHeader>
              <CardContent>
                <Tabs defaultValue="confidence">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="confidence">Confidence</TabsTrigger>
                    <TabsTrigger value="speech">Speech</TabsTrigger>
                  </TabsList>

                  <TabsContent value="confidence" className="mt-4">
                    <div className="max-h-[500px] overflow-y-auto rounded-md border p-4 bg-white dark:bg-zinc-900/50">
                      <ConfidencePane words={asArray<any>(data?.aligned_words)} />
                    </div>
                  </TabsContent>

                  <TabsContent value="speech" className="mt-4">
                    <SpeechPane speech={data?.speech ?? null} />
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="shadow-sm border-zinc-200 dark:border-zinc-800">
              <CardHeader><CardTitle className="text-lg">Audio Player</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <AudioPlayer src={`${api}/api/audio/${id}`} hasAudio={!!data?.has_audio} />
                <div className="flex flex-wrap gap-2">
                  {transcripts.original && <BadgePill text="original" />}
                  {transcripts.edited && <BadgePill text="edited" />}
                  {transcripts.redacted && <BadgePill text="redacted" />}
                  <BadgePill
                    text={piiCount ? `${piiCount} pii hits` : "no pii detected"}
                    variant={piiCount ? "destructive" : "secondary"}
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-sm border-zinc-200 dark:border-zinc-800">
              <CardHeader><CardTitle className="text-lg">Segments</CardTitle></CardHeader>
              <CardContent className="max-h-[400px] overflow-auto space-y-3 pr-2">
                {segments.length > 0 ? (
                  segments.map((s, i) => (
                    <div key={i} className="text-sm p-3 border border-zinc-100 dark:border-zinc-800 rounded bg-zinc-50 dark:bg-zinc-900/50">
                      <div className="font-bold text-[10px] uppercase tracking-wider text-zinc-400 mb-1">
                        {s.label || `Segment ${i + 1}`}
                      </div>
                      <div className="whitespace-pre-wrap leading-relaxed">{s.text}</div>
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-zinc-500 italic py-4">No segments generated yet.</div>
                )}
              </CardContent>
            </Card>

            <Card className="shadow-sm border-zinc-200 dark:border-zinc-800">
              <CardHeader><CardTitle className="text-lg">Recording Details</CardTitle></CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-zinc-500">Date Created</span>
                  <span className="font-medium text-zinc-700 dark:text-zinc-300">
                    {formatDateTime(data?.created_at ?? undefined)}
                  </span>
                </div>
                <div className="pt-2">
                  <div className="text-xs font-semibold text-zinc-400 uppercase mb-2">Labels & Tags</div>
                  <TagsEditor id={id} tags={tags} onSaved={refreshMeta} />
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Obfuscation/Redaction Dialog */}
      <Dialog open={isObfuscateOpen} onOpenChange={setIsObfuscateOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Modify Transcript Text</DialogTitle>
            <DialogDescription>
              Replace "{activePii?.preview}" with the text below. All following highlights will be automatically shifted to maintain alignment.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <label className="text-xs font-medium text-zinc-500 mb-1.5 block">Replacement Text</label>
            <Input
              value={replacementValue}
              onChange={(e) => setReplacementValue(e.target.value)}
              placeholder="e.g. [REDACTED] or a pseudonym"
              onKeyDown={(e) => e.key === 'Enter' && handleConfirmObfuscation()}
              autoFocus
              className="bg-zinc-50 dark:bg-zinc-900"
            />
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="ghost" onClick={() => setIsObfuscateOpen(false)} disabled={processing}>Cancel</Button>
            <Button onClick={handleConfirmObfuscation} disabled={processing || !replacementValue.trim()}>
              {processing ? "Updating..." : "Update & Reprocess"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}