from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from limpieza import __version__
from limpieza.clean import clean_hit
from limpieza.i18n import I18n
from limpieza.models import Hit, Safety
from limpieza.paths import current, fmt_bytes
from limpieza.rules import builtin_rules
from limpieza.scan import measure


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except Exception:
            continue


def main(argv: Sequence[str] | None = None) -> int:
    _configure_stdio()
    argv = list(sys.argv[1:] if argv is None else argv)
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--lang", choices=("en", "es"), default=None)
    pre_args, _ = pre.parse_known_args(argv)
    i18n = I18n(pre_args.lang)

    parser = argparse.ArgumentParser(
        prog="limpieza",
        description=f"{i18n.t('app')} — {i18n.t('tagline')}",
    )
    parser.add_argument("--lang", choices=("en", "es"), default=pre_args.lang, help=i18n.t("lang"))
    parser.add_argument("--version", action="version", version=f"limpieza {__version__}")
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--lang", choices=("en", "es"), default=pre_args.lang, help=i18n.t("lang"))
    sub = parser.add_subparsers(dest="cmd")

    scan_p = sub.add_parser("scan", help=i18n.t("scan"), parents=[shared])
    _add_filter_args(scan_p, i18n)
    scan_p.add_argument("--json", action="store_true", help=i18n.t("json"))

    clean_p = sub.add_parser("clean", help=i18n.t("clean"), parents=[shared])
    _add_filter_args(clean_p, i18n)
    clean_p.add_argument("--apply", action="store_true", help=i18n.t("apply"))
    clean_p.add_argument("-y", "--yes", action="store_true", help=i18n.t("yes"))

    sub.add_parser("gui", help=i18n.t("gui"), parents=[shared])

    args = parser.parse_args(argv)
    if args.lang:
        i18n = I18n(args.lang)

    if args.cmd == "gui":
        from limpieza.gui import run_gui

        run_gui(i18n)
        return 0
    if args.cmd == "clean":
        return _cmd_clean(args, i18n)
    return _cmd_scan(
        args
        if args.cmd == "scan"
        else argparse.Namespace(safe=False, ids=None, min_size=0, json=False),
        i18n,
    )


def _add_filter_args(parser: argparse.ArgumentParser, i18n: I18n) -> None:
    parser.add_argument("--safe", action="store_true", help=i18n.t("safe_only"))
    parser.add_argument("--id", dest="ids", default=None, help=i18n.t("ids"))
    parser.add_argument("--min-size", type=float, default=0, metavar="MB", help=i18n.t("min_size"))


def _cmd_scan(args: argparse.Namespace, i18n: I18n) -> int:
    hits = _collect(args)
    if getattr(args, "json", False):
        print(json.dumps(_hits_json(hits), indent=2, ensure_ascii=False))
        return 0
    _print_table(hits, i18n)
    total = sum(h.bytes for h in hits)
    print(f"\n{i18n.t('would_free')}: {fmt_bytes(total)}")
    return 0


def _cmd_clean(args: argparse.Namespace, i18n: I18n) -> int:
    hits = [h for h in _collect(args) if h.reclaimable]
    if not hits:
        print(i18n.t("nothing"))
        return 0

    _print_table(hits, i18n)
    total_bytes = sum(h.bytes for h in hits)
    total_files = sum(h.files for h in hits)
    print()
    if not args.apply:
        print(i18n.t("dry_banner"))
        print(f"{i18n.t('would_free')}: {fmt_bytes(total_bytes)} ({total_files} files)")
        return 0

    if not args.yes:
        prompt = i18n.t("confirm", files=total_files, size=fmt_bytes(total_bytes))
        expected = "borrar" if i18n.lang == "es" else "delete"
        try:
            answer = input(prompt).strip().lower()
        except EOFError:
            answer = ""
        if answer != expected:
            print(i18n.t("aborted"))
            return 1

    freed = 0
    skipped = 0
    for hit in hits:
        stats = clean_hit(hit, apply=True)
        freed += stats.deleted_bytes
        skipped += stats.errors + stats.skipped
        print(f"  {stats.name}: {fmt_bytes(stats.deleted_bytes)}  ({stats.deleted_files} files)")
    print(f"\n{i18n.t('done')} {i18n.t('freed')}: {fmt_bytes(freed)}")
    if skipped:
        print(f"  {skipped} {i18n.t('skipped')}")
    return 0


def _collect(args: argparse.Namespace) -> list[Hit]:
    loc = current()
    wanted = {part.strip() for part in (args.ids or "").split(",") if part.strip()}
    min_bytes = int(float(args.min_size) * 1024 * 1024)
    hits: list[Hit] = []
    for rule in builtin_rules(loc):
        if args.safe and rule.safety != Safety.SAFE:
            continue
        if wanted and rule.id not in wanted:
            continue
        if not getattr(args, "json", False):
            print(f"... {rule.id}", file=sys.stderr)
        hit = measure(rule)
        if hit.missing:
            continue
        if hit.bytes < min_bytes:
            continue
        hits.append(hit)
    hits.sort(key=lambda h: h.bytes, reverse=True)
    return hits


def _print_table(hits: list[Hit], i18n: I18n) -> None:
    rows = []
    for hit in hits:
        rows.append(
            (
                hit.rule.id,
                hit.rule.name,
                i18n.t(hit.rule.safety.value),
                fmt_bytes(hit.bytes),
                str(hit.files),
                hit.rule.reason,
            )
        )
    headers = (
        i18n.t("col_id"),
        i18n.t("col_name"),
        i18n.t("col_safety"),
        i18n.t("col_size"),
        i18n.t("col_files"),
        i18n.t("col_reason"),
    )
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = min(max(widths[i], len(cell)), 56)
    def fmt_row(cols: tuple[str, ...]) -> str:
        parts = []
        for i, cell in enumerate(cols):
            text = cell if len(cell) <= widths[i] else cell[: widths[i] - 1] + "…"
            parts.append(text.ljust(widths[i]))
        return "  ".join(parts)

    print(fmt_row(headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt_row(row))


def _hits_json(hits: list[Hit]) -> list[dict[str, object]]:
    return [
        {
            "id": h.rule.id,
            "name": h.rule.name,
            "safety": h.rule.safety.value,
            "bytes": h.bytes,
            "files": h.files,
            "reason": h.rule.reason,
            "roots": [str(p) for p in h.rule.roots],
            "samples": h.samples,
        }
        for h in hits
    ]


if __name__ == "__main__":
    raise SystemExit(main())
