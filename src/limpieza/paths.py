from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def platform_id(system: str | None = None) -> str:
    name = (system or sys.platform).lower()
    if name.startswith("win"):
        return "windows"
    if name.startswith("linux"):
        return "linux"
    if name.startswith("darwin"):
        return "darwin"
    return name


@dataclass(frozen=True)
class Locations:
    platform: str
    home: Path
    temp: Path
    downloads: Path
    cache: Path
    localappdata: Path | None
    appdata: Path | None
    programdata: Path | None
    tmp: Path


def current(system: str | None = None) -> Locations:
    plat = platform_id(system)
    home = Path.home()
    downloads = _first_existing(
        home / "Downloads",
        home / "Descargas",
        Path(os.environ.get("USERPROFILE", str(home))) / "Downloads",
    ) or (home / "Downloads")

    if plat == "windows":
        local = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
        roaming = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))
        programdata = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
        temp = Path(os.environ.get("TEMP") or os.environ.get("TMP") or str(local / "Temp"))
        return Locations(
            platform=plat,
            home=home,
            temp=temp,
            downloads=downloads,
            cache=local,
            localappdata=local,
            appdata=roaming,
            programdata=programdata,
            tmp=temp,
        )

    xdg = Path(os.environ.get("XDG_CACHE_HOME", str(home / ".cache")))
    tmp = Path(os.environ.get("TMPDIR", "/tmp"))
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    temp = Path(runtime) if runtime else tmp
    return Locations(
        platform=plat,
        home=home,
        temp=temp,
        downloads=downloads,
        cache=xdg,
        localappdata=None,
        appdata=None,
        programdata=None,
        tmp=tmp,
    )


def _first_existing(*candidates: Path) -> Path | None:
    for path in candidates:
        if path.exists():
            return path
    return None


def is_forbidden(path: Path, loc: Locations | None = None) -> bool:
    """Refuse to operate on roots, home, or user libraries."""
    loc = loc or current()
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        return True

    if resolved.is_file():
        resolved = resolved.parent

    home = loc.home.resolve()
    forbidden: list[Path] = [
        home,
        home / "Documents",
        home / "Documentos",
        home / "Desktop",
        home / "Escritorio",
        home / "Pictures",
        home / "Imágenes",
        home / "Imagenes",
        home / "Videos",
        home / "Music",
        home / "Música",
        home / "Musica",
        home / "OneDrive",
    ]

    if loc.platform == "windows":
        forbidden.extend(
            [
                Path(os.environ.get("SystemRoot", r"C:\Windows")),
                Path(r"C:\Windows"),
                Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
                Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
            ]
        )
        if len(resolved.parts) <= 1:
            return True
    else:
        forbidden.extend(
            [
                Path("/"),
                Path("/usr"),
                Path("/bin"),
                Path("/sbin"),
                Path("/etc"),
                Path("/boot"),
                Path("/lib"),
                Path("/opt"),
                Path("/root"),
                Path("/home"),
            ]
        )
        if resolved == Path("/"):
            return True

    for base in forbidden:
        try:
            base_res = base.resolve()
        except OSError:
            continue
        if resolved == base_res:
            return True

    windows_temp = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Temp"
    try:
        if loc.platform == "windows" and resolved == windows_temp.resolve():
            return False
    except OSError:
        pass
    return False


def fmt_bytes(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size) < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"
