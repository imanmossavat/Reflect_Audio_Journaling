import Link from "next/link";
import { API } from "@/lib/api";

function badge(text: string) {
    return (
        <span className="text-xs px-2 py-1 rounded border border-zinc-300 dark:border-zinc-700">
      {text}
    </span>
    );
}

export default async function RecordingsPage() {
    const res = await fetch(`${API}/api/recordings`, { cache: "no-store" });
    const items = await res.json();

    return (
        <div className="p-10 space-y-6 bg-zinc-50 h-screen w-screen">
            <div className="space-y-2 max-w-2xl mx-auto">
                <Link
                    href="/"
                    className="text-sm text-zinc-600 hover:underline dark:text-zinc-400"
                >
                    ← Back to home
                </Link>

                <h1 className="text-3xl mt-10 font-bold">Your Recordings</h1>
            </div>

            <div className="space-y-4">
                {items.map((rec: any) => {
                    const t = rec.transcripts || {};
                    const hasEdited = !!t.edited;
                    const hasRedacted = !!t.redacted;
                    const hasAudio = rec.has_audio ?? !!rec.audio;

                    return (
                        <Link
                            key={rec.recording_id}
                            href={`/recordings/${rec.recording_id}`}
                            className="block p-4 rounded border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                        >
                            <div className="flex items-start justify-between gap-4">
                                <div>
                                    <div className="font-semibold">{rec.recording_id}</div>
                                    <div className="text-sm text-zinc-500">
                                        {rec.created_at || "Unknown date"}
                                    </div>
                                </div>

                                <div className="flex gap-2 flex-wrap justify-end">
                                    {hasAudio ? badge("audio") : badge("no audio")}
                                    {hasEdited && badge("edited")}
                                    {hasRedacted && badge("redacted")}
                                    {!hasEdited && !hasRedacted && badge("original")}
                                </div>
                            </div>
                        </Link>
                    );
                })}
            </div>
        </div>
    );
}
