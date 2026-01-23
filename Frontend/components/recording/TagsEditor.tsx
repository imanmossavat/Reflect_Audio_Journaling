"use client";

import * as React from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import BadgePill from "@/components/shared/BadgePill";
import { normalizeTagsFromString } from "@/lib/recording.utils";
import { API } from "@/lib/api";

export default function TagsEditor({
    id,
    tags,
    onSaved,
}: {
    id: string;
    tags: string[];
    onSaved: (nextTags: string[]) => void;
}) {
    const [tagsInput, setTagsInput] = React.useState(tags.join(", "));
    const [saving, setSaving] = React.useState(false);
    const [err, setErr] = React.useState<string | null>(null);

    React.useEffect(() => {
        setTagsInput(tags.join(", "));
    }, [tags]);

    const save = async () => {
        setErr(null);
        setSaving(true);

        try {
            const next = normalizeTagsFromString(tagsInput);

            const res = await fetch(`${API}/api/recordings/${id}/meta`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tags: next }),
            });

            if (!res.ok) {
                const e = await res.json().catch(() => ({}));
                throw new Error((e as any)?.detail || "Failed to update tags");
            }

            const out = (await res.json()) as { tags?: string[] };
            onSaved(out?.tags ?? next);
        } catch (e: unknown) {
            setErr(e instanceof Error ? e.message : "Something went wrong");
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="space-y-2">
            <Input
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="e.g. school, anxiety, plans"
            />

            <div className="flex gap-2">
                <Button onClick={save} disabled={saving}>
                    {saving ? "Saving..." : "Save tags"}
                </Button>
                <Button variant="secondary" onClick={() => setTagsInput(tags.join(", "))} disabled={saving}>
                    Reset
                </Button>
            </div>

            {err && <div className="text-xs text-red-600">{err}</div>}

            {tags.length > 0 ? (
                <div className="flex flex-wrap gap-2 pt-1">
                    {tags.map((t) => (
                        <BadgePill key={t} text={t} />
                    ))}
                </div>
            ) : (
                <div className="text-xs text-zinc-500">No tags yet.</div>
            )}
        </div>
    );
}
