from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from limpieza.clean import clean_hit
from limpieza.i18n import I18n
from limpieza.models import Hit, Safety
from limpieza.paths import current, fmt_bytes
from limpieza.rules import builtin_rules
from limpieza.scan import measure


def run_gui(i18n: I18n | None = None) -> None:
    i18n = i18n or I18n()
    App(i18n).mainloop()


class App(tk.Tk):
    def __init__(self, i18n: I18n) -> None:
        super().__init__()
        self.i18n = i18n
        self.hits: dict[str, Hit] = {}
        self.title(i18n.t("title"))
        self.geometry("980x620")
        self.minsize(760, 480)

        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Button(top, text=i18n.t("scan_btn"), command=self.do_scan).pack(side="left")
        ttk.Button(top, text=i18n.t("clean_btn"), command=self.do_clean).pack(side="left", padx=(8, 0))
        self.dry = tk.BooleanVar(value=True)
        self.safe = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text=i18n.t("dry_chk"), variable=self.dry).pack(side="left", padx=12)
        ttk.Checkbutton(top, text=i18n.t("safe_chk"), variable=self.safe).pack(side="left")
        self.status = ttk.Label(top, text=i18n.t("tagline"))
        self.status.pack(side="right")

        cols = ("sel", "id", "name", "safety", "size", "files", "reason")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="extended")
        headings = {
            "sel": i18n.t("select"),
            "id": i18n.t("col_id"),
            "name": i18n.t("col_name"),
            "safety": i18n.t("col_safety"),
            "size": i18n.t("col_size"),
            "files": i18n.t("col_files"),
            "reason": i18n.t("col_reason"),
        }
        widths = {"sel": 70, "id": 140, "name": 180, "safety": 80, "size": 90, "files": 80, "reason": 320}
        for col in cols:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], stretch=col in {"name", "reason"})
        self.tree.tag_configure("safe", foreground="#0a7f3f")
        self.tree.tag_configure("review", foreground="#a15c00")
        self.tree.bind("<Double-1>", self._toggle)
        self.tree.bind("<space>", self._toggle)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scroll.pack(side="left", fill="y", pady=8)

        log_frame = ttk.LabelFrame(self, text=i18n.t("log"), padding=6)
        log_frame.pack(side="bottom", fill="both", expand=False, padx=8, pady=(0, 8))
        self.log = tk.Text(log_frame, height=8, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)

        self.after(200, self.do_scan)

    def _toggle(self, event: tk.Event | None = None) -> str:
        item = self.tree.focus()
        if not item:
            return "break"
        vals = list(self.tree.item(item, "values"))
        vals[0] = "[ ]" if vals[0] == "[x]" else "[x]"
        self.tree.item(item, values=vals)
        return "break"

    def _write(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.update_idletasks()

    def do_scan(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.hits.clear()
        self.status.configure(text=self.i18n.t("scan") + "…")
        self._write(self.i18n.t("scan") + "…")
        safe_only = self.safe.get()
        threading.Thread(target=self._scan_worker, args=(safe_only,), daemon=True).start()

    def _scan_worker(self, safe_only: bool) -> None:
        loc = current()
        found: list[Hit] = []
        for rule in builtin_rules(loc):
            if safe_only and rule.safety != Safety.SAFE:
                continue
            hit = measure(rule)
            if hit.missing or hit.bytes <= 0:
                continue
            found.append(hit)
        self.after(0, lambda: self._show_hits(found))

    def _show_hits(self, found: list[Hit]) -> None:
        self.hits = {hit.rule.id: hit for hit in found}
        for hit in found:
            rule = hit.rule
            mark = "[x]" if rule.safety == Safety.SAFE else "[ ]"
            self.tree.insert(
                "",
                "end",
                iid=rule.id,
                values=(
                    mark,
                    rule.id,
                    rule.name,
                    self.i18n.t(rule.safety.value),
                    fmt_bytes(hit.bytes),
                    str(hit.files),
                    rule.reason,
                ),
                tags=(rule.safety.value,),
            )
        total = sum(h.bytes for h in found)
        self.status.configure(text=f"{self.i18n.t('would_free')}: {fmt_bytes(total)}")
        self._write(f"{self.i18n.t('would_free')}: {fmt_bytes(total)}")

    def do_clean(self) -> None:
        selected: list[Hit] = []
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            if vals and vals[0] == "[x]" and item in self.hits:
                selected.append(self.hits[item])
        if not selected:
            messagebox.showinfo(self.i18n.t("app"), self.i18n.t("need_sel"))
            return
        total_bytes = sum(h.bytes for h in selected)
        total_files = sum(h.files for h in selected)
        apply = not self.dry.get()
        if apply and not messagebox.askokcancel(
            self.i18n.t("app"),
            self.i18n.t("confirm_gui", files=total_files, size=fmt_bytes(total_bytes)),
        ):
            return
        if not apply:
            self._write(self.i18n.t("dry_banner"))
        freed = 0
        for hit in selected:
            stats = clean_hit(hit, apply=apply)
            freed += stats.deleted_bytes
            verb = self.i18n.t("would_free") if not apply else self.i18n.t("freed")
            self._write(f"{stats.name}: {verb} {fmt_bytes(stats.deleted_bytes)}")
        self._write(f"{self.i18n.t('done')} {fmt_bytes(freed)}")
        if apply:
            self.do_scan()
