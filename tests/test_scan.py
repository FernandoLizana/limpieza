from __future__ import annotations

import os
import time
from pathlib import Path

from limpieza.models import Kind, Rule, Safety
from limpieza.scan import measure


def _rule(root: Path, **kwargs: object) -> Rule:
    defaults = dict(
        id="t",
        name="test",
        safety=Safety.SAFE,
        reason="test",
        roots=(root,),
        min_age_hours=0,
    )
    defaults.update(kwargs)
    return Rule(**defaults)  # type: ignore[arg-type]


def test_measure_counts_files(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"12345")
    (tmp_path / "b.bin").write_bytes(b"67890")
    hit = measure(_rule(tmp_path))
    assert hit.files == 2
    assert hit.bytes == 10


def test_min_age_skips_recent(tmp_path: Path) -> None:
    old = tmp_path / "old.txt"
    new = tmp_path / "new.txt"
    old.write_text("old")
    new.write_text("new")
    aged = time.time() - 48 * 3600
    os.utime(old, (aged, aged))
    hit = measure(_rule(tmp_path, min_age_hours=24))
    assert hit.files == 1
    assert hit.samples[0].endswith("old.txt")


def test_glob_only_matching(tmp_path: Path) -> None:
    installer = tmp_path / "Setup.exe"
    notes = tmp_path / "readme.txt"
    installer.write_bytes(b"abc")
    notes.write_bytes(b"xyzxyz")
    aged = time.time() - 40 * 24 * 3600
    os.utime(installer, (aged, aged))
    os.utime(notes, (aged, aged))
    hit = measure(
        _rule(
            tmp_path,
            kind=Kind.GLOB,
            patterns=("*.exe", "*.msi"),
            min_age_hours=30 * 24,
        )
    )
    assert hit.files == 1
    assert hit.bytes == 3


def test_keep_latest(tmp_path: Path) -> None:
    for i, name in enumerate(("v1", "v2", "v3")):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "node.exe").write_bytes(b"x" * 10)
        stamp = time.time() - 30 + i
        os.utime(folder, (stamp, stamp))
    hit = measure(_rule(tmp_path, kind=Kind.KEEP_LATEST, keep=1))
    assert hit.files == 2
    names = {Path(s).parent.name for s in hit.samples}
    assert "v3" not in names


def test_skips_git_and_node_modules(tmp_path: Path) -> None:
    git = tmp_path / ".git"
    git.mkdir()
    (git / "packed").write_bytes(b"secret")
    nm = tmp_path / "node_modules"
    nm.mkdir()
    (nm / "pkg.js").write_bytes(b"dep")
    (tmp_path / "ok.tmp").write_bytes(b"ok")
    hit = measure(_rule(tmp_path))
    assert hit.files == 1
    assert hit.bytes == 2
