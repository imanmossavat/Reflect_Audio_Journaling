"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const API = "http://localhost:8000";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", "en");

    const res = await fetch(`${API}/api/recordings/upload`, {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    console.log("[UPLOAD RESULT]", data);

    // redirect to transcript review
    router.push(`/editor/${data.recording_id}?raw=1`);
  };

  return (
    <div className="min-h-screen w-full bg-zinc-50 dark:bg-black flex justify-center py-20 px-6">
      <div className="max-w-xl w-full">
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>New Recording</CardTitle>
            <CardDescription>
              Upload an audio file to start transcription and PII detection.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <Input
              type="file"
              accept="audio/*"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />

            <Button
              onClick={handleUpload}
              disabled={!file || loading}
              className="w-full"
            >
              {loading ? "Processing..." : "Upload & Process"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
