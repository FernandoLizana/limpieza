from __future__ import annotations

import json
import os
import time
from pathlib import Path

from limpieza.models import CleanStats, Hit, Kind, Rule
from limpieza.paths import current, is_forbidden
from limpieza.scan import iter_targets, walk_files


def history_file() -> Path:
    loc = current()
    override = os.environ.get("LIMPIEZA_STATE_DIR")
    if override:
        base = Path(override)
    elif loc.platform == "windows" and loc.localappdata:
        base = loc.localappdata / "limpieza"
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", str(loc.home / ".local" / "state"))) / "limpieza"
    base.mkdir(parents=True, exist_ok=True)
    return base / "history.jsonl"


def clean_hit(hit: Hit, *, apply: bool) -> CleanStats:
    rule = hit.rule
    stats = CleanStats(rule_id=rule.id, name=rule.name, dry_run=not apply)
    if hit.missing or not hit.reclaimable:
        return stats

    for path, st in walk_files(rule):
        if is_forbidden(path):
            stats.skipped += 1
            continue
        stats.deleted_bytes += int(st.st_size)
        stats.deleted_files += 1
        if not apply:
            continue
        try:
            path.unlink()
        except OSError:
            stats.errors += 1
            stats.deleted_files -= 1
            stats.deleted_bytes -= int(st.st_size)

    if apply:
        _remove_empty_dirs(rule)
        _append_history(stats)

    return stats


def _remove_empty_dirs(rule: Rule) -> None:
    targets = list(iter_targets(rule))
    for target in targets:
        if is_forbidden(target) or not target.exists():
            continue
        keep_root = rule.kind != Kind.KEEP_LATEST
        _rm_empty_tree(target, keep_root=keep_root)


def _rm_empty_tree(root: Path, *, keep_root: bool) -> None:
    if root.is_symlink() or not root.is_dir():
        if not keep_root and root.is_dir() and not root.is_symlink():
            try:
                root.rmdir()
            except OSError:
                pass
        return
    try:
        entries = list(os.scandir(root))
    except OSError:
        return
    for entry in entries:
        try:
            if entry.is_symlink():
                continue
            if entry.is_dir(follow_symlinks=False):
                _rm_empty_tree(Path(entry.path), keep_root=False)
        except OSError:
            continue
    if keep_root:
        return
    try:
        root.rmdir()
    except OSError:
        pass


def _append_history(stats: CleanStats) -> None:
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "id": stats.rule_id,
        "files": stats.deleted_files,
        "bytes": stats.deleted_bytes,
        "errors": stats.errors,
        "dry_run": stats.dry_run,
    }
    try:
        with history_file().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass
