import Link from "next/link";
import { API } from "@/lib/api";
import RecordingsClient from "./RecordingsClient";
import ServerStatus from "@/components/ServerStatus";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

export default async function RecordingsPage() {
    let items = [];
    try {
        const res = await fetch(`${API}/api/recordings`, { cache: "no-store" });
        if (res.ok) {
            const data = await res.json();
            // Resiliently handle array or object response
            items = Array.isArray(data) ? data : (data.recordings || []);
        }
    } catch (e) {
        console.error("Engine offline, could not fetch recordings.");
    }

    return (
        <div className="min-h-screen w-full bg-zinc-50 dark:bg-zinc-950">
            <div className="mx-auto max-w-5xl px-6 py-10 space-y-8">

                {/* BACK LINK - Kept exactly as requested */}
                <div className="space-y-4">
                    <Link href="/" className="text-sm text-zinc-600 hover:underline dark:text-zinc-400">
                        ← Back to home
                    </Link>

                    {/* FLEX ROW FOR TITLE + STATUS */}
                    <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                        <div className="space-y-2">
                            <div className="flex items-center gap-3">
                                <h1 className="text-3xl font-bold tracking-tight text-zinc-950 dark:text-zinc-50">
                                    Your Recordings
                                </h1>
                                <Badge variant="secondary" className="bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 font-bold px-2.5 py-0.5">
                                    {items.length}
                                </Badge>
                            </div>
                            <p className="text-sm text-zinc-500">
                                Search in titles and transcript text. Filter by date/status.
                            </p>
                        </div>

                        <div className="self-start md:self-auto pb-1">
                            <ServerStatus />
                        </div>
                    </div>
                </div>

                <Separator className="bg-zinc-200 dark:bg-zinc-800" />

                <div className="mx-auto">
                    <RecordingsClient items={items} />
                </div>
            </div>
        </div>
    );
}