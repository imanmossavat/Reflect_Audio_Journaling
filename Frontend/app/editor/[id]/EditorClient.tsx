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
        const load = async () => {
            // 1) try edited
            let r = await fetch(`${API}/api/recordings/${id}/transcript?version=edited`);
            let d = await r.json();
            if (d?.text) {
                setText(d.text);
                setLoading(false);
                return;
            }

            // 2) fallback original
            r = await fetch(`${API}/api/recordings/${id}/transcript?version=original`);
            d = await r.json();
            setText(d?.text || "");
            setLoading(false);
        };

        load();
    }, [id]);

    const save = async () => {
        const res = await fetch(`${API}/api/recordings/${id}/transcript/edited`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
        });

        if (!res.ok) {
            // basic error handling so you don't silently fail
            const err = await res.json().catch(() => ({}));
            alert(err?.detail || "Save failed");
            return;
        }

        router.push(`/recordings/${id}`);
    };

    const saveAndSegment = async () => {
        const form = new FormData();
        form.append("recording_id", id);
        form.append("edited_transcript", text);

        const res = await fetch(`${API}/api/recordings/finalize`, { method: "POST", body: form });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert(err?.detail || "Finalize failed");
            return;
        }

        router.push(`/recordings/${id}`);
    };

    if (loading) return <div className="p-10">Loading…</div>;

    return (
        <div className="p-10 max-w-2xl mx-auto space-y-6">
            <Textarea className="h-96" value={text} onChange={e => setText(e.target.value)} />

            <div className="space-y-2">
                <Button className="w-full" onClick={save}>
                    Save transcript
                </Button>
                <Button variant="secondary" className="w-full" onClick={saveAndSegment}>
                    Save & generate segments
                </Button>
            </div>
        </div>
    );
}
