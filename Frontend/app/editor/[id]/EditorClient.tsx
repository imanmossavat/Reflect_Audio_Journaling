"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { API } from "@/lib/api";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export default function EditorClient({ id }: { id: string }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(true);

  const [saving, setSaving] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const router = useRouter();

  const canSubmit = useMemo(() => text.trim().length > 0, [text]);

  useEffect(() => {
    const load = async () => {
      setError(null);
      setStatus("Loading transcript…");
      setLoading(true);

      try {
        // Prefer edited
        let r = await fetch(`${API}/api/recordings/${id}/transcript?version=edited`, { cache: "no-store" });
        let d = await r.json().catch(() => ({}));

        if (d?.text?.trim()) {
          setText(d.text);
          setLoading(false);
          setStatus(null);
          return;
        }

        // Fallback original
        r = await fetch(`${API}/api/recordings/${id}/transcript?version=original`, { cache: "no-store" });
        d = await r.json().catch(() => ({}));
        setText(d?.text || "");
      } catch (e: any) {
        setError(e?.message || "Failed to load transcript");
      } finally {
        setLoading(false);
        setStatus(null);
      }
    };

    load();
  }, [id]);

  const saveDraft = async () => {
    if (!canSubmit || saving || finalizing) return;

    setError(null);
    setStatus("Saving draft…");
    setSaving(true);

    try {
      const res = await fetch(`${API}/api/recordings/${id}/transcript/edited`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || "Save failed");
      }

      setStatus("Saved.");
      // Optional: tiny delay not needed. Just go back.
      router.push(`/recordings/${id}`);
    } catch (e: any) {
      setError(e?.message || "Save failed");
      setStatus(null);
    } finally {
      setSaving(false);
    }
  };

  const finalizeProcessing = async () => {
    if (!canSubmit || saving || finalizing) return;

    setError(null);
    setStatus("Finalizing… running processing pipeline");
    setFinalizing(true);

    try {
      const form = new FormData();
      form.append("recording_id", id);
      form.append("edited_transcript", text);

      const res = await fetch(`${API}/api/recordings/finalize`, { method: "POST", body: form });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || "Finalize failed");
      }

      setStatus("Done. Redirecting…");
      router.push(`/recordings/${id}`);
    } catch (e: any) {
      setError(e?.message || "Finalize failed");
      setStatus(null);
    } finally {
      setFinalizing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
        <div className="mx-auto max-w-3xl p-6 md:p-10 space-y-4">
          <div className="text-sm text-zinc-500">Loading…</div>
          <div className="h-64 rounded-md border border-zinc-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-900/30" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <div className="mx-auto max-w-3xl p-6 md:p-10 space-y-4">
        <Link href={`/recordings/${id}`} className="text-sm text-zinc-600 hover:underline dark:text-zinc-400">
          ← Back to recording
        </Link>

        {(error || status) && (
          <Alert>
            <AlertTitle>Status</AlertTitle>
            <AlertDescription className="space-y-1">
              {status && <div>{status}</div>}
              {error && <div className="text-red-600">{error}</div>}
            </AlertDescription>
          </Alert>
        )}

        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>Edit transcript</CardTitle>
            <CardDescription>
              Save a draft anytime. When you’re ready, finalize to run the processing pipeline (segments, PII, etc.).
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <Textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Edit your transcript…"
              className="min-h-[420px]"
              disabled={saving || finalizing}
            />

            <div className="flex flex-col gap-2">
              <Button onClick={saveDraft} disabled={!canSubmit || saving || finalizing}>
                {saving ? "Saving…" : "Save draft"}
              </Button>

              <Button variant="secondary" onClick={finalizeProcessing} disabled={!canSubmit || saving || finalizing}>
                {finalizing ? "Finalizing…" : "Finalize processing"}
              </Button>

              <div className="text-xs text-zinc-500">
                Finalize will update derived data (segments).
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
