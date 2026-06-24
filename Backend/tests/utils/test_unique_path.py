from app.utils.unique_path import unique_path


def test_no_collision_returns_original(tmp_path):
    assert unique_path(tmp_path, "18-06.m4a") == tmp_path / "18-06.m4a"


def test_collisions_get_numbered_suffix(tmp_path):
    (tmp_path / "18-06.m4a").write_bytes(b"")
    assert unique_path(tmp_path, "18-06.m4a") == tmp_path / "18-06 (1).m4a"

    (tmp_path / "18-06 (1).m4a").write_bytes(b"")
    assert unique_path(tmp_path, "18-06.m4a") == tmp_path / "18-06 (2).m4a"


def test_basename_only_no_traversal(tmp_path):
    assert unique_path(tmp_path, "/etc/passwd").parent == tmp_path
