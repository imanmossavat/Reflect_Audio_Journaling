"use client";

import { useState } from "react";
import { Mic, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const MAX_FILE_MB = 200;
const ACCEPTED_MIME_PREFIX = "audio/";

function validateAudioFile(f: File) {
    if (!f) return "No file selected.";

    const type = f.type || "";
    const name = f.name || "";

    const isAudioType = type.startsWith(ACCEPTED_MIME_PREFIX);
    const isWebm = type === "video/webm" || name.toLowerCase().endsWith(".webm");
    const isCommonAudioExt = /\.(wav|mp3|m4a|ogg|aac|flac)$/i.test(name);

    if (!isAudioType && !isWebm && !isCommonAudioExt) {
        return "That doesn’t look like an audio file.";
    }

    const mb = f.size / (1024 * 1024);
    if (mb > MAX_FILE_MB) return `File is too large (${mb.toFixed(1)}MB). Max is ${MAX_FILE_MB}MB.`;
    return null;
}

interface UploadTabProps {
    uploading: boolean;
    onUpload: (file: File) => void;
    onError: (msg: string | null) => void;
}

export default function UploadTab({ uploading, onUpload, onError }: UploadTabProps) {
    const [file, setFile] = useState<File | null>(null);

    const handleFileChange = (newFile: File | null) => {
        setFile(newFile);
        if (newFile) {
            const error = validateAudioFile(newFile);
            onError(error);
        } else {
            onError(null);
        }
    };

    const handleUploadClick = () => {
        if (!file) return;
        const error = validateAudioFile(file);
        if (error) {
            onError(error);
            return;
        }
        onUpload(file);
    };

    return (
        <div className="space-y-4 pt-4">
            <div className="flex flex-col items-center justify-center border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-xl p-8 transition-colors hover:border-zinc-300 dark:hover:border-zinc-700">
                <Input
                    type="file"
                    accept="audio/*"
                    id="audio-upload"
                    className="hidden"
                    disabled={uploading}
                    onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
                />
                <label htmlFor="audio-upload" className="cursor-pointer flex flex-col items-center gap-2 text-center">
                    <div className="p-3 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
                        {file ? <Check className="h-6 w-6 text-green-500" /> : <Mic className="h-6 w-6" />}
                    </div>
                    <span className="text-sm font-medium">{file ? file.name : "Click to select audio file"}</span>
                    <span className="text-xs text-zinc-500">WAV, MP3, M4A or WebM up to {MAX_FILE_MB}MB</span>
                </label>
            </div>

            <Button onClick={handleUploadClick} disabled={!file || uploading} className="w-full h-11">
                {uploading ? "Uploading..." : "Process Audio"}
            </Button>
        </div>
    );
}
