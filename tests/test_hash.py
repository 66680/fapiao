from pathlib import Path

from invstruct.utils.hash import canonical_json_sha256, sha256_file


def test_sha256_deterministic(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("invstruct", encoding="utf-8")

    first = sha256_file(file_path)
    second = sha256_file(file_path)

    assert first == second
    assert len(first) == 64


def test_canonical_json_sha256_stable() -> None:
    payload_a = {"b": 2, "a": 1}
    payload_b = {"a": 1, "b": 2}
    assert canonical_json_sha256(payload_a) == canonical_json_sha256(payload_b)
