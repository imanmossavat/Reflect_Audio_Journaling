import { RecordingData, PiiHit } from "./recording.types";

export const API = "http://127.0.0.1:8000";

// --- Types for specific API payloads ---
export type RecordingListItem = {
  recording_id: string;
  title: string | null;
  created_at: string | null;
  has_audio: boolean;
  transcripts: { original: boolean; edited: boolean; redacted: boolean };
  latest_transcript_version: string | null;
  search_text: string | null;
  tags: string[];
};

export type SemanticHit = {
  recording_id: string;
  segment_id: number;
  score: number;
  label: string;
  text: string;
  start_s: number | null;
  end_s: number | null;
};

// --- API Client ---

export const Api = {
  // Recordings
  listRecordings: async (): Promise<RecordingListItem[]> => {
    const res = await fetch(`${API}/api/recordings`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch recordings");
    return res.json();
  },

  getRecording: async (id: string): Promise<RecordingData> => {
    const res = await fetch(`${API}/api/recordings/${id}`, { cache: "no-store" });
    if (res.status === 404) return {} as RecordingData; // Handle not found gracefully in UI
    if (!res.ok) throw new Error("Failed to fetch recording");
    return res.json();
  },

  updateRecordingMeta: async (id: string, payload: { title?: string; tags?: string[] }) => {
    const res = await fetch(`${API}/api/recordings/${id}/meta`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to update metadata");
    return res.json();
  },

  deleteRecording: async (id: string) => {
    const res = await fetch(`${API}/api/recordings/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete recording");
    return res.json();
  },

  deleteAudio: async (id: string) => {
    const res = await fetch(`${API}/api/recordings/${id}/audio`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete audio");
    return res.json();
  },

  deleteTranscripts: async (id: string) => {
    const res = await fetch(`${API}/api/recordings/${id}/transcript?version=all`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete transcripts");
    return res.json();
  },

  deleteSegments: async (id: string) => {
    const res = await fetch(`${API}/api/recordings/${id}/segments`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete segments");
    return res.json();
  },

  // Audio & Uploads
  uploadAudio: async (formData: FormData): Promise<{ recording_id: string }> => {
    const res = await fetch(`${API}/api/recordings/upload`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.detail || "Upload failed");
    }
    return res.json();
  },

  createTextEntry: async (text: string): Promise<{ recording_id: string }> => {
    const res = await fetch(`${API}/api/recordings/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.detail || "Failed to create text entry");
    }
    return res.json();
  },

  // Transcripts & Processing
  getTranscript: async (id: string, version: "original" | "edited" | "redacted" = "original") => {
    const res = await fetch(`${API}/api/recordings/${id}/transcript?version=${version}`);
    if (!res.ok) return { text: "" };
    return res.json(); // returns { text: "..." }
  },

  saveEditedTranscript: async (id: string, text: string) => {
    const res = await fetch(`${API}/api/recordings/${id}/transcript/edited`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error("Failed to save transcript");
    return res.json();
  },

  finalizeRecording: async (id: string, editedTranscript: string) => {
    const formData = new FormData();
    formData.append("recording_id", id);
    formData.append("edited_transcript", editedTranscript);

    const res = await fetch(`${API}/api/recordings/finalize`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Processing failed");
    return res.json();
  },

  syncPii: async (id: string, findings: PiiHit[]) => {
    const res = await fetch(`${API}/api/recordings/${id}/pii`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ findings }),
    });
    if (!res.ok) throw new Error("Failed to sync PII");
    return res.json();
  },


  // Settings
  getSettings: async () => {
    const res = await fetch(`${API}/api/settings`);
    if (!res.ok) throw new Error("Failed to fetch settings");
    return res.json();
  },

  updateSettings: async (settings: object, restart = false) => {
    const payload = { ...settings, RESTART_REQUIRED: restart };
    const res = await fetch(`${API}/api/settings/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to update settings");
    return res.json();
  },

  resetSettings: async () => {
    const res = await fetch(`${API}/api/settings/reset`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to reset settings");
    return res.json();
  },

  openFolder: async (path: string) => {
    const res = await fetch(`${API}/api/settings/open-folder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    if (!res.ok) throw new Error("Failed to open folder");
    return res.json();
  },

  // AI Tools
  semanticSearch: async (query: string): Promise<SemanticHit[]> => {
    const res = await fetch(`${API}/api/search/semantic`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.hits || [];
  }
};
