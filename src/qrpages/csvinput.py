"""Reading networks from CSV files (bulk mode)."""

from __future__ import annotations

import csv
from pathlib import Path

from .qr import QrError, normalize_security
from .render import Network

# Accepted column names (lower-cased) -> canonical field
COLUMNS = {
    "ssid": "ssid",
    "name": "ssid",
    "wifi name": "ssid",
    "wifi_name": "ssid",
    "password": "password",
    "pass": "password",
    "key": "password",
    "comment": "comment",
    "description": "comment",
    "security": "security",
    "hidden": "hidden",
}
TRUE_VALUES = {"1", "true", "yes", "y", "on"}


class CsvError(Exception):
    """Raised when a CSV file cannot be read or lacks an ssid column."""


def _delimiter(header_line: str) -> str:
    """Pick the delimiter that splits the header row into the most columns.

    csv.Sniffer chokes on files with quoted values or ragged rows, and the
    header alone is enough to tell `,` from `;` or a tab.
    """
    counts = {candidate: header_line.count(candidate) for candidate in ",;\t"}
    best = max(counts, key=lambda candidate: counts[candidate])
    return best if counts[best] else ","


def read_networks(path: Path) -> tuple[list[Network], list[str]]:
    """Return (networks, warnings) parsed from *path*.

    Required header column: ssid (aliases: name, wifi name).
    Optional: password, comment, security, hidden.
    """
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise CsvError(f"{path}: {exc.strerror}") from None

    if not text.strip():
        return [], [f"{path.name}: file is empty"]

    lines = text.splitlines()
    reader = csv.DictReader(lines, delimiter=_delimiter(lines[0]))
    if not reader.fieldnames:
        raise CsvError(f"{path.name}: missing header row")

    mapping = {}
    for raw in reader.fieldnames:
        canonical = COLUMNS.get((raw or "").strip().lower())
        if canonical and canonical not in mapping.values():
            mapping[raw] = canonical
    if "ssid" not in mapping.values():
        raise CsvError(
            f"{path.name}: no 'ssid' column found "
            f"(header: {', '.join(f or '' for f in reader.fieldnames)})"
        )

    networks: list[Network] = []
    warnings: list[str] = []
    for line_number, row in enumerate(reader, start=2):
        values = {
            field: (row.get(raw) or "").strip() for raw, field in mapping.items()
        }
        if not values.get("ssid"):
            if any(values.values()):
                warnings.append(f"{path.name} line {line_number}: empty ssid, skipped")
            continue
        try:
            security = normalize_security(values.get("security"))
        except QrError as exc:
            warnings.append(f"{path.name} line {line_number}: {exc}, skipped")
            continue
        networks.append(
            Network(
                ssid=values["ssid"],
                password=values.get("password", ""),
                comment=values.get("comment", ""),
                security=security,
                hidden=values.get("hidden", "").lower() in TRUE_VALUES,
            )
        )
    return networks, warnings


def collect_csv_files(paths: list[Path], default_dir: Path) -> list[Path]:
    """Expand CLI paths (files or directories) into a sorted list of CSV files."""
    if not paths:
        paths = [default_dir]
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(p for p in path.glob("*.csv") if p.is_file()))
        elif path.is_file():
            files.append(path)
        else:
            raise CsvError(f"path not found: {path}")
    # Preserve order, drop duplicates
    seen: set[Path] = set()
    unique = []
    for file in files:
        resolved = file.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(file)
    return unique
