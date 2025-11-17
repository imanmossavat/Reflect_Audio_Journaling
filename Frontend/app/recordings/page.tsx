import Link from "next/link";
import { API } from "@/lib/api";

export default async function RecordingsPage() {
  const res = await fetch(`${API}/api/recordings`, { cache: "no-store" });
  const items = await res.json();

  return (
    <div className="p-10 space-y-6 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Your Recordings</h1>

      <div className="space-y-4">
        {items.map((rec: any) => (
          <Link
            key={rec.recording_id}
            href={`/recordings/${rec.recording_id}`}
            className="block p-4 rounded border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800"
          >
            <div className="font-semibold">{rec.recording_id}</div>
            <div className="text-sm text-zinc-500">
              {rec.created_at || "Unknown date"}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
