"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { API } from "@/lib/api";

import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

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
  if (name === "NotAllowedError") return "Microphone permission denied. Allow it in your browser settings.";
  if (name === "NotFoundError") return "No microphone found. Plug one in or enable it.";
  if (name === "NotReadableError") return "Microphone is in use by another app (Teams/Zoom/etc.).";
  return err?.message || "Microphone access failed.";
}

export default function UploadPage() {
  const router = useRouter();

  // ---- Upload tab state ----
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [statusText, setStatusText] = useState<string | null>(null);

  // ---- Record tab state ----
  const [recording, setRecording] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [micError, setMicError] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);

  // ---- Write tab state ----
  const [text, setText] = useState("");
  const [creatingTextEntry, setCreatingTextEntry] = useState(false);

  // Preview URL for recorded audio (avoid leaks)
  const previewUrl = useMemo(() => {
    if (!recordedBlob) return null;
    return URL.createObjectURL(recordedBlob);
  }, [recordedBlob]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => {
    return () => {
      // cleanup on unmount
      try {
        mediaRecorderRef.current?.stop();
      } catch {}
      streamRef.current?.getTracks().forEach((t) => t.stop());
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, []);

  const resetErrors = () => {
    setUploadError(null);
    setMicError(null);
    setStatusText(null);
  };

  // Shared uploader
  const upload = async (uploadFile: File) => {
    const validation = validateAudioFile(uploadFile);
    if (validation) {
      setUploadError(validation);
      return;
    }

    resetErrors();
    setStatusText("Uploading audio…");
    setUploading(true);

    const formData = new FormData();
    formData.append("file", uploadFile);
    formData.append("language", "en");

    let res: Response;
    try {
      res = await fetch(`${API}/api/recordings/upload`, { method: "POST", body: formData });
    } catch (e: any) {
      setUploading(false);
      setStatusText(null);
      setUploadError(e?.message || "Network error while uploading.");
      return;
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      setUploading(false);
      setStatusText(null);
      setUploadError(err?.detail || "Upload failed.");
      return;
    }

    setStatusText("Starting processing…");
    const data = await res.json().catch(() => null);

    setUploading(false);
    setStatusText(null);

    if (!data?.recording_id) {
      setUploadError("Upload succeeded, but server returned no recording_id.");
      return;
    }

    router.push(`/editor/${data.recording_id}`);
  };

  // ---- Upload handlers ----
  const handleUploadFile = async () => {
    if (!file || uploading || recording || creatingTextEntry) return;
    await upload(file);
  };

  // ---- Recording handlers ----
  const startRecording = async () => {
    if (uploading || creatingTextEntry) return;

    resetErrors();
    setRecordedBlob(null);
    setSeconds(0);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        } as any,
      });

      streamRef.current = stream;

      const mr = new MediaRecorder(stream);
      mediaRecorderRef.current = mr;
      chunksRef.current = [];

      mr.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
      };

      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mr.mimeType || "audio/webm" });
        setRecordedBlob(blob);

        // stop mic
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      };

      mr.start();
      setRecording(true);

      timerRef.current = window.setInterval(() => {
        setSeconds((s) => s + 1);
      }, 1000);
    } catch (err: any) {
      setMicError(humanMicError(err));
    }
  };

  const stopRecording = () => {
    const mr = mediaRecorderRef.current;
    if (!mr) return;

    try {
      mr.stop();
    } catch {}

    setRecording(false);
    if (timerRef.current) window.clearInterval(timerRef.current);
    timerRef.current = null;
  };

  const discardRecording = () => {
    setRecordedBlob(null);
    setSeconds(0);
    setMicError(null);
  };

  const handleUploadRecording = async () => {
    if (!recordedBlob || uploading || creatingTextEntry) return;

    const recordedFile = new File([recordedBlob], `recording_${Date.now()}.webm`, {
      type: recordedBlob.type || "audio/webm",
    });

    await upload(recordedFile);
  };

  // ---- Text entry handler (frontend only for now) ----
  const handleCreateTextEntry = async () => {
    const res = await fetch(`${API}/api/recordings/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data?.detail || "Failed to create text entry");
    router.push(`/editor/${data.recording_id}`);

  };

  return (
    <div className="min-h-screen w-full bg-zinc-50">
      <div className="mx-auto max-w-3xl p-6 md:p-10 space-y-4">
        <Link href="/" className="text-sm text-zinc-600 hover:underline">
          ← Back to home
        </Link>

        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>New Entry</CardTitle>
            <CardDescription>
              Upload audio, record in-app, or just type. Humans love options.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {(uploadError || micError || statusText) && (
              <Alert>
                <AlertTitle>Status</AlertTitle>
                <AlertDescription className="space-y-1">
                  {statusText && <div>{statusText}</div>}
                  {uploadError && <div className="text-red-600">{uploadError}</div>}
                  {micError && <div className="text-red-600">{micError}</div>}
                </AlertDescription>
              </Alert>
            )}

            <Tabs defaultValue="upload" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="upload" disabled={recording || uploading || creatingTextEntry}>
                  Upload
                </TabsTrigger>
                <TabsTrigger value="record" disabled={uploading || creatingTextEntry}>
                  Record
                </TabsTrigger>
                <TabsTrigger value="write" disabled={recording || uploading}>
                  Write
                </TabsTrigger>
              </TabsList>

              {/* UPLOAD */}
              <TabsContent value="upload" className="space-y-3 pt-3">
                <div className="text-sm font-semibold">Upload audio</div>

                <Input
                  type="file"
                  accept="audio/*"
                  disabled={uploading || recording || creatingTextEntry}
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />

                <div className="text-xs text-zinc-500">
                  Accepted: audio files. Max {MAX_FILE_MB}MB.
                </div>

                <Button
                  onClick={handleUploadFile}
                  disabled={!file || uploading || recording || creatingTextEntry}
                  className="w-full"
                >
                  {uploading ? "Processing…" : "Upload & Process"}
                </Button>
              </TabsContent>

              {/* RECORD */}
              <TabsContent value="record" className="space-y-3 pt-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold">Record audio</div>
                  <div className="text-xs text-zinc-500">
                    {recording ? `Recording: ${formatTime(seconds)}` : recordedBlob ? `Recorded: ${formatTime(seconds)}` : ""}
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    onClick={startRecording}
                    disabled={recording || uploading || creatingTextEntry}
                    className="flex-1"
                  >
                    Start
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={stopRecording}
                    disabled={!recording || uploading || creatingTextEntry}
                    className="flex-1"
                  >
                    Stop
                  </Button>
                </div>

                {recordedBlob && (
                  <div className="space-y-3 rounded-lg border bg-white p-3">
                    {previewUrl && <audio controls src={previewUrl} className="w-full" />}

                    <div className="flex gap-2">
                      <Button
                        onClick={handleUploadRecording}
                        disabled={uploading || creatingTextEntry}
                        className="flex-1"
                      >
                        {uploading ? "Processing…" : "Use this recording"}
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={discardRecording}
                        disabled={uploading || creatingTextEntry}
                      >
                        Discard
                      </Button>
                    </div>
                  </div>
                )}
              </TabsContent>

              {/* WRITE */}
              <TabsContent value="write" className="space-y-3 pt-3">
                <div className="text-sm font-semibold">Write entry</div>

                <Textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Type your journal entry here…"
                  className="min-h-[180px]"
                  disabled={creatingTextEntry || uploading || recording}
                />

                <div className="flex items-center justify-between text-xs text-zinc-500">
                  <span>{text.trim().length} characters</span>
                  <button
                    type="button"
                    className="hover:underline"
                    onClick={() => setText("")}
                    disabled={creatingTextEntry || uploading || recording || !text}
                  >
                    Clear
                  </button>
                </div>

                <Button
                  onClick={handleCreateTextEntry}
                  disabled={creatingTextEntry || uploading || recording || !text.trim()}
                  className="w-full"
                >
                  Create entry
                </Button>

                <div className="text-xs text-zinc-500">
                  This will create an entry without audio.
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}