"use client";

import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useRouter } from "next/navigation";

export default function EditorClient({ id }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    fetch(`${API}/api/recordings/${id}`)
      .then(r => r.json())
      .then(d => {
        setText(d.transcript || "");
        setLoading(false);
      });
  }, [id]);

  const save = async () => {
    const form = new FormData();
    form.append("recording_id", id);
    form.append("edited_transcript", text);

    await fetch(`${API}/api/recordings/finalize`, { method: "POST", body: form });
    router.push(`/recordings/${id}`);
  };

  if (loading) return <div className="p-10">Loading…</div>;

  return (
    <div className="p-10 max-w-2xl mx-auto space-y-6">
      <Textarea className="h-96" value={text} onChange={e => setText(e.target.value)} />
      <Button className="w-full" onClick={save}>
        Save transcript
      </Button>
    </div>
  );
}
