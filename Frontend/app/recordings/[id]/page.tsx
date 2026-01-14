import AudioPlayer from "@/app/components/AudioPlayer";
import TranscriptViewer from "@/app/components/TranscriptViewer";
import RecordingActions from "@/app/components/RecordingActions";
import { API } from "@/lib/api";

async function fetchTranscript(id, version) {
    const r = await fetch(`${API}/api/recordings/${id}/transcript?version=${version}`, {
        cache: "no-store",
    });
    return r.ok ? r.json() : { text: "" };
}

export default async function RecordingPage({ params }: { params: { id: string } }) {
    const { id } = await params;

    // metadata (pii, created_at, etc.)
    const res = await fetch(`${API}/api/recordings/${id}`, { cache: "no-store" });
    const data = await res.json();

    // Prefer edited, fallback original
    let t = await fetchTranscript(id, "edited");
    if (!t?.text) t = await fetchTranscript(id, "original");

    // MVP: only show PII highlights when viewing original
    const showingOriginal = !data?.transcripts?.edited && !!data?.transcripts?.original;
    const piiForView = showingOriginal ? [] : data.pii;
    console.log(piiForView)
    return (
        <div className="p-10 space-y-6 max-w-2xl mx-auto">
            <h1 className="text-3xl font-bold">Recording {id}</h1>
            <AudioPlayer src={`${API}/api/audio/${id}`} />
            <RecordingActions id={id} />

            <h2 className="text-xl font-semibold mt-6">Transcript</h2>
            <TranscriptViewer text={t.text || ""} pii={piiForView} segments={data.segments} />
        </div>
    );
}
