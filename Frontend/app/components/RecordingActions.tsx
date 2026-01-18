"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { API } from "@/lib/api";

export default function RecordingActions({ id }: { id: string }) {
    const router = useRouter();

    const del = async (url: string, redirectTo?: string) => {
        const ok = confirm("Are you sure?");
        if (!ok) return;

        const res = await fetch(`${API}${url}`, { method: "DELETE" });
        if (!res.ok) {
            alert("Delete failed");
            return;
        }
        if (redirectTo) router.push(redirectTo);
        else router.refresh();
    };

    return (
        <div className="flex flex-col gap-2">
            <Button variant="secondary" onClick={() => del(`/api/recordings/${id}/audio`)}>
                Delete audio
            </Button>

            <Button variant="secondary" onClick={() => del(`/api/recordings/${id}/transcript?version=all`)}>
                Delete transcripts
            </Button>

            <Button variant="secondary" onClick={() => del(`/api/recordings/${id}/segments`)}>
                Delete segments
            </Button>

            <Button variant="destructive" onClick={() => del(`/api/recordings/${id}`, "/recordings")}>
                Delete recording (everything)
            </Button>
        </div>
    );
}
