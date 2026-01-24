export type TranscriptVersion = "original" | "edited" | "redacted";

export type TranscriptBlob = {
    original?: string | null;
    edited?: string | null;
    redacted?: string | null;
};

export type PiiHit = {
    text?: string;
    label?: string;
    preview?: string;
    start_char?: number | null;
    end_char?: number | null;
    start_s?: number | null;
    end_s?: number | null;
};

export type RecordingSegment = {
    label?: string | null;
    text?: string | null;
    start_s?: number | null;
    end_s?: number | null;
};

export type AlignedWord = {
    word: string;
    prob?: number | null;
    start_s?: number | null;
    end_s?: number | null;
};

export type SpeechConfidenceLowWord = {
    word: string;
    prob?: number | null;
    start_s?: number | null;
    end_s?: number | null;
};

export type SpeechConfidence = {
    mean?: number;
    median?: number;
    std?: number;
    min?: number;
    max?: number;
    threshold?: number;
    low_count?: number;
    count?: number;
    low?: SpeechConfidenceLowWord[];
};

export type SpeechPause = {
    avg_pause_s?: number;
    max_pause_s?: number;
    total_silence_s?: number;
    pause_count?: number;
};

export type FillerHit = string | { phrase?: string };

export type SpeechFillers = {
    count?: number;
    percent?: number; // 0..1
    hits?: FillerHit[];
};

export type SpeechAnalysis = {
    confidence?: SpeechConfidence;
    pause?: SpeechPause;
    fillers?: SpeechFillers;
};

export type RecordingData = {
    recording_id?: string | null;
    title?: string | null;
    created_at?: string | null;
    has_audio?: boolean | null;

    transcripts?: TranscriptBlob | null;

    segments?: RecordingSegment[] | null;

    tags?: string[] | null;

    pii?: PiiHit[] | null;
    pii_original?: PiiHit[] | null;
    pii_edited?: PiiHit[] | null;

    aligned_words?: AlignedWord[] | null;

    prosody?: unknown[] | null; // tighten later
    speech?: SpeechAnalysis | null;
    duration?: number;
};
