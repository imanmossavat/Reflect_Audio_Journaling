export type Mode = "clarifying" | "deep_dive" | null;

export interface QAEntry {
    timestamp: string;
    question: string;
    answer: string;
}

export interface Topic {
    name: string;
    summary: string;
    quotes: string[];
}

const API_BASE = "http://localhost:8000";

export interface UploadJournalResponse {
    word_count: number;
    filename: string;
    journal_id: number;
}

export interface ExtractTopicsResponse {
    topics: Topic[];
    journal_text: string;
}

export interface GenerateQuestionRequest {
    journal_id: number;
    mode: Mode;
    step: number | null;
    topic: string | null;
    topic_summary: string | null;
    history: QAEntry[];
}

async function parseError(res: Response, fallback: string): Promise<Error> {
    const data = await res.json().catch(() => ({}));
    const message = data.detail || fallback;
    return new Error(message);
}

export async function uploadJournal(file: File): Promise<UploadJournalResponse> {
    const form = new FormData();
    form.append("file", file);

    const res = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: form,
    });

    if (!res.ok) {
        throw await parseError(res, "Something went wrong while uploading journal");
    }

    return res.json();
}

export async function extractTopics(journal_id: number): Promise<ExtractTopicsResponse> {
    const res = await fetch(`${API_BASE}/topics?journal_id=${journal_id}`, { method: "POST" });

    if (!res.ok) {
        throw await parseError(res, "Failed to extract topics");
    }

    return res.json();
}

export async function generateQuestionStream(
    payload: GenerateQuestionRequest,
    onToken: (token: string) => void,
): Promise<void> {
    const res = await fetch(`${API_BASE}/generate-question`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    if (!res.ok) {
        throw await parseError(res, "Something went wrong while generating question");
    }

    const reader = res.body?.getReader();
    if (!reader) {
        return;
    }

    const decoder = new TextDecoder();
    let buffer = "";
    let streamDone = false;

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
            if (!line.startsWith("data: ")) {
                continue;
            }

            const payloadLine = line.slice(6);
            if (payloadLine === "[DONE]") {
                streamDone = true;
                break;
            }

            try {
                const parsed = JSON.parse(payloadLine) as { token?: string };
                if (parsed.token) {
                    onToken(parsed.token);
                }
            } catch {
            }
        }

        if (streamDone) {
            break;
        }
    }
}

export async function saveAnswer(payload: {
    journal_id: number;
    timestamp: string;
    question: string;
    answer: string;
}): Promise<void> {
    const res = await fetch(`${API_BASE}/save-answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    if (!res.ok) {
        throw await parseError(res, "Failed to save answer");
    }
}
