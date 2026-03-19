import { API } from "@/lib/api";
import RecordingClient from "@/app/recordings/[id]/RecordingClient";

export default async function RecordingPage({ params }: { params: { id: string } }) {
    const { id } = await params;
    let data = null;

    try {
        const res = await fetch(`${API}/api/recordings/${id}`, { cache: "no-store" });
        if (res.ok) {
            data = await res.json();
        }
    } catch (e) {
        console.error("Backend offline or request failed:", e);
    }

    return (
        <RecordingClient api={API} id={id} initialData={data} />
    );
}
