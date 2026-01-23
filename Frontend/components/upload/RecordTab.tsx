"use client";

import { useState, useRef, useMemo, useEffect } from "react";
import { Mic, Square, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import WaveformVisualizer from "@/components/shared/WaveformVisualizer";

function formatTime(seconds: number) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
}

function humanMicError(err: any) {
    const name = err?.name;
    if (name === "NotAllowedError") return "Microphone permission denied.";
    if (name === "NotFoundError") return "No microphone found.";
    return err?.message || "Microphone access failed.";
}

interface RecordTabProps {
    uploading: boolean;
    onUploadBlob: (blob: Blob) => void;
    onError: (msg: string) => void;
    onClearError: () => void;
}

export default function RecordTab({ uploading, onUploadBlob, onError, onClearError }: RecordTabProps) {
    const [recording, setRecording] = useState(false);
    const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
    const [seconds, setSeconds] = useState(0);

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

    const startRecording = async () => {
        onClearError();
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
            onError(humanMicError(err));
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && recording) {
            mediaRecorderRef.current.stop();
            setRecording(false);
            if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
        }
    };

    return (
        <div className="space-y-4 pt-4">
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
                        <Button onClick={() => onUploadBlob(recordedBlob)} className="flex-1 h-11" disabled={uploading}>
                            {uploading ? "Processing..." : "Use this recording"}
                        </Button>
                        <Button variant="outline" size="icon" className="h-11 w-11 shrink-0" onClick={() => setRecordedBlob(null)} disabled={uploading}>
                            <Trash2 className="h-4 w-4 text-zinc-500" />
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
