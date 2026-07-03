"""Hashing behaviour."""
from packages.core.utils.hashing import sha256_bytes, sha256_file


def test_sha256_bytes_known_vector():
    assert sha256_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert sha256_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_sha256_file_streams(tmp_path):
    p = tmp_path / "blob.bin"
    p.write_bytes(b"abc")
    assert sha256_file(p) == sha256_bytes(b"abc")
