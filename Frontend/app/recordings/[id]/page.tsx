import AudioPlayer from "@/app/components/AudioPlayer";
import TranscriptViewer from "@/app/components/TranscriptViewer";
import { API } from "@/lib/api";

export default async function RecordingPage({ params }) {
    const {id} = await params;
  const res = await fetch(`${API}/api/recordings/${id}`, { cache: "no-store" });
  const data = await res.json();

  return (
    <div className="p-10 space-y-6 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold">Recording {id}</h1>
      <AudioPlayer src={`${API}/api/audio/${id}`} />

      <h2 className="text-xl font-semibold mt-6">Transcript</h2>
      <TranscriptViewer text={data.transcript} pii={data.pii} />
    </div>
  );
}
