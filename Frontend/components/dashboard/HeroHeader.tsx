"use client";

import { ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import ServerStatus from "@/components/shared/ServerStatus";

export default function HeroHeader() {
    return (
        <header className="space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">

                <div className="flex items-center gap-3">
                    <div className="h-12 w-12 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex items-center justify-center shadow-sm">
                        <ShieldCheck className="h-7 w-7 text-zinc-900 dark:text-zinc-100" />
                    </div>
                    <div className="flex flex-col">
                        <h1 className="text-4xl font-bold tracking-tight text-zinc-950 dark:text-zinc-50 leading-none">
                            REFLECT
                        </h1>
                        <span className="text-[10px] font-bold text-zinc-400 tracking-[0.2em] mt-1.5 uppercase">Local Intelligence</span>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <ServerStatus />

                    <Badge variant="outline" className="hidden sm:flex h-7 border-zinc-300 dark:border-zinc-700 text-zinc-500">
                        v1.0.0
                    </Badge>
                </div>
            </div>

            <p className="text-lg text-zinc-600 dark:text-zinc-400 max-w-2xl leading-relaxed">
                Your private, local-first intelligence hub. Capture audio or text and generate redacted, searchable insights without cloud processing.
            </p>
        </header>
    );
}
