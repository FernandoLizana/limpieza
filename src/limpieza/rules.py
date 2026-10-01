from __future__ import annotations

from pathlib import Path

from limpieza.models import Kind, Rule, Safety
from limpieza.paths import Locations, is_forbidden

BROWSER_CACHE_DIRS = (
    "Cache",
    "Code Cache",
    "GPUCache",
    "Media Cache",
    "ShaderCache",
    "GrShaderCache",
    "DawnCache",
)


def builtin_rules(loc: Locations) -> list[Rule]:
    rules: list[Rule] = []

    def add(rule: Rule) -> None:
        roots = tuple(p for p in rule.roots if p and not is_forbidden(p, loc))
        if roots:
            rules.append(Rule(**{**rule.__dict__, "roots": roots}))

    include_user_temp = loc.platform == "windows"
    if not include_user_temp:
        try:
            include_user_temp = loc.temp.resolve() != loc.tmp.resolve()
        except OSError:
            include_user_temp = loc.temp != loc.tmp
    if include_user_temp:
        add(
            Rule(
                id="user-temp",
                name="Temporary files",
                safety=Safety.SAFE,
                reason="OS and app temp files. Skips items newer than 24 hours.",
                roots=(loc.temp,),
                min_age_hours=24,
                owner_only=loc.platform != "windows",
            )
        )

    if loc.platform != "windows":
        add(
            Rule(
                id="system-tmp",
                name="User files in /tmp",
                safety=Safety.SAFE,
                reason="Only files owned by you and older than 3 days.",
                roots=(loc.tmp,),
                min_age_hours=72,
                owner_only=True,
            )
        )

    pip_roots = _existing(
        loc.cache / "pip" / "cache",
        loc.cache / "pip" / "Cache",
        loc.home / ".cache" / "pip",
    )
    add(
        Rule(
            id="pip-cache",
            name="pip cache",
            safety=Safety.SAFE,
            reason="Downloaded Python wheels. Regenerated on the next install.",
            roots=pip_roots,
        )
    )

    npm_roots = _existing(
        loc.cache / "npm-cache",
        loc.home / ".npm" / "_cacache",
        loc.home / ".npm" / "_logs",
    )
    add(
        Rule(
            id="npm-cache",
            name="npm cache",
            safety=Safety.SAFE,
            reason="npm package cache. Regenerated with npm install.",
            roots=npm_roots,
        )
    )

    pnpm_roots = _existing(
        loc.cache / "pnpm" / "store",
        loc.home / ".local" / "share" / "pnpm" / "store",
        loc.home / ".pnpm-store",
    )
    add(
        Rule(
            id="pnpm-store",
            name="pnpm store",
            safety=Safety.SAFE,
            reason="Content-addressable pnpm store. Packages re-download as needed.",
            roots=pnpm_roots,
        )
    )

    yarn_roots = _existing(
        loc.cache / "Yarn" / "Cache",
        loc.cache / "yarn",
        loc.home / ".cache" / "yarn",
        loc.home / ".yarn" / "cache",
    )
    add(
        Rule(
            id="yarn-cache",
            name="Yarn cache",
            safety=Safety.SAFE,
            reason="Yarn package cache.",
            roots=yarn_roots,
        )
    )

    gradle_roots = _existing(
        loc.home / ".gradle" / "caches",
        loc.home / ".gradle" / "daemon",
        loc.home / ".gradle" / ".tmp",
    )
    add(
        Rule(
            id="gradle-cache",
            name="Gradle caches",
            safety=Safety.SAFE,
            reason="Gradle build caches and daemons. Wrapper files are kept.",
            roots=gradle_roots,
        )
    )

    uv_roots = _existing(loc.cache / "uv", loc.home / ".cache" / "uv")
    add(
        Rule(
            id="uv-cache",
            name="uv cache",
            safety=Safety.SAFE,
            reason="uv Python package cache.",
            roots=uv_roots,
        )
    )

    nuget_roots = _existing(
        loc.cache / "NuGet" / "v3-cache",
        loc.home / ".nuget" / "packages",
    )
    add(
        Rule(
            id="nuget-cache",
            name="NuGet cache",
            safety=Safety.REVIEW,
            reason="Restored .NET packages. Rebuilds will download them again.",
            roots=nuget_roots,
        )
    )

    cargo_roots = _existing(
        loc.home / ".cargo" / "registry" / "cache",
        loc.home / ".cargo" / "git" / "db",
    )
    add(
        Rule(
            id="cargo-cache",
            name="Cargo cache",
            safety=Safety.REVIEW,
            reason="Rust crate cache. Next cargo build will re-fetch.",
            roots=cargo_roots,
        )
    )

    hf_roots = _existing(
        loc.home / ".cache" / "huggingface",
        loc.cache / "huggingface",
    )
    add(
        Rule(
            id="huggingface-cache",
            name="Hugging Face models",
            safety=Safety.REVIEW,
            reason="Downloaded ML models. Large, but slow to download again.",
            roots=hf_roots,
        )
    )

    thumb_roots = _existing(
        loc.home / ".cache" / "thumbnails",
        loc.cache / "Microsoft" / "Windows" / "Explorer",
    )
    add(
        Rule(
            id="thumbnails",
            name="Thumbnail cache",
            safety=Safety.SAFE,
            reason="Image thumbnails. The OS recreates them as you browse.",
            roots=thumb_roots,
        )
    )

    if loc.platform == "windows" and loc.programdata:
        add(
            Rule(
                id="nvidia-ota",
                name="NVIDIA update cache",
                safety=Safety.SAFE,
                reason="NVIDIA App downloaded driver/update artifacts.",
                roots=_existing(
                    loc.programdata
                    / "NVIDIA Corporation"
                    / "NVIDIA App"
                    / "UpdateFramework"
                    / "ota-artifacts"
                ),
            )
        )
        add(
            Rule(
                id="windows-temp",
                name="Windows\\Temp",
                safety=Safety.SAFE,
                reason="System temp folder (only files you can access, older than 24h).",
                roots=_existing(Path(os_windows_temp())),
                min_age_hours=24,
            )
        )

    browser_roots = _browser_roots(loc)
    add(
        Rule(
            id="browser-cache",
            name="Browser caches",
            safety=Safety.SAFE,
            reason="Chrome/Edge/Firefox cache only. Cookies and history are kept.",
            roots=browser_roots,
            kind=Kind.NAMED_SUBDIRS,
            names=BROWSER_CACHE_DIRS,
        )
    )

    agent_roots = _existing(
        *(
            base / "User" / "globalStorage" / "anysphere.cursor-agent-worker" / "agent-cli"
            / ".local" / "share" / "cursor-agent" / "versions"
            for base in _cursor_config_dirs(loc)
        )
    )
    add(
        Rule(
            id="cursor-old-agents",
            name="Old Cursor agent runtimes",
            safety=Safety.SAFE,
            reason="Keeps the newest agent runtime and removes older copies.",
            roots=agent_roots,
            kind=Kind.KEEP_LATEST,
            keep=1,
        )
    )

    add(
        Rule(
            id="old-installers",
            name="Old installers in Downloads",
            safety=Safety.REVIEW,
            reason="Setup files older than 30 days. Your documents are not touched.",
            roots=(loc.downloads,),
            kind=Kind.GLOB,
            patterns=(
                "*.exe",
                "*.msi",
                "*.msix",
                "*.dmg",
                "*.pkg",
                "*.deb",
                "*.rpm",
                "*.apk",
            ),
            min_age_hours=30 * 24,
        )
    )

    return rules


def os_windows_temp() -> str:
    import os

    root = os.environ.get("SystemRoot", r"C:\Windows")
    return str(Path(root) / "Temp")


def _existing(*paths: Path) -> tuple[Path, ...]:
    return tuple(p for p in paths if p.exists())


def _cursor_config_dirs(loc: Locations) -> list[Path]:
    dirs: list[Path] = []
    if loc.appdata:
        dirs.append(loc.appdata / "Cursor")
    dirs.extend(
        [
            loc.home / ".config" / "Cursor",
            loc.home / ".cursor",
        ]
    )
    return dirs


def _browser_roots(loc: Locations) -> tuple[Path, ...]:
    roots: list[Path] = []
    if loc.localappdata:
        roots.extend(
            [
                loc.localappdata / "Google" / "Chrome" / "User Data",
                loc.localappdata / "Microsoft" / "Edge" / "User Data",
                loc.localappdata / "BraveSoftware" / "Brave-Browser" / "User Data",
                loc.localappdata / "Mozilla" / "Firefox" / "Profiles",
            ]
        )
    roots.extend(
        [
            loc.home / ".config" / "google-chrome",
            loc.home / ".config" / "chromium",
            loc.home / ".config" / "microsoft-edge",
            loc.home / ".mozilla" / "firefox",
            loc.home / ".cache" / "google-chrome",
            loc.home / ".cache" / "chromium",
            loc.home / ".cache" / "mozilla",
        ]
    )
    return _existing(*roots)
