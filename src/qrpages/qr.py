"""WiFi payload building and inline-SVG QR code generation (segno)."""

from __future__ import annotations

import segno
from segno import helpers

from .config import QrSettings

SECURITY_TYPES = {"WPA": "WPA", "WEP": "WEP", "NOPASS": "nopass"}
QUIET_ZONE_MODULES = 2


class QrError(Exception):
    """Raised when the credentials cannot be encoded into a QR code."""


def normalize_security(value: str | None) -> str | None:
    """Map user input to a WIFI: security token; None/'nopass' means open network."""
    if value is None or not str(value).strip():
        return "WPA"
    key = str(value).strip().upper()
    if key in ("NONE", "OPEN", "NOPASS"):
        return None
    try:
        return SECURITY_TYPES[key]
    except KeyError:
        raise QrError(
            f"unknown security type {value!r} (expected WPA, WEP or nopass)"
        ) from None


def wifi_payload(
    ssid: str, password: str | None, security: str | None, hidden: bool
) -> str:
    """Return the `WIFI:...;;` string; segno handles escaping of : ; , \\ and \"."""
    return helpers.make_wifi_data(
        ssid=ssid,
        password=password or None,
        security=security,
        hidden=hidden,
    )


def wifi_svg(
    ssid: str,
    password: str | None,
    settings: QrSettings,
    security: str | None = "WPA",
    hidden: bool = False,
) -> str:
    """Render the WiFi QR code as an inline <svg> sized by the template's CSS.

    `omitsize=True` emits a viewBox without width/height, so the template can
    scale the code to an exact millimetre size.
    """
    payload = wifi_payload(ssid, password, security, hidden)
    try:
        code = segno.make_qr(payload, error=settings.error_correction.lower())
    except segno.DataOverflowError as exc:
        raise QrError(f"credentials too long to encode: {exc}") from None
    return code.svg_inline(
        dark=settings.color,
        light=settings.background,
        border=QUIET_ZONE_MODULES,
        omitsize=True,
    )
