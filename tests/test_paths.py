from __future__ import annotations

import os
from pathlib import Path

from limpieza.paths import Locations, fmt_bytes, is_forbidden, platform_id


def _loc(tmp_path: Path, plat: str = "windows") -> Locations:
    return Locations(
        platform=plat,
        home=tmp_path / "home",
        temp=tmp_path / "home" / "AppData" / "Local" / "Temp",
        downloads=tmp_path / "home" / "Downloads",
        cache=tmp_path / "home" / "AppData" / "Local",
        localappdata=tmp_path / "home" / "AppData" / "Local",
        appdata=tmp_path / "home" / "AppData" / "Roaming",
        programdata=tmp_path / "ProgramData",
        tmp=tmp_path / "tmp",
    )


def test_platform_id() -> None:
    assert platform_id("win32") == "windows"
    assert platform_id("linux") == "linux"
    assert platform_id("darwin") == "darwin"


def test_forbidden_user_libraries(tmp_path: Path) -> None:
    loc = _loc(tmp_path)
    loc.home.mkdir(parents=True)
    (loc.home / "Documents").mkdir()
    (loc.home / "Desktop").mkdir()
    loc.temp.mkdir(parents=True)
    (loc.temp / "file.tmp").write_text("tmp")
    assert is_forbidden(loc.home, loc)
    assert is_forbidden(loc.home / "Documents", loc)
    assert is_forbidden(loc.home / "Desktop", loc)
    assert not is_forbidden(loc.temp, loc)
    assert not is_forbidden(loc.temp / "file.tmp", loc)


def test_forbidden_unix_roots(tmp_path: Path) -> None:
    loc = Locations(
        platform="linux",
        home=tmp_path / "home" / "user",
        temp=tmp_path / "run",
        downloads=tmp_path / "home" / "user" / "Downloads",
        cache=tmp_path / "home" / "user" / ".cache",
        localappdata=None,
        appdata=None,
        programdata=None,
        tmp=tmp_path / "tmp",
    )
    loc.home.mkdir(parents=True)
    loc.temp.mkdir()
    loc.tmp.mkdir()
    assert is_forbidden(loc.home, loc)
    assert not is_forbidden(loc.tmp, loc)
    assert not is_forbidden(loc.temp, loc)


def test_fmt_bytes() -> None:
    assert fmt_bytes(512) == "512 B"
    assert "KB" in fmt_bytes(2048)
    assert "MB" in fmt_bytes(2 * 1024 * 1024)
