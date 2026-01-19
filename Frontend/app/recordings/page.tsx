import Link from "next/link";
import { API } from "@/lib/api";
import RecordingsClient from "./RecordingsClient";

export default async function RecordingsPage() {
    const res = await fetch(`${API}/api/recordings`, { cache: "no-store" });
    if (!res.ok) {
        throw new Error(`Failed to load recordings: ${res.status}`);
    }
    const items = await res.json();

    return (
        <div className="min-h-screen w-screen bg-zinc-50">
            <div className="p-10 space-y-6">
                <div className="space-y-2 max-w-5xl mx-auto">
                    <Link href="/" className="text-sm text-zinc-600 hover:underline dark:text-zinc-400">
                        ← Back to home
                    </Link>
                    <h1 className="text-3xl mt-6 font-bold">Your Recordings</h1>
                    <p className="text-sm text-zinc-500">
                        Search in titles and transcript text. Filter by date/status.
                    </p>
                </div>

                <div className="mx-auto">
                    <RecordingsClient items={items} />
                </div>
            </div>
        </div>
    );
}
