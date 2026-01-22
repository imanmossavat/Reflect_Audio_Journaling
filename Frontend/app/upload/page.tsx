"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { API } from "@/lib/api";
import WaveformVisualizer from "@/components/WaveformVisualizer";

import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Mic, Square, Trash2, Check, ArrowLeft } from "lucide-react";

const MAX_FILE_MB = 200;
const ACCEPTED_MIME_PREFIX = "audio/";

function formatTime(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function validateAudioFile(f: File) {
  if (!f) return "No file selected.";
  if (!f.type?.startsWith(ACCEPTED_MIME_PREFIX)) return "That doesn’t look like an audio file.";
  const mb = f.size / (1024 * 1024);
  if (mb > MAX_FILE_MB) return `File is too large (${mb.toFixed(1)}MB). Max is ${MAX_FILE_MB}MB.`;
  return null;
}

function humanMicError(err: any) {
  const name = err?.name;
  if (name === "NotAllowedError") return "Microphone permission denied.";
  if (name === "NotFoundError") return "No microphone found.";
  return err?.message || "Microphone access failed.";
}

/**
 * The inner content that handles the search params logic
 */
function UploadPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Sync tab with URL: ?tab=record or ?tab=write
  const defaultTab = searchParams.get("tab") || "upload";

  // State
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [statusText, setStatusText] = useState<string | null>(null);

  const [recording, setRecording] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [micError, setMicError] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(0);

  const [text, setText] = useState("");
  const [creatingTextEntry, setCreatingTextEntry] = useState(false);

  // Refs for recording logic
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const previewUrl = useMemo(() => {
    if (!recordedBlob) return null;
    return URL.createObjectURL(recordedBlob);
  }, [recordedBlob]);

  useEffect(() => {
    return () => { if (previewUrl) URL.revokeObjectURL(previewUrl); };
  }, [previewUrl]);

  const stopTracks = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  };

  const resetErrors = () => {
    setUploadError(null);
    setMicError(null);
    setStatusText(null);
  };

  const upload = async (uploadFile: File) => {
    const validation = validateAudioFile(uploadFile);
    if (validation) { setUploadError(validation); return; }

    resetErrors();
    setStatusText("Uploading and analyzing audio...");
    setUploading(true);

    const formData = new FormData();
    formData.append("file", uploadFile);
    formData.append("language", "en");

    try {
      const res = await fetch(`${API}/api/recordings/upload`, { method: "POST", body: formData });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || "Upload failed.");
      }
      const data = await res.json();
      router.push(`/editor/${data.recording_id}`);
    } catch (e: any) {
      setUploadError(e.message);
      setUploading(false);
    }
  };

  const startRecording = async () => {
    resetErrors();
    setRecordedBlob(null);
    setSeconds(0);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mr = new MediaRecorder(stream);
      mediaRecorderRef.current = mr;
      chunksRef.current = [];

      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mr.mimeType || "audio/webm" });
        setRecordedBlob(blob);
        stopTracks();
      };

      mr.start();
      setRecording(true);
      timerIntervalRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    } catch (err: any) {
      setMicError(humanMicError(err));
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
      setRecording(false);
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    }
  };

  const handleCreateTextEntry = async () => {
    if (!text.trim()) return;
    setCreatingTextEntry(true);
    resetErrors();

    try {
      const res = await fetch(`${API}/api/recordings/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Failed to create entry");
      router.push(`/editor/${data.recording_id}`);
    } catch (e: any) {
      setUploadError(e.message);
      setCreatingTextEntry(false);
    }
  };

  return (
      <div className="mx-auto max-w-3xl p-6 md:p-10 space-y-4">
        <Link href="/" className="text-sm text-zinc-600 hover:text-zinc-900 flex items-center gap-1 dark:text-zinc-400 dark:hover:text-zinc-100 transition-colors">
          <ArrowLeft className="h-3 w-3" /> Back to library
        </Link>

        <Card className="shadow-sm border-zinc-200 dark:border-zinc-800 overflow-hidden">
          <CardHeader className="bg-white dark:bg-zinc-900 border-b border-zinc-100 dark:border-zinc-800 pb-8">
            <CardTitle className="text-2xl font-bold">New Recording</CardTitle>
            <CardDescription>Choose how you want to capture your thoughts today.</CardDescription>
          </CardHeader>

          <CardContent className="space-y-4 pt-6">
            {(uploadError || micError || statusText) && (
                <Alert variant={uploadError || micError ? "destructive" : "default"} className="animate-in fade-in zoom-in duration-200">
                  <AlertDescription className="flex items-center gap-2">
                    {(uploading || statusText) && !uploadError && <Loader2 className="h-4 w-4 animate-spin" />}
                    {statusText || uploadError || micError}
                  </AlertDescription>
                </Alert>
            )}

            <Tabs defaultValue={defaultTab} className="w-full">
              <TabsList className="grid w-full grid-cols-3 bg-zinc-100 dark:bg-zinc-900">
                <TabsTrigger value="upload" disabled={recording || uploading}>Upload</TabsTrigger>
                <TabsTrigger value="record" disabled={uploading}>Record</TabsTrigger>
                <TabsTrigger value="write" disabled={recording || uploading}>Write</TabsTrigger>
              </TabsList>

              {/* --- UPLOAD TAB --- */}
              <TabsContent value="upload" className="space-y-4 pt-4">
                <div className="flex flex-col items-center justify-center border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-xl p-8 transition-colors hover:border-zinc-300 dark:hover:border-zinc-700">
                  <Input
                      type="file"
                      accept="audio/*"
                      id="audio-upload"
                      className="hidden"
                      disabled={uploading}
                      onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                  <label htmlFor="audio-upload" className="cursor-pointer flex flex-col items-center gap-2 text-center">
                    <div className="p-3 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
                      {file ? <Check className="h-6 w-6 text-green-500" /> : <Mic className="h-6 w-6" />}
                    </div>
                    <span className="text-sm font-medium">{file ? file.name : "Click to select audio file"}</span>
                    <span className="text-xs text-zinc-500">WAV, MP3, M4A or WebM up to {MAX_FILE_MB}MB</span>
                  </label>
                </div>

                <Button onClick={() => file && upload(file)} disabled={!file || uploading} className="w-full h-11">
                  {uploading ? "Uploading..." : "Process Audio"}
                </Button>
              </TabsContent>

              {/* --- RECORD TAB --- */}
              <TabsContent value="record" className="space-y-4 pt-4">
                <div className="flex flex-col gap-4 p-6 bg-zinc-100 dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {recording && <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />}
                      <span className="text-sm font-medium">
                      {recording ? "Recording live..." : recordedBlob ? "Recording ready" : "Ready to record"}
                    </span>
                    </div>
                    <span className="font-mono text-2xl font-bold tracking-tighter">{formatTime(seconds)}</span>
                  </div>

                  {recording && <WaveformVisualizer stream={streamRef.current} />}
                </div>

                <div className="flex gap-3">
                  {!recording ? (
                      <Button onClick={startRecording} className="flex-1 h-12 bg-red-600 hover:bg-red-700 text-white gap-2 font-bold shadow-lg shadow-red-900/20">
                        <Mic className="h-4 w-4" /> Start
                      </Button>
                  ) : (
                      <Button onClick={stopRecording} variant="secondary" className="flex-1 h-12 gap-2 font-bold border-2 border-zinc-200 dark:border-zinc-800">
                        <Square className="h-4 w-4 fill-current" /> Stop
                      </Button>
                  )}
                </div>

                {recordedBlob && !recording && (
                    <div className="space-y-4 pt-2 animate-in slide-in-from-bottom-2 duration-300">
                      <audio controls src={previewUrl!} className="w-full h-10" />
                      <div className="flex gap-2">
                        <Button onClick={() => upload(new File([recordedBlob], "mic_record.webm"))} className="flex-1 h-11" disabled={uploading}>
                          {uploading ? "Processing..." : "Use this recording"}
                        </Button>
                        <Button variant="outline" size="icon" className="h-11 w-11 shrink-0" onClick={() => setRecordedBlob(null)} disabled={uploading}>
                          <Trash2 className="h-4 w-4 text-zinc-500" />
                        </Button>
                      </div>
                    </div>
                )}
              </TabsContent>

              {/* --- WRITE TAB --- */}
              <TabsContent value="write" className="space-y-4 pt-4">
                <Textarea
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Start writing your thoughts..."
                    className="min-h-[250px] bg-zinc-50 dark:bg-zinc-900/50 resize-none focus-visible:ring-red-500"
                />
                <div className="flex justify-between items-center px-1">
                  <span className="text-[10px] uppercase font-bold text-zinc-400 tracking-widest">{text.length} Characters</span>
                  <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs text-zinc-500"
                      onClick={() => setText("")}
                      disabled={!text}
                  >Clear</Button>
                </div>
                <Button onClick={handleCreateTextEntry} disabled={!text.trim() || creatingTextEntry} className="w-full h-11">
                  {creatingTextEntry ? "Saving Entry..." : "Create Text Entry"}
                </Button>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
  );
}

/**
 * Main export with Suspense boundary
 */
export default function UploadPage() {
  return (
      <div className="min-h-screen w-full bg-zinc-50 dark:bg-zinc-950">
        <Suspense fallback={
          <div className="flex items-center justify-center min-h-screen">
            <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
          </div>
        }>
          <UploadPageContent />
        </Suspense>
      </div>
  );
}