from __future__ import annotations

import locale

TEXTS = {
    "en": {
        "app": "Limpieza",
        "tagline": "Intelligent disk cleaner for Windows and Linux",
        "scan": "Scan",
        "clean": "Clean",
        "gui": "Open the graphical interface",
        "safe_only": "Only regenerable caches and temps",
        "apply": "Actually delete (default is dry-run)",
        "yes": "Do not ask for confirmation",
        "min_size": "Hide targets smaller than this many MB",
        "json": "JSON output",
        "ids": "Comma-separated rule ids",
        "lang": "Language (en or es)",
        "nothing": "Nothing to delete with the current filters.",
        "dry_banner": "DRY-RUN — no files will be deleted. Pass --apply to delete.",
        "confirm": "Type 'delete' to permanently remove {files} files ({size}): ",
        "aborted": "Cancelled.",
        "done": "Done.",
        "would_free": "Would free",
        "freed": "Freed",
        "skipped": "skipped (in use or permission)",
        "col_id": "ID",
        "col_name": "Target",
        "col_safety": "Safety",
        "col_size": "Size",
        "col_files": "Files",
        "col_reason": "Why",
        "safe": "safe",
        "review": "review",
        "scan_btn": "Scan",
        "clean_btn": "Clean selected",
        "dry_chk": "Dry-run (preview only)",
        "safe_chk": "Safe targets only",
        "log": "Log",
        "select": "Include",
        "need_sel": "Select at least one target with reclaimable space.",
        "confirm_gui": "Delete {files} files ({size})?\nThis cannot be undone.",
        "title": "Limpieza — intelligent cleaner",
    },
    "es": {
        "app": "Limpieza",
        "tagline": "Borrado inteligente de disco para Windows y Linux",
        "scan": "Analizar",
        "clean": "Limpiar",
        "gui": "Abrir la interfaz gráfica",
        "safe_only": "Solo caches y temporales regenerables",
        "apply": "Borrar de verdad (por defecto solo simula)",
        "yes": "No pedir confirmación",
        "min_size": "Ocultar objetivos menores de estos MB",
        "json": "Salida JSON",
        "ids": "Ids de reglas separados por coma",
        "lang": "Idioma (en o es)",
        "nothing": "No hay nada que borrar con los filtros actuales.",
        "dry_banner": "SIMULACIÓN — no se borra nada. Usa --apply para borrar.",
        "confirm": "Escribe 'borrar' para eliminar {files} archivos ({size}): ",
        "aborted": "Cancelado.",
        "done": "Listo.",
        "would_free": "Liberaría",
        "freed": "Liberado",
        "skipped": "omitidos (en uso o sin permiso)",
        "col_id": "ID",
        "col_name": "Objetivo",
        "col_safety": "Riesgo",
        "col_size": "Tamaño",
        "col_files": "Archivos",
        "col_reason": "Por qué",
        "safe": "seguro",
        "review": "revisar",
        "scan_btn": "Analizar",
        "clean_btn": "Limpiar selección",
        "dry_chk": "Solo simular (no borrar)",
        "safe_chk": "Solo objetivos seguros",
        "log": "Registro",
        "select": "Incluir",
        "need_sel": "Elige al menos un objetivo con espacio recuperable.",
        "confirm_gui": "¿Borrar {files} archivos ({size})?\nEsto no se puede deshacer.",
        "title": "Limpieza — borrado inteligente",
    },
}


def detect_lang(explicit: str | None = None) -> str:
    if explicit in TEXTS:
        return explicit
    try:
        loc = locale.getlocale()[0] or ""
    except Exception:
        loc = ""
    if loc.lower().startswith("es"):
        return "es"
    return "en"


class I18n:
    def __init__(self, lang: str | None = None) -> None:
        self.lang = detect_lang(lang)

    def t(self, key: str, **kwargs: object) -> str:
        table = TEXTS.get(self.lang, TEXTS["en"])
        text = table.get(key) or TEXTS["en"].get(key, key)
        return text.format(**kwargs) if kwargs else text
