import { API } from "@/lib/api";
import RecordingsClient from "./RecordingsClient";
import PageHeader from "@/components/shared/PageHeader";
import { Separator } from "@/components/ui/separator";
import { HelpDialog } from "@/components/shared/HelpDialog";

export default async function RecordingsPage() {
    let items = [];
    try {
        const res = await fetch(`${API}/api/recordings`, { cache: "no-store" });
        if (res.ok) {
            const data = await res.json();
            items = Array.isArray(data) ? data : (data.recordings || []);
        }
    } catch (e) {
        console.error("Engine offline, could not fetch recordings.");
    }

    return (
        <div className="min-h-screen w-full bg-zinc-50 dark:bg-zinc-950">
            <div className="mx-auto max-w-5xl px-6 py-10 space-y-8">

                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <PageHeader
                        title="Your Recordings"
                        description="Search in titles and transcript text. Filter by date/status."
                    />
                    <HelpDialog />
                </div>

                <Separator className="bg-zinc-200 dark:bg-zinc-800" />

                <div className="mx-auto">
                    <RecordingsClient items={items} />
                </div>
            </div>
        </div>
    );
}