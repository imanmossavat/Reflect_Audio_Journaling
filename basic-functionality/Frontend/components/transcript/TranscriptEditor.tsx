"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Api } from "@/lib/api";

export default function TranscriptEditor({
    api,
    id,
    initialText,
    onSaved,
}: {
    api: string;
    id: string;
    initialText: string;
    onSaved?: (newText: string) => void;
}) {
    const [editing, setEditing] = React.useState(false);
    const [draft, setDraft] = React.useState(initialText || "");
    const [saving, setSaving] = React.useState(false);

    // Keep editor in sync when tab changes
    React.useEffect(() => {
        if (!editing) setDraft(initialText || "");
    }, [initialText, editing]);

    async function save() {
        setSaving(true);
        try {
            await Api.finalizeRecording(id, draft);
            onSaved?.(draft);
            setEditing(false);
        } catch (e) {
            console.error(e);
            // toast handle by parent? or generic alert? Original had strict throw.
        } finally {
            setSaving(false);
        }
    }

    if (!editing) {
        return (
            <div className="flex justify-end">
                <Button variant="outline" onClick={() => setEditing(true)}>
                    Edit transcript
                </Button>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            <Textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                className="min-h-[220px]"
            />

            <div className="flex gap-2">
                <Button onClick={save} disabled={saving}>
                    Save
                </Button>
                <Button
                    variant="outline"
                    onClick={() => {
                        setDraft(initialText || "");
                        setEditing(false);
                    }}
                    disabled={saving}
                >
                    Cancel
                </Button>
            </div>
        </div>
    );
}
