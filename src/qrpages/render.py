"""Jinja2 -> HTML -> PDF rendering via a project-local headless Chromium."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound
from jinja2 import select_autoescape
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from .config import Config
from .qr import wifi_svg


class RenderError(Exception):
    """Raised when a template is missing or the PDF engine fails."""


@dataclass(frozen=True)
class Network:
    """One WiFi network to render as a page.

    `security` holds a canonical WIFI: token ("WPA", "WEP") or None for an open
    network; use qr.normalize_security() when building one from user input.
    """

    ssid: str
    password: str = ""
    comment: str = ""
    security: str | None = "WPA"
    hidden: bool = False


class PdfRenderer:
    """Renders pages to PDF, reusing one browser instance for the whole run."""

    def __init__(self, config: Config, templates_dir: Path, fonts_dir: Path):
        self.config = config
        self.templates_dir = templates_dir
        self.fonts_dir = fonts_dir
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(default_for_string=True, default=True),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )
        self._playwright = None
        self._browser = None

    def __enter__(self) -> PdfRenderer:
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch()
        except PlaywrightError as exc:
            self.__exit__(None, None, None)
            raise RenderError(
                f"could not start the bundled Chromium ({exc}). "
                "Run ./setup.sh to (re)install it."
            ) from None
        return self

    def __exit__(self, *_exc) -> None:
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def load_template(self, template_name: str | None = None):
        """Return the compiled template; raises RenderError if it is missing.

        Called before the browser starts so a typo fails fast.
        """
        name = template_name or self.config.template
        try:
            return self.env.get_template(name)
        except TemplateNotFound:
            raise RenderError(
                f"template {name!r} not found in {self.templates_dir}"
            ) from None

    def html_for(self, network: Network, template_name: str | None = None) -> str:
        template = self.load_template(template_name)
        cfg = self.config
        return template.render(
            ssid=network.ssid,
            password=network.password,
            comment=network.comment,
            qr_svg=wifi_svg(
                network.ssid,
                network.password,
                cfg.qr,
                security=network.security,
                hidden=network.hidden,
            ),
            typography=cfg.typography,
            qr=cfg.qr,
            display=cfg.display,
            fonts_url=self.fonts_dir.resolve().as_uri(),
        )

    def render(
        self, network: Network, destination: Path, template_name: str | None = None
    ) -> Path:
        """Render one network to *destination* (a .pdf path) and return that path."""
        if self._browser is None:
            raise RenderError("renderer used outside of its context manager")
        html = self.html_for(network, template_name)
        page = self._browser.new_page()
        try:
            # A file:// base URL lets the template reference the bundled fonts.
            page.goto(self.templates_dir.resolve().as_uri() + "/")
            page.set_content(html, wait_until="load")
            page.evaluate("document.fonts.ready")
            destination.parent.mkdir(parents=True, exist_ok=True)
            page.pdf(
                path=str(destination),
                prefer_css_page_size=True,
                print_background=True,
            )
        except PlaywrightError as exc:
            raise RenderError(f"PDF generation failed for {network.ssid!r}: {exc}") from None
        finally:
            page.close()
        return destination
