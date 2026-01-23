"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface WriteTabProps {
    isSaving: boolean;
    onSubmit: (text: string) => void;
}

export default function WriteTab({ isSaving, onSubmit }: WriteTabProps) {
    const [text, setText] = useState("");

    return (
        <div className="space-y-4 pt-4">
            <Textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Start writing your thoughts..."
                className="min-h-[250px] bg-zinc-50 dark:bg-zinc-900/50 resize-none focus-visible:ring-red-500"
            />
            <div className="flex justify-between items-center px-1">
                <span className="text-[10px] uppercase font-bold text-zinc-400 tracking-widest">{text.length} Characters</span>
                <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs text-zinc-500"
                    onClick={() => setText("")}
                    disabled={!text}
                >Clear</Button>
            </div>
            <Button onClick={() => onSubmit(text)} disabled={!text.trim() || isSaving} className="w-full h-11">
                {isSaving ? "Saving Entry..." : "Create Text Entry"}
            </Button>
        </div>
    );
}
