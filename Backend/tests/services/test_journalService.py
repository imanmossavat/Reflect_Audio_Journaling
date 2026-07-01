"""Tests for sourceService.

Only tests that match the current API surface are included here.
Tests for the removed save_processed_source_file inline-chunking flow
and the removed update_source_text function have been deleted — they
tested an old architecture where chunking/indexing happened synchronously
inside the HTTP handler. That work now runs in _process_source_sync via
a background task.
"""
import pytest

from types import SimpleNamespace
from pathlib import Path
from fastapi import HTTPException

from app.services import sourceService


class DummyUploadFile:
    def __init__(self, filename: str, content_type: str, content: bytes):
        self.filename = filename
        self.content_type = content_type
        self._content = content

    async def read(self) -> bytes:
        return self._content


# ---------------------------------------------------------------------------
# get_all_sources
# ---------------------------------------------------------------------------

def test_get_all_sources_happy_path(mocker):
    session = mocker.Mock()
    expected = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    mocker.patch.object(sourceService.sourceRepository, "get_all_sources", return_value=expected)

    result = sourceService.get_all_sources(session)

    assert result == expected


# ---------------------------------------------------------------------------
# get_source_by_id
# ---------------------------------------------------------------------------

def test_get_source_by_id_happy_path(mocker):
    session = mocker.Mock()
    expected = SimpleNamespace(id=1, text="source text")
    mocker.patch.object(sourceService.sourceRepository, "get_source_by_id", return_value=expected)

    result = sourceService.get_source_by_id(session, 1)

    assert result == expected


def test_get_source_by_id_not_found(mocker):
    session = mocker.Mock()
    mocker.patch.object(sourceService.sourceRepository, "get_source_by_id", return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        sourceService.get_source_by_id(session, 999)

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# get_unprocessed_sources
# ---------------------------------------------------------------------------

def test_get_unprocessed_sources_happy_path(mocker):
    query = object()
    expected = [SimpleNamespace(id=10), SimpleNamespace(id=11)]

    exec_result = mocker.Mock()
    exec_result.all.return_value = expected

    session = mocker.Mock()
    session.exec.return_value = exec_result

    mocker.patch.object(sourceService.sourceRepository, "get_unprocessed_sources_query", return_value=query)

    result = sourceService.get_unprocessed_sources(session)

    assert result == expected
    session.exec.assert_called_once_with(query)


# ---------------------------------------------------------------------------
# save_raw_source_file
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_raw_source_file_happy_path(mocker, tmp_path):
    (tmp_path / "audio").mkdir(parents=True, exist_ok=True)
    (tmp_path / "text").mkdir(parents=True, exist_ok=True)
    mocker.patch.object(sourceService, "BASE_DIR", tmp_path)
    mocker.patch("app.services.sourceService.get_setting", return_value="%Y-%m-%d")
    mocker.patch.object(sourceService.sourceRepository, "filename_exists", return_value=False)

    file = DummyUploadFile("entry.txt", "text/plain", b"hello world")
    expected = SimpleNamespace(id=5)
    create_source_mock = mocker.patch.object(
        sourceService.sourceRepository, "create_source", return_value=expected
    )

    result = await sourceService.save_raw_source_file(mocker.Mock(), file)

    assert result == expected
    kwargs = create_source_mock.call_args.kwargs
    assert kwargs["file_type"] == "text"
    assert kwargs["status"] == "not processed"

    file_path = Path(kwargs["file_path"])
    assert file_path.exists()
    assert file_path.read_bytes() == b"hello world"


@pytest.mark.asyncio
async def test_save_raw_source_file_unsupported_type(mocker, tmp_path):
    (tmp_path / "audio").mkdir(parents=True, exist_ok=True)
    (tmp_path / "text").mkdir(parents=True, exist_ok=True)
    mocker.patch.object(sourceService, "BASE_DIR", tmp_path)

    file = DummyUploadFile("entry.pdf", "application/pdf", b"pdf data")

    with pytest.raises(HTTPException) as exc_info:
        await sourceService.save_raw_source_file(mocker.Mock(), file)

    assert exc_info.value.status_code == 400
    assert "unsupported" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# save_processed_source_file
# The current implementation saves the file and creates the DB record.
# Chunking / indexing / summarisation happen in the background task.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_processed_source_file_creates_record(mocker, tmp_path):
    (tmp_path / "audio").mkdir(parents=True, exist_ok=True)
    (tmp_path / "text").mkdir(parents=True, exist_ok=True)
    mocker.patch.object(sourceService, "BASE_DIR", tmp_path)
    mocker.patch("app.services.sourceService.get_setting", return_value="%Y-%m-%d")
    mocker.patch.object(sourceService.sourceRepository, "filename_exists", return_value=False)

    session = mocker.Mock()
    file = DummyUploadFile("note.txt", "text/plain", b"hello world")
    expected = SimpleNamespace(id=7)
    create_source_mock = mocker.patch.object(
        sourceService.sourceRepository, "create_source", return_value=expected
    )

    result = await sourceService.save_processed_source_file(session, file)

    assert result == expected
    kwargs = create_source_mock.call_args.kwargs
    assert kwargs["file_type"] == "text"
    assert kwargs["status"] == "queued"


@pytest.mark.asyncio
async def test_save_processed_source_file_unsupported_type(mocker, tmp_path):
    (tmp_path / "audio").mkdir(parents=True, exist_ok=True)
    (tmp_path / "text").mkdir(parents=True, exist_ok=True)
    mocker.patch.object(sourceService, "BASE_DIR", tmp_path)

    file = DummyUploadFile("document.pdf", "application/pdf", b"pdf bytes")

    with pytest.raises(HTTPException) as exc_info:
        await sourceService.save_processed_source_file(mocker.Mock(), file)

    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# save_raw_source_text / save_processed_source_text
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_raw_source_text_happy_path(mocker):
    session = mocker.Mock()
    expected = SimpleNamespace(id=20, text="raw")
    mocker.patch.object(sourceService.sourceRepository, "create_source", return_value=expected)

    result = await sourceService.save_raw_source_text(session, "raw")

    assert result == expected


@pytest.mark.asyncio
async def test_save_processed_source_text_happy_path(mocker):
    session = mocker.Mock()
    expected = SimpleNamespace(id=12)
    create_mock = mocker.patch.object(
        sourceService.sourceRepository, "create_source", return_value=expected
    )

    result = await sourceService.save_processed_source_text(session, "my source text")

    assert result == expected
    kwargs = create_mock.call_args.kwargs
    assert kwargs["status"] == "queued"


# ---------------------------------------------------------------------------
# transcribe_source
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transcribe_source_happy_path(mocker):
    session = mocker.Mock()
    source = SimpleNamespace(id=30, file_type="audio", file_path="/tmp/audio.wav")
    updated = SimpleNamespace(id=30, text="transcribed text")

    mocker.patch.object(sourceService.sourceRepository, "get_source_by_id", return_value=source)

    sentence = SimpleNamespace(text="hello", start_s=0.0, end_s=1.0)
    transcriber = mocker.Mock()
    transcriber.transcribe.return_value = SimpleNamespace(
        text="transcribed text", sentences=[sentence], meta={"model": "base"}
    )
    mocker.patch.object(sourceService, "TranscriptionManager", return_value=transcriber)

    update_mock = mocker.patch.object(
        sourceService.sourceRepository, "update_source_transcript", return_value=updated
    )

    result = await sourceService.transcribe_source(session, 30)

    assert result == updated
    update_mock.assert_called_once_with(
        session, source, "transcribed text",
        [{"text": "hello", "start_s": 0.0, "end_s": 1.0}],
        {"model": "base"},
    )


@pytest.mark.asyncio
async def test_transcribe_source_not_found(mocker):
    session = mocker.Mock()
    mocker.patch.object(sourceService.sourceRepository, "get_source_by_id", return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await sourceService.transcribe_source(session, 999)

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# _process_source_sync — Chroma cleanup on reprocess
#
# Regression test for the stale-vector bug: reprocessing a source deleted the
# old SQL Chunk rows but left the matching Chroma vectors behind under the
# same source_id, pointing at now-outdated text. The fix mirrors
# chatService.reindex_chat's existing correct pattern. This test exists to
# fail loudly if that second delete call is ever removed, not for general
# pipeline coverage.
# ---------------------------------------------------------------------------

def test_process_source_sync_deletes_chroma_vectors_when_reprocessing(mocker):
    source_id = 42
    fake_source = SimpleNamespace(
        id=source_id, file_type="text", file_path=None,
        text="existing source text, already present so transcription is skipped",
        created_at=None,
    )

    # Every `with Session(engine) as session:` block in _process_source_sync
    # gets the same tolerant mock session; none of the calls made against it
    # need to succeed meaningfully for this test's assertion.
    mocker.patch.object(sourceService, "Session")

    mocker.patch.object(sourceService.sourceRepository, "get_source_by_id", return_value=fake_source)
    mocker.patch.object(sourceService, "chunk_text", return_value=[{"text": "a chunk of text"}])
    mocker.patch.object(
        sourceService.sourceRepository, "create_chunks",
        return_value=[SimpleNamespace(id=999)],
    )

    # This is the function whose non-zero return value must trigger the
    # Chroma cleanup. Patched at its source since _process_source_sync
    # imports it locally (`from app.repositories.chatRepository import
    # delete_chunks_for_source`) inside the function body.
    delete_chunks_mock = mocker.patch(
        "app.repositories.chatRepository.delete_chunks_for_source", return_value=2
    )

    mocker.patch.object(sourceService, "_check_ollama", return_value="ok")
    mocker.patch.object(sourceService, "check_model_installed", return_value=True)
    mocker.patch.object(sourceService, "index_chunks")
    mocker.patch.object(sourceService, "regenerate_summary")

    fake_collection = mocker.Mock()
    mocker.patch.object(sourceService, "get_chroma_collection", return_value=fake_collection)

    sourceService._process_source_sync(source_id)

    delete_chunks_mock.assert_called_once_with(mocker.ANY, source_id)
    fake_collection.delete.assert_called_once_with(where={"source_id": str(source_id)})


def test_process_source_sync_skips_chroma_delete_when_no_chunks_existed(mocker):
    """No prior chunks (e.g. first-time processing) -> nothing to clean up,
    so the Chroma delete call must not fire (matches chatService.reindex_chat's
    `if deleted:` guard)."""
    source_id = 43
    fake_source = SimpleNamespace(
        id=source_id, file_type="text", file_path=None,
        text="brand new source, never processed before",
        created_at=None,
    )

    mocker.patch.object(sourceService, "Session")
    mocker.patch.object(sourceService.sourceRepository, "get_source_by_id", return_value=fake_source)
    mocker.patch.object(sourceService, "chunk_text", return_value=[{"text": "a chunk of text"}])
    mocker.patch.object(
        sourceService.sourceRepository, "create_chunks",
        return_value=[SimpleNamespace(id=1000)],
    )
    mocker.patch("app.repositories.chatRepository.delete_chunks_for_source", return_value=0)
    mocker.patch.object(sourceService, "_check_ollama", return_value="ok")
    mocker.patch.object(sourceService, "check_model_installed", return_value=True)
    mocker.patch.object(sourceService, "index_chunks")
    mocker.patch.object(sourceService, "regenerate_summary")

    fake_collection = mocker.Mock()
    mocker.patch.object(sourceService, "get_chroma_collection", return_value=fake_collection)

    sourceService._process_source_sync(source_id)

    fake_collection.delete.assert_not_called()


@pytest.mark.asyncio
async def test_transcribe_source_wrong_type(mocker):
    session = mocker.Mock()
    source = SimpleNamespace(id=31, file_type="text", file_path=None)
    mocker.patch.object(sourceService.sourceRepository, "get_source_by_id", return_value=source)

    with pytest.raises(HTTPException) as exc_info:
        await sourceService.transcribe_source(session, 31)

    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# process_source — now just queues; chunking/indexing happen in background
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_source_queues_unprocessed(mocker):
    session = mocker.Mock()
    source = SimpleNamespace(id=50, status="not processed")

    mocker.patch.object(sourceService.sourceRepository, "get_source_by_id", return_value=source)
    update_mock = mocker.patch.object(
        sourceService.sourceRepository, "update_source_status", return_value=source
    )

    await sourceService.process_source(session, 50)

    update_mock.assert_called_once_with(session, source, "queued")


@pytest.mark.asyncio
async def test_process_source_already_processed(mocker):
    session = mocker.Mock()
    source = SimpleNamespace(id=51, status="processed")
    mocker.patch.object(sourceService.sourceRepository, "get_source_by_id", return_value=source)

    with pytest.raises(HTTPException) as exc_info:
        await sourceService.process_source(session, 51)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_process_source_not_found(mocker):
    session = mocker.Mock()
    mocker.patch.object(sourceService.sourceRepository, "get_source_by_id", return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await sourceService.process_source(session, 999)

    assert exc_info.value.status_code == 404
