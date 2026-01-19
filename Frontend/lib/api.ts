export const API = "http://127.0.0.1:8000";

export async function uploadRecording(formData: FormData) {
  const res = await fetch(`${API}/api/recordings/upload`, {
    method: "POST",
    body: formData,
  });
  return res.json();
}

export async function finalizeRecording(data: {
  recording_id: string;
  edited_transcript: string;
}) {
  const formData = new FormData();
  formData.append("recording_id", data.recording_id);
  formData.append("edited_transcript", data.edited_transcript);

  const res = await fetch(`${API}/api/recordings/finalize`, {
    method: "POST",
    body: formData,
  });
  return res.json();
}
