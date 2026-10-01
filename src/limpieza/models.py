from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Safety(str, Enum):
    SAFE = "safe"
    REVIEW = "review"


class Kind(str, Enum):
    DIR = "dir"
    NAMED_SUBDIRS = "named_subdirs"
    KEEP_LATEST = "keep_latest"
    GLOB = "glob"


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    safety: Safety
    reason: str
    roots: tuple[Path, ...]
    kind: Kind = Kind.DIR
    names: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()
    keep: int = 1
    min_age_hours: int = 0
    owner_only: bool = False


@dataclass
class Hit:
    rule: Rule
    bytes: int = 0
    files: int = 0
    dirs: int = 0
    skipped_errors: int = 0
    missing: bool = False
    samples: list[str] = field(default_factory=list)

    @property
    def reclaimable(self) -> bool:
        return self.bytes > 0 and not self.missing


@dataclass
class CleanStats:
    rule_id: str
    name: str
    deleted_files: int = 0
    deleted_bytes: int = 0
    skipped: int = 0
    errors: int = 0
    dry_run: bool = True
