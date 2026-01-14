"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { API } from "@/lib/api";
import Link from "next/link";

export default function UploadPage() {
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);

    // recording state
    const [recording, setRecording] = useState(false);
    const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
    const [micError, setMicError] = useState<string | null>(null);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<BlobPart[]>([]);
    const streamRef = useRef<MediaStream | null>(null);

    const router = useRouter();

    useEffect(() => {
        return () => {
            // cleanup on unmount
            try {
                mediaRecorderRef.current?.stop();
            } catch {}
            streamRef.current?.getTracks().forEach(t => t.stop());
        };
    }, []);

    const startRecording = async () => {
        setMicError(null);
        setRecordedBlob(null);

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
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
                stream.getTracks().forEach(t => t.stop());
                streamRef.current = null;
            };

            mr.start();
            setRecording(true);
        } catch (e: any) {
            setMicError(e?.message || "Microphone access denied");
        }
    };

    const stopRecording = async () => {
        const mr = mediaRecorderRef.current;
        if (!mr) return;

        try {
            mr.stop();
        } catch {}
        setRecording(false);
    };

    const upload = async (uploadFile: File) => {
        setLoading(true);

        const formData = new FormData();
        formData.append("file", uploadFile);
        formData.append("language", "en");

        const res = await fetch(`${API}/api/recordings/upload`, { method: "POST", body: formData });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert(err?.detail || "Upload failed");
            setLoading(false);
            return;
        }

        const data = await res.json();
        setLoading(false);
        router.push(`/editor/${data.recording_id}`);
    };

    const handleUploadFile = async () => {
        if (!file) return;
        await upload(file);
    };

    const handleUploadRecording = async () => {
        if (!recordedBlob) return;

        // turn blob into File
        const recordedFile = new File([recordedBlob], `recording_${Date.now()}.webm`, {
            type: recordedBlob.type || "audio/webm",
        });

        await upload(recordedFile);
    };

    return (
        <div className="p-10 space-y-6 bg-zinc-50 w-screen h-screen mx-auto">
            <div className="space-y-2 max-w-3xl mx-auto">
                <Link
                    href="/"
                    className="text-sm text-zinc-600 hover:underline dark:text-zinc-400"
                >
                    ← Back to home
                </Link>
                <Card className="shadow-sm mt-10 mx-auto">
                    <CardHeader>
                        <CardTitle>New Recording</CardTitle>
                        <CardDescription>Upload an audio file or record inside the app.</CardDescription>
                    </CardHeader>

                    <CardContent className="space-y-6">
                        <div className="space-y-3">
                            <div className="font-semibold">Upload audio</div>
                            <Input
                                type="file"
                                accept="audio/*"
                                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                            />
                            <Button onClick={handleUploadFile} disabled={!file || loading} className="w-full">
                                {loading ? "Processing..." : "Upload & Process"}
                            </Button>
                        </div>

                        <div className="h-px bg-zinc-200 dark:bg-zinc-800" />

                        {/* Record */}
                        <div className="space-y-3">
                            <div className="font-semibold">Record audio</div>

                            {micError && <div className="text-sm text-red-500">{micError}</div>}

                            <div className="flex gap-2">
                                <Button
                                    variant={recording ? "secondary" : "default"}
                                    onClick={startRecording}
                                    disabled={recording || loading}
                                >
                                    Start
                                </Button>
                                <Button
                                    variant="secondary"
                                    onClick={stopRecording}
                                    disabled={!recording || loading}
                                >
                                    Stop
                                </Button>
                            </div>

                            {recordedBlob && (
                                <div className="space-y-3">
                                    <audio controls src={URL.createObjectURL(recordedBlob)} className="w-full" />
                                    <Button onClick={handleUploadRecording} disabled={loading} className="w-full">
                                        {loading ? "Processing..." : "Use this recording"}
                                    </Button>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
