"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Api } from "@/lib/api";
import { ArrowRight, FileText, Mic, Loader2 } from "lucide-react";

export default function RecentRecordings() {
    const [items, setItems] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchRecent() {
            try {
                const data = await Api.listRecordings();
                setItems(data.slice(0, 5));
            } catch (err) {
                console.error("Dashboard fetch error:", err);
            } finally {
                setLoading(false);
            }
        }
        fetchRecent();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-8">
                <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
            </div>
        );
    }

    if (items.length === 0) {
        return (
            <div className="py-6 text-center border border-dashed border-zinc-200 dark:border-zinc-800 rounded-xl">
                <p className="text-[10px] text-zinc-400 uppercase font-bold tracking-widest">No history found</p>
            </div>
        );
    }

    return (
        <div className="space-y-1">
            {items.map((item) => (
                <Link key={item.recording_id || item.id} href={`/recordings/${item.recording_id || item.id}`} className="group block">
                    <div className="flex items-center justify-between p-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-all border border-transparent hover:border-zinc-200 dark:hover:border-zinc-800">
                        <div className="flex items-center gap-3 min-w-0">
                            <div className="h-7 w-7 rounded-md bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center shrink-0">
                                {item.has_audio ? (
                                    <Mic className="h-3.5 w-3.5 text-zinc-500" />
                                ) : (
                                    <FileText className="h-3.5 w-3.5 text-zinc-500" />
                                )}
                            </div>
                            <div className="flex flex-col min-w-0">
                                <span className="text-xs font-semibold truncate text-zinc-700 dark:text-zinc-200">
                                    {item.title || "Untitled Entry"}
                                </span>
                                <span className="text-[9px] text-zinc-400 uppercase">
                                    {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'Just now'}
                                </span>
                            </div>
                        </div>
                        <ArrowRight className="h-3 w-3 text-zinc-300 group-hover:text-zinc-900 dark:group-hover:text-zinc-100 transition-all -translate-x-1 group-hover:translate-x-0 opacity-0 group-hover:opacity-100" />
                    </div>
                </Link>
            ))}
        </div>
    );
}