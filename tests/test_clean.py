from __future__ import annotations

from pathlib import Path

from limpieza.clean import clean_hit
from limpieza.models import Rule, Safety
from limpieza.scan import measure


def _hit(root: Path):
    rule = Rule(
        id="t",
        name="test",
        safety=Safety.SAFE,
        reason="test",
        roots=(root,),
        min_age_hours=0,
    )
    return measure(rule)


def test_dry_run_does_not_delete(tmp_path: Path) -> None:
    target = tmp_path / "cache"
    target.mkdir()
    file = target / "blob.bin"
    file.write_bytes(b"hello-world")
    stats = clean_hit(_hit(target), apply=False)
    assert file.exists()
    assert stats.dry_run is True
    assert stats.deleted_files == 1
    assert stats.deleted_bytes == 11


def test_apply_deletes_files_keeps_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LIMPIEZA_STATE_DIR", str(tmp_path / "state"))
    target = tmp_path / "cache"
    nested = target / "sub"
    nested.mkdir(parents=True)
    file = nested / "blob.bin"
    file.write_bytes(b"bye")
    stats = clean_hit(_hit(target), apply=True)
    assert stats.dry_run is False
    assert not file.exists()
    assert target.exists()
    assert stats.deleted_files == 1


def test_empty_hit_is_noop(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    rule = Rule(
        id="t",
        name="test",
        safety=Safety.SAFE,
        reason="test",
        roots=(missing,),
    )
    stats = clean_hit(measure(rule), apply=True)
    assert stats.deleted_files == 0
