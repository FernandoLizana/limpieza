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


_FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def _safe_resolve(path: Path) -> Path | None:
    try:
        return path.expanduser().resolve()
    except OSError:
        return None


def _same_or_under(path: Path, base: Path) -> bool:
    try:
        return path == base or path.is_relative_to(base)
    except (OSError, ValueError):
        return False


def is_link_like(path: Path) -> bool:
    """True for symlinks and Windows junctions/mount points (do not follow)."""
    try:
        if path.is_symlink():
            return True
    except OSError:
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction):
        try:
            if is_junction():
                return True
        except OSError:
            return True
    try:
        st = path.lstat()
    except OSError:
        return True
    if getattr(st, "st_reparse_tag", 0):
        return True
    if getattr(st, "st_file_attributes", 0) & _FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    return False


def is_link_like_entry(entry: os.DirEntry) -> bool:
    """Same as is_link_like, for os.scandir entries."""
    try:
        if entry.is_symlink():
            return True
    except OSError:
        return True
    try:
        st = entry.stat(follow_symlinks=False)
    except OSError:
        return True
    if getattr(st, "st_reparse_tag", 0):
        return True
    if getattr(st, "st_file_attributes", 0) & _FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    return False


def is_forbidden(path: Path, loc: Locations | None = None) -> bool:
    """Refuse home, user libraries, OS trees, and anything under them.

    Caches that live *under* the user profile (AppData, .cache, Downloads)
    stay allowed. Document libraries and system roots are blocked including
    descendants, so a junction/symlink into Documents cannot be cleaned.
    """
    loc = loc or current()
    resolved = _safe_resolve(path)
    if resolved is None:
        return True

    home = _safe_resolve(loc.home)
    if home is None:
        return True
    if resolved == home:
        return True
    if resolved.parent == home and resolved.is_file():
        return True

    libraries = [
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
    onedrive = os.environ.get("OneDrive")
    if onedrive:
        libraries.append(Path(onedrive))

    for base in libraries:
        base_res = _safe_resolve(base)
        if base_res is not None and _same_or_under(resolved, base_res):
            return True

    if loc.platform == "windows":
        if len(resolved.parts) <= 1:
            return True
        windows_temp = _safe_resolve(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Temp")
        if windows_temp is not None and _same_or_under(resolved, windows_temp):
            return False
        for raw in (
            os.environ.get("SystemRoot", r"C:\Windows"),
            r"C:\Windows",
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        ):
            base_res = _safe_resolve(Path(raw))
            if base_res is not None and _same_or_under(resolved, base_res):
                return True
        return False

    if resolved == Path("/"):
        return True
    for raw in ("/usr", "/bin", "/sbin", "/etc", "/boot", "/lib", "/opt", "/root"):
        base_res = _safe_resolve(Path(raw))
        if base_res is not None and _same_or_under(resolved, base_res):
            return True
    home_root = _safe_resolve(Path("/home"))
    if home_root is not None and resolved == home_root:
        return True
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
