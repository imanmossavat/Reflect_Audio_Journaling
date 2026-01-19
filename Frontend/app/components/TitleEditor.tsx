"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function EditableTitle({
                                          api,
                                          id,
                                          initialTitle,
                                          onSaved,
                                      }: {
    api: string;
    id: string;
    initialTitle: string;
    onSaved?: (title: string) => void;
}) {
    const [editing, setEditing] = React.useState(false);
    const [title, setTitle] = React.useState(initialTitle || "");
    const [draft, setDraft] = React.useState(initialTitle || "");
    const [saving, setSaving] = React.useState(false);

    React.useEffect(() => {
        setTitle(initialTitle || "");
        setDraft(initialTitle || "");
    }, [initialTitle]);

    async function save() {
        setSaving(true);
        try {
            const r = await fetch(`${api}/api/recordings/${id}/meta`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: draft }),
            });

            if (!r.ok) throw new Error("Failed to save title");
            const data = await r.json();
            setTitle(data.title || draft);
            setEditing(false);
            onSaved?.(data.title || draft);
        } finally {
            setSaving(false);
        }
    }

    if (!editing) {
        return (
            <div className="flex items-center justify-between gap-3">
                <h1 className="text-3xl font-bold">{title || `Recording ${id}`}</h1>
                <Button variant="outline" onClick={() => setEditing(true)}>
                    Edit title
                </Button>
            </div>
        );
    }

    return (
        <div className="space-y-2">
            <div className="flex gap-2">
                <Input value={draft} onChange={(e) => setDraft(e.target.value)} />
                <Button onClick={save} disabled={saving}>
                    Save
                </Button>
                <Button
                    variant="outline"
                    onClick={() => {
                        setDraft(title);
                        setEditing(false);
                    }}
                    disabled={saving}
                >
                    Cancel
                </Button>
            </div>
            <div className="text-xs text-zinc-500">
                Tip: keep it short, your future self is lazy.
            </div>
        </div>
    );
}
