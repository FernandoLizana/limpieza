from __future__ import annotations

import fnmatch
import os
import time
from collections.abc import Iterator
from pathlib import Path

from limpieza.models import Hit, Kind, Rule
from limpieza.paths import is_forbidden

SAMPLE_LIMIT = 8
SKIP_DIR_NAMES = {".git", ".svn", ".hg", "node_modules"}


def iter_targets(rule: Rule) -> Iterator[Path]:
    if rule.kind == Kind.NAMED_SUBDIRS:
        names = set(rule.names)
        for root in rule.roots:
            if not root.exists():
                continue
            yield from _named_subdirs(root, names)
        return

    if rule.kind == Kind.KEEP_LATEST:
        for root in rule.roots:
            if not root.is_dir():
                continue
            subdirs = [p for p in _safe_iterdir(root) if p.is_dir() and not p.is_symlink()]
            subdirs.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
            yield from subdirs[rule.keep :]
        return

    yield from (root for root in rule.roots if root.exists())


def walk_files(rule: Rule) -> Iterator[tuple[Path, os.stat_result]]:
    cutoff = time.time() - rule.min_age_hours * 3600 if rule.min_age_hours else None
    uid = os.getuid() if rule.owner_only and hasattr(os, "getuid") else None
    patterns = rule.patterns

    for target in iter_targets(rule):
        if is_forbidden(target):
            continue
        if target.is_file() and not target.is_symlink():
            try:
                st = target.stat()
            except OSError:
                continue
            if _wanted(target, st, cutoff, uid, patterns, glob_mode=rule.kind == Kind.GLOB):
                yield target, st
            continue
        yield from _walk_dir(target, cutoff, uid, patterns, glob_mode=rule.kind == Kind.GLOB)


def measure(rule: Rule) -> Hit:
    existing = [p for p in rule.roots if p.exists()]
    if not existing:
        return Hit(rule=rule, missing=True)

    hit = Hit(rule=rule)
    for path, st in walk_files(rule):
        hit.files += 1
        hit.bytes += int(st.st_size)
        if len(hit.samples) < SAMPLE_LIMIT:
            hit.samples.append(str(path))
    hit.dirs = sum(1 for _ in iter_targets(rule))
    return hit


def _walk_dir(
    root: Path,
    cutoff: float | None,
    uid: int | None,
    patterns: tuple[str, ...],
    glob_mode: bool,
) -> Iterator[tuple[Path, os.stat_result]]:
    if root.is_symlink() or is_forbidden(root):
        return
    try:
        scan = os.scandir(root)
    except OSError:
        return

    with scan:
        for entry in scan:
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if entry.name in SKIP_DIR_NAMES:
                        continue
                    yield from _walk_dir(Path(entry.path), cutoff, uid, patterns, glob_mode)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
                st = entry.stat(follow_symlinks=False)
                path = Path(entry.path)
                if _wanted(path, st, cutoff, uid, patterns, glob_mode):
                    yield path, st
            except OSError:
                continue


def _wanted(
    path: Path,
    st: os.stat_result,
    cutoff: float | None,
    uid: int | None,
    patterns: tuple[str, ...],
    glob_mode: bool,
) -> bool:
    if cutoff is not None and st.st_mtime > cutoff:
        return False
    if uid is not None and getattr(st, "st_uid", uid) != uid:
        return False
    if glob_mode:
        if not patterns:
            return False
        return any(fnmatch.fnmatch(path.name, pat) for pat in patterns)
    if patterns:
        return any(fnmatch.fnmatch(path.name, pat) for pat in patterns)
    return True


def _named_subdirs(root: Path, names: set[str]) -> Iterator[Path]:
    if root.is_symlink():
        return
    try:
        scan = os.scandir(root)
    except OSError:
        return
    with scan:
        for entry in scan:
            try:
                if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                    continue
                path = Path(entry.path)
                if entry.name in names:
                    yield path
                    continue
                if entry.name in SKIP_DIR_NAMES:
                    continue
                yield from _named_subdirs(path, names)
            except OSError:
                continue


def _safe_iterdir(path: Path) -> list[Path]:
    try:
        return list(path.iterdir())
    except OSError:
        return []
