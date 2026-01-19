import { API } from "@/lib/api";
import RecordingClient from "@/app/recordings/[id]/RecordingClient";

export default async function RecordingPage({ params }: { params: { id: string } }) {
    const { id } = await params;

    const res = await fetch(`${API}/api/recordings/${id}`, { cache: "no-store" });
    const data = await res.json();

    return (
        <RecordingClient api={API} id={id} initialData={data} />
    );
}
