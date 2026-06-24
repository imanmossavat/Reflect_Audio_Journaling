from pathlib import Path


def unique_path(directory: Path, filename: str) -> Path:
    # Path in `directory` for `filename`, adding " (n)" before the extension on collision.
    
    name = Path(filename).name or "file"
    stem, suffix = Path(name).stem, Path(name).suffix
    candidate = directory / name
    index = 1
    while candidate.exists():
        candidate = directory / f"{stem} ({index}){suffix}"
        index += 1
    return candidate
