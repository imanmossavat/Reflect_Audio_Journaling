import pytest

from types import SimpleNamespace
from pathlib import Path
from fastapi import HTTPException

from app.services import journalService

class DummyUploadFile:
    def __init__(self, filename: str, content_type: str, content: bytes):
        self.filename = filename
        self.content_type = content_type
        self._content = content

    async def read(self) -> bytes:
        return self._content


def test_get_all_journals_happy_path(mocker):
    session = mocker.Mock()
    expected = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    mocker.patch.object(journalService.journalRepository, "get_all_journals", return_value=expected)

    result = journalService.get_all_journals(session)

    assert result == expected


def test_get_journal_by_id_happy_path(mocker):
    session = mocker.Mock()
    expected = SimpleNamespace(id=1, text="journal text")
    mocker.patch.object(journalService.journalRepository, "get_journal_by_id", return_value=expected)

    result = journalService.get_journal_by_id(session, 1)

    assert result == expected


def test_get_journal_by_id_not_found(mocker):
    session = mocker.Mock()
    mocker.patch.object(journalService.journalRepository, "get_journal_by_id", return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        journalService.get_journal_by_id(session, 999)

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


def test_get_unprocessed_journals_happy_path(mocker):
    query = object()
    expected = [SimpleNamespace(id=10), SimpleNamespace(id=11)]

    exec_result = mocker.Mock()
    exec_result.all.return_value = expected

    session = mocker.Mock()
    session.exec.return_value = exec_result

    mocker.patch.object(journalService.journalRepository, "get_unprocessed_journals_query", return_value=query)

    result = journalService.get_unprocessed_journals(session)

    assert result == expected
    session.exec.assert_called_once_with(query)


@pytest.mark.asyncio
async def test_save_raw_journal_file_happy_path(mocker, tmp_path):
    (tmp_path / "audio").mkdir(parents=True, exist_ok=True)
    (tmp_path / "text").mkdir(parents=True, exist_ok=True)
    mocker.patch.object(journalService, "BASE_DIR", tmp_path)

    file = DummyUploadFile("entry.txt", "text/plain", b"hello world")
    expected = SimpleNamespace(id=5)
    create_journal_mock = mocker.patch.object(journalService.journalRepository, "create_journal", return_value=expected)

    result = await journalService.save_raw_journal_file(mocker.Mock(), file)

    assert result == expected
    kwargs = create_journal_mock.call_args.kwargs
    assert kwargs["filename"] == "entry.txt"
    assert kwargs["file_type"] == "text"
    assert kwargs["status"] == "not processed"
    
    # Verify file was actually written to disk
    file_path = Path(kwargs["file_path"])
    assert file_path.exists()
    assert file_path.read_bytes() == b"hello world"


@pytest.mark.asyncio
async def test_save_raw_journal_file_unsupported_type(mocker, tmp_path):
    """Test that unsupported file extensions raise 400 error."""
    (tmp_path / "audio").mkdir(parents=True, exist_ok=True)
    (tmp_path / "text").mkdir(parents=True, exist_ok=True)
    mocker.patch.object(journalService, "BASE_DIR", tmp_path)

    file = DummyUploadFile("entry.pdf", "application/pdf", b"pdf data")

    with pytest.raises(HTTPException) as exc_info:
        await journalService.save_raw_journal_file(mocker.Mock(), file)

    assert exc_info.value.status_code == 400
    assert "unsupported" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_save_processed_journal_file_happy_path(mocker, tmp_path):
    (tmp_path / "audio").mkdir(parents=True, exist_ok=True)
    (tmp_path / "text").mkdir(parents=True, exist_ok=True)
    mocker.patch.object(journalService, "BASE_DIR", tmp_path)

    session = mocker.Mock()
    file = DummyUploadFile("entry.txt", "text/plain", b"hello world")
    journal = SimpleNamespace(id=7)
    db_chunks = [SimpleNamespace(id=101, chunk_text="chunk one")]

    mocker.patch.object(journalService.journalRepository, "create_journal", return_value=journal)
    mocker.patch.object(journalService, "chunk_text", return_value=[{"text": "chunk one"}])
    mocker.patch.object(journalService.journalRepository, "create_chunks", return_value=db_chunks)
    index_chunks_mock = mocker.patch.object(journalService, "index_chunks")

    result = await journalService.save_processed_journal_file(session, file)

    assert result == journal
    index_chunks_mock.assert_called_once_with([
        {"id": "101", "text": "chunk one", "journal_id": "7"}
    ])


@pytest.mark.asyncio
async def test_save_processed_journal_file_index_chunks_fails(mocker, tmp_path):
    (tmp_path / "audio").mkdir(parents=True, exist_ok=True)
    (tmp_path / "text").mkdir(parents=True, exist_ok=True)
    mocker.patch.object(journalService, "BASE_DIR", tmp_path)

    session = mocker.Mock()
    file = DummyUploadFile("entry.txt", "text/plain", b"hello world")
    journal = SimpleNamespace(id=7)
    db_chunks = [SimpleNamespace(id=101, chunk_text="chunk one"), SimpleNamespace(id=102, chunk_text="chunk two")]

    mocker.patch.object(journalService.journalRepository, "create_journal", return_value=journal)
    mocker.patch.object(journalService, "chunk_text", return_value=[{"text": "chunk one"}, {"text": "chunk two"}])
    mocker.patch.object(journalService.journalRepository, "create_chunks", return_value=db_chunks)
    mocker.patch.object(journalService, "index_chunks", side_effect=Exception("Index error"))

    with pytest.raises(HTTPException) as exc_info:
        await journalService.save_processed_journal_file(session, file)

    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_save_processed_journal_text_happy_path(mocker):
    session = mocker.Mock()
    journal = SimpleNamespace(id=12)
    db_chunks = [SimpleNamespace(id=202, chunk_text="chunked")]

    mocker.patch.object(journalService.journalRepository, "create_journal", return_value=journal)
    mocker.patch.object(journalService, "chunk_text", return_value=[{"text": "chunked"}])
    mocker.patch.object(journalService.journalRepository, "create_chunks", return_value=db_chunks)
    index_chunks_mock = mocker.patch.object(journalService, "index_chunks")

    result = await journalService.save_processed_journal_text(session, "my journal text")

    assert result == journal
    index_chunks_mock.assert_called_once_with([
        {"id": "202", "text": "chunked", "journal_id": "12"}
    ])


@pytest.mark.asyncio
async def test_save_processed_journal_text_no_chunks(mocker):
    session = mocker.Mock()
    journal = SimpleNamespace(id=12)

    mocker.patch.object(journalService.journalRepository, "create_journal", return_value=journal)
    mocker.patch.object(journalService, "chunk_text", return_value=[])

    with pytest.raises(HTTPException) as exc_info:
        await journalService.save_processed_journal_text(session, "")

    assert exc_info.value.status_code == 500
    assert "no chunks" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_save_raw_journal_text_happy_path(mocker):
    session = mocker.Mock()
    expected = SimpleNamespace(id=20, text="raw")
    mocker.patch.object(journalService.journalRepository, "create_journal", return_value=expected)

    result = await journalService.save_raw_journal_text(session, "raw")

    assert result == expected


@pytest.mark.asyncio
async def test_transcribe_journal_happy_path(mocker):
    session = mocker.Mock()
    journal = SimpleNamespace(id=30, file_type="audio", file_path="/tmp/audio.wav")
    updated = SimpleNamespace(id=30, text="transcribed text")

    mocker.patch.object(journalService.journalRepository, "get_journal_by_id", return_value=journal)

    transcriber = mocker.Mock()
    transcriber.transcribe.return_value = SimpleNamespace(text="transcribed text")
    mocker.patch.object(journalService, "TranscriptionManager", return_value=transcriber)

    update_mock = mocker.patch.object(journalService.journalRepository, "update_journal_text", return_value=updated)

    result = await journalService.transcribe_journal(session, 30)

    assert result == updated
    update_mock.assert_called_once_with(session, journal, "transcribed text")


@pytest.mark.asyncio
async def test_update_journal_text_happy_path(mocker):
    session = mocker.Mock()
    journal = SimpleNamespace(id=40, status="not processed")
    updated = SimpleNamespace(id=40, text="edited")

    mocker.patch.object(journalService.journalRepository, "get_journal_by_id", return_value=journal)
    update_mock = mocker.patch.object(journalService.journalRepository, "update_journal_text", return_value=updated)

    result = await journalService.update_journal_text(session, 40, "edited")

    assert result == updated
    update_mock.assert_called_once_with(session, journal, "edited")


@pytest.mark.asyncio
async def test_process_journal_happy_path(mocker):
    session = mocker.Mock()
    journal = SimpleNamespace(id=50, status="not processed", text="already transcribed", file_type="text")
    db_chunks = [SimpleNamespace(id=303, chunk_text="chunk A")]

    mocker.patch.object(journalService.journalRepository, "get_journal_by_id", return_value=journal)
    mocker.patch.object(journalService, "chunk_text", return_value=[{"text": "chunk A"}])
    create_chunks_mock = mocker.patch.object(journalService.journalRepository, "create_chunks", return_value=db_chunks)
    index_chunks_mock = mocker.patch.object(journalService, "index_chunks")

    result = await journalService.process_journal(session, 50)

    assert result == journal
    create_chunks_mock.assert_called_once()
    index_chunks_mock.assert_called_once_with([
        {"id": "303", "text": "chunk A", "journal_id": "50"}
    ])


@pytest.mark.asyncio
async def test_process_journal_markdown_stripping(mocker):
    session = mocker.Mock()
    journal = SimpleNamespace(id=51, status="not processed", text="# Title\n**bold** text", file_type="markdown")
    db_chunks = [SimpleNamespace(id=304, chunk_text="chunk B")]

    mocker.patch.object(journalService.journalRepository, "get_journal_by_id", return_value=journal)
    chunk_text_mock = mocker.patch.object(journalService, "chunk_text", return_value=[{"text": "chunk B"}])
    mocker.patch.object(journalService.journalRepository, "create_chunks", return_value=db_chunks)
    mocker.patch.object(journalService, "index_chunks")
    mocker.patch("app.services.journalService.strip_markdown.strip_markdown", return_value="Title bold text")

    await journalService.process_journal(session, 51)

    chunk_text_mock.assert_called_once()
    assert chunk_text_mock.call_args[0][0] == "Title bold text"


@pytest.mark.asyncio
async def test_process_journal_create_chunks_fails(mocker):
    session = mocker.Mock()
    journal = SimpleNamespace(id=52, status="not processed", text="text content", file_type="text")

    mocker.patch.object(journalService.journalRepository, "get_journal_by_id", return_value=journal)
    mocker.patch.object(journalService, "chunk_text", return_value=[{"text": "chunk"}])
    mocker.patch.object(journalService.journalRepository, "create_chunks", side_effect=Exception("DB error"))

    with pytest.raises(HTTPException) as exc_info:
        await journalService.process_journal(session, 52)

    assert exc_info.value.status_code == 500
