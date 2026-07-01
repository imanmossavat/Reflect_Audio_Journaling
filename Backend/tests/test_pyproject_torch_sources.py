"""Regression guard for the bug where `cpu` and `cuda` torch extras were
defined identically in pyproject.toml with no [tool.uv.sources] routing, so
`uv sync --extra cuda` silently installed the CPU-only wheel from PyPI --
downgrading a colleague's working CUDA install without any error
(docs/ISSUES.md #1/#9; see CHANGES.md, July 2026).
"""

import tomllib
from pathlib import Path

import pytest

PYPROJECT_PATH = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _load_pyproject():
    with PYPROJECT_PATH.open("rb") as f:
        return tomllib.load(f)


@pytest.mark.parametrize("package", ["torch", "torchaudio"])
def test_cpu_and_cuda_extras_route_to_different_indexes(package):
    data = _load_pyproject()

    sources = data["tool"]["uv"]["sources"][package]
    by_extra = {entry["extra"]: entry["index"] for entry in sources}

    assert {"cpu", "cuda"} <= by_extra.keys(), (
        f"{package} must map both the cpu and cuda extras to an explicit index"
    )
    assert by_extra["cpu"] != by_extra["cuda"], (
        f"{package}'s cpu and cuda extras resolve from the same index -- this is "
        "the exact regression that shipped a CPU-only torch to a CUDA machine"
    )

    index_urls = {idx["name"]: idx["url"] for idx in data["tool"]["uv"]["index"]}
    assert index_urls[by_extra["cpu"]] != index_urls[by_extra["cuda"]]
    assert "cu" in index_urls[by_extra["cuda"]], (
        "cuda extra's index should point at a CUDA-tagged PyTorch wheel index "
        "(e.g. download.pytorch.org/whl/cu128)"
    )


def test_cpu_and_cuda_extras_are_marked_conflicting():
    """Without this, uv can try to satisfy both extras in one resolve, which
    silently picks one index's wheel over the other instead of erroring."""
    data = _load_pyproject()
    conflict_pairs = [{c["extra"] for c in pair} for pair in data["tool"]["uv"]["conflicts"]]
    assert {"cpu", "cuda"} in conflict_pairs
