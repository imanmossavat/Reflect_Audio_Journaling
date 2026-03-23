from fastapi import UploadFile


async def transcribe(file: UploadFile) -> str:
    """Transcribe non-text uploads into journal text.

    This is intentionally left open for future implementation.
    """
    raise NotImplementedError("Transcription module is not implemented yet.")
