"""Loading and validation of config.toml."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
ERROR_LEVELS = ("L", "M", "Q", "H")


class ConfigError(Exception):
    """Raised when config.toml is missing, malformed or holds invalid values."""


@dataclass(frozen=True)
class Typography:
    header_color: str = "#000000"
    subheader_color: str = "#555555"
    comment_color: str = "#333333"


@dataclass(frozen=True)
class QrSettings:
    error_correction: str = "M"
    color: str = "#000000"
    background: str = "#FFFFFF"


@dataclass(frozen=True)
class Display:
    credentials: bool = True
    comment: bool = True


@dataclass(frozen=True)
class Config:
    template: str = "a4.html.j2"
    typography: Typography = field(default_factory=Typography)
    qr: QrSettings = field(default_factory=QrSettings)
    display: Display = field(default_factory=Display)


def _section(data: dict, name: str) -> dict:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ConfigError(f"[{name}] must be a table")
    return value


def _color(section: dict, table: str, key: str, default: str) -> str:
    value = section.get(key, default)
    if not isinstance(value, str) or not HEX_COLOR.match(value):
        raise ConfigError(
            f"{table}.{key}: expected a hex color like '#1a2b3c', got {value!r}"
        )
    return value


def _flag(section: dict, table: str, key: str, default: bool) -> bool:
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"{table}.{key}: expected true or false, got {value!r}")
    return value


def load_config(path: Path) -> Config:
    """Read *path* and return a validated Config. Missing keys fall back to defaults."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"configuration file not found: {path}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: invalid TOML ({exc})") from None

    template = data.get("template", "a4.html.j2")
    if not isinstance(template, str) or not template:
        raise ConfigError(f"template: expected a file name, got {template!r}")

    typo = _section(data, "typography")
    qr = _section(data, "qr")
    display = _section(data, "display")

    level = qr.get("error_correction", "M")
    if not isinstance(level, str) or level.upper() not in ERROR_LEVELS:
        raise ConfigError(
            "qr.error_correction: expected one of "
            f"{', '.join(ERROR_LEVELS)}, got {level!r}"
        )

    return Config(
        template=template,
        typography=Typography(
            header_color=_color(typo, "typography", "header_color", "#000000"),
            subheader_color=_color(typo, "typography", "subheader_color", "#555555"),
            comment_color=_color(typo, "typography", "comment_color", "#333333"),
        ),
        qr=QrSettings(
            error_correction=level.upper(),
            color=_color(qr, "qr", "color", "#000000"),
            background=_color(qr, "qr", "background", "#FFFFFF"),
        ),
        display=Display(
            credentials=_flag(display, "display", "credentials", True),
            comment=_flag(display, "display", "comment", True),
        ),
    )
