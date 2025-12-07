from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.config import load_defaults
from bioetl.infrastructure.config.defaults_loader import DefaultsValidationError


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_load_defaults_with_env_substitution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HASH_SALT", "secret-salt")
    monkeypatch.setenv("MAX_URL_LEN", "1500")
    monkeypatch.setenv("CHEMBL_BASE", "https://env.example.org")

    _write(
        tmp_path / "hashing.yaml",
        """
hashing:
  algorithm: blake2b
  digest_size_bytes: 16
  output_encoding: hex_lower
  salt: ${HASH_SALT:-fallback}
  hash_version: v2
        """,
    )

    _write(
        tmp_path / "normalization.yaml",
        """
normalization:
  case_sensitive_fields:
    - foo
  id_fields: []
        """,
    )

    _write(
        tmp_path / "defaults" / "network.yaml",
        """
http:
  default:
    max_url_length: ${MAX_URL_LEN:-2000}
        """,
    )

    _write(
        tmp_path / "defaults" / "chembl.yaml",
        """
sources:
  chembl:
    provider: chembl
    base_url: ${CHEMBL_BASE:-https://chembl.example/api}
    batch_size: 25
        """,
    )

    defaults = load_defaults(base_dir=tmp_path)

    assert defaults.hashing.hashing.salt == "secret-salt"
    assert defaults.network is not None
    assert defaults.network.http.default.max_url_length == 1500

    chembl_defaults = defaults.get_source_default("chembl")
    assert chembl_defaults is not None
    assert str(chembl_defaults.base_url).rstrip("/") == "https://env.example.org"
    assert chembl_defaults.batch_size == 25
    assert defaults.normalization.normalization.case_sensitive_fields == ["foo"]


def test_invalid_hashing_defaults_raises(tmp_path: Path) -> None:
    _write(
        tmp_path / "hashing.yaml",
        """
hashing:
  algorithm: blake2b
  digest_size_bytes: invalid
        """,
    )
    _write(
        tmp_path / "normalization.yaml",
        """
normalization:
  case_sensitive_fields: []
  id_fields: []
        """,
    )
    _write(
        tmp_path / "defaults" / "network.yaml",
        """
http:
  default:
    max_url_length: 2000
        """,
    )

    with pytest.raises(DefaultsValidationError):
        load_defaults(base_dir=tmp_path)
