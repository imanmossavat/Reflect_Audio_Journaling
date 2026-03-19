"use client";

import Link from "next/link";
import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Api } from "@/lib/api";

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, ArrowLeft } from "lucide-react";
import { toast } from "sonner";

import UploadTab from "@/components/upload/UploadTab";
import RecordTab from "@/components/upload/RecordTab";
import WriteTab from "@/components/upload/WriteTab";

function UploadPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const defaultTab = searchParams.get("tab") || "upload";
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusText, setStatusText] = useState<string | null>(null);

  const resetErrors = () => {
    setError(null);
    setStatusText(null);
  };

  const handleUploadFile = async (file: File) => {
    resetErrors();
    setStatusText("Uploading and analyzing audio...");
    setUploading(true);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", "en");

    try {
      const data = await Api.uploadAudio(formData);
      toast.success("Recording uploaded successfully!");
      router.push(`/recordings/${data.recording_id}`);
    } catch (e: any) {
      setError(e.message);
      toast.error("Upload failed: " + e.message);
      setUploading(false);
    }
  };

  const handleUploadBlob = async (blob: Blob) => {
    const file = new File([blob], "mic_record.webm", { type: blob.type || "audio/webm" });
    await handleUploadFile(file);
  };

  const handleCreateTextEntry = async (text: string) => {
    resetErrors();
    setUploading(true);

    try {
      const data = await Api.createTextEntry(text);
      toast.success("Note created successfully!");
      router.push(`/recordings/${data.recording_id}`);
    } catch (e: any) {
      setError(e.message);
      toast.error("Failed to create note: " + e.message);
      setUploading(false);
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
          {(error || statusText) && (
            <Alert variant={error ? "destructive" : "default"} className="animate-in fade-in zoom-in duration-200">
              <AlertDescription className="flex items-center gap-2">
                {(uploading || statusText) && !error && <Loader2 className="h-4 w-4 animate-spin" />}
                {statusText || error}
              </AlertDescription>
            </Alert>
          )}

          <Tabs defaultValue={defaultTab} className="w-full">
            <TabsList className="grid w-full grid-cols-3 bg-zinc-100 dark:bg-zinc-900">
              <TabsTrigger value="upload" disabled={uploading}>Upload</TabsTrigger>
              <TabsTrigger value="record" disabled={uploading}>Record</TabsTrigger>
              <TabsTrigger value="write" disabled={uploading}>Write</TabsTrigger>
            </TabsList>

            <TabsContent value="upload">
              <UploadTab
                uploading={uploading}
                onUpload={handleUploadFile}
                onError={setError}
              />
            </TabsContent>

            <TabsContent value="record">
              <RecordTab
                uploading={uploading}
                onUploadBlob={handleUploadBlob}
                onError={setError}
                onClearError={resetErrors}
              />
            </TabsContent>

            <TabsContent value="write">
              <WriteTab
                isSaving={uploading}
                onSubmit={handleCreateTextEntry}
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}

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