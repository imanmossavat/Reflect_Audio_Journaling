import whisper
import whisperx
import librosa

# ============================================================
# NOTES
# The first time you run this script, it will download the model you choose. This might take a while but is only done once.
# ============================================================

# ============================================================
# PREREQUISITES
# python 3.10
# install the packages in requirements-audioonly.txt
# ============================================================

# ============================================================
# CONFIGURATION – CHANGE THESE
# ============================================================

AUDIO_FILE = "audio/TestAudio.m4a"
PROMPT_TEXT = "Fontys University Eindhoven Netherlands"

# tiny | base | small | medium | large | large-v2 | large-v3 | large-v3-turbo | turbo
WHISPER_MODEL_SIZE = "base"

# None → auto-detect | "en" → English | "nl" → Dutch | etc. | auto-detect will make the transcription take longer
LANGUAGE = "en"

# "cpu" | "mps" (apple silicon) | "cuda" (nvidia gpu)
DEVICE = "cpu"

# Enable word-level timestamps via WhisperX
# True  → word-level alignment
# False → transcript only
USE_WORD_ALIGNMENT = False

# ============================================================
# TRANSCRIPTION FUNCTION
# ============================================================

def transcribe_with_whisperx(
    audio_file,
    device,
    whisper_model_size,
    prompt_text="",
    language=None,
    use_word_alignment=True,
):
    whisper_model = whisper.load_model(
        whisper_model_size,
        device=device
    )

    result = whisper_model.transcribe(
        audio_file,
        prompt=prompt_text,
        language=language
    )

    detected_language = result.get("language", "en")

    if not use_word_alignment:
        transcript = " ".join(seg["text"].strip() for seg in result["segments"])
        transcript = " ".join(transcript.split())

        return {
            "language": detected_language,
            "transcript": transcript,
            "word_segments": None
        }

    align_model, align_metadata = whisperx.load_align_model(
        language_code=detected_language,
        device=device
    )

    audio, sr = librosa.load(audio_file, sr=16000, mono=True)

    aligned = whisperx.align(
        transcript=result["segments"],
        model=align_model,
        align_model_metadata=align_metadata,
        audio=audio,
        device=device,
        return_char_alignments=False
    )

    transcript = " ".join(w["word"].strip() for w in aligned["word_segments"])
    transcript = " ".join(transcript.split())

    return {
        "language": detected_language,
        "transcript": transcript,
        "word_segments": aligned["word_segments"]
    }

# ============================================================
# RUN SCRIPT
# ============================================================

if __name__ == "__main__":
    result = transcribe_with_whisperx(
        audio_file=AUDIO_FILE,
        device=DEVICE,
        whisper_model_size=WHISPER_MODEL_SIZE,
        prompt_text=PROMPT_TEXT,
        language=LANGUAGE,
        use_word_alignment=USE_WORD_ALIGNMENT
    )

    print(f"Detected language: {result['language']}\n")
    print("Transcript:\n")
    print(result["transcript"])

    if result["word_segments"]:
        print("\n--- Word-level alignment ---")
        for w in result["word_segments"]:
            print(f"[{w['start']:.2f}-{w['end']:.2f}] {w['word']}")

