"""Command line interface: `qrpages bulk` and `qrpages single`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import ConfigError, load_config
from .csvinput import CsvError, collect_csv_files, read_networks
from .naming import pdf_filename, unique_filename
from .qr import QrError, normalize_security
from .render import Network, PdfRenderer, RenderError

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_DIR / "config.toml"
DEFAULT_INPUT = PROJECT_DIR / "input"
DEFAULT_OUTPUT = PROJECT_DIR / "output"
TEMPLATES_DIR = PROJECT_DIR / "templates"
FONTS_DIR = TEMPLATES_DIR / "fonts"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrpages",
        description="Generate printable A4 PDF pages with WiFi QR codes.",
    )
    parser.add_argument("--version", action="version", version=f"qrpages {__version__}")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        metavar="PATH",
        help="configuration file (default: config.toml)",
    )
    common.add_argument(
        "--template",
        metavar="NAME",
        help="template file inside templates/ (default: from config)",
    )
    common.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        metavar="DIR",
        help="where the PDFs are written (default: output/)",
    )

    sub = parser.add_subparsers(dest="mode", required=True)

    bulk = sub.add_parser(
        "bulk",
        parents=[common],
        help="render every row of one or more CSV files",
        description=(
            "Render a page per CSV row. Without PATH, every *.csv in input/ is used. "
            "Columns: ssid (required), password, comment, security, hidden."
        ),
    )
    bulk.add_argument(
        "paths",
        nargs="*",
        type=Path,
        metavar="PATH",
        help="CSV files or directories (default: input/)",
    )

    single = sub.add_parser(
        "single",
        parents=[common],
        help="render one page from the given credentials",
    )
    single.add_argument("--ssid", required=True, help="network name")
    single.add_argument("--password", default="", help="network password")
    single.add_argument("--comment", default="", help="optional comment line")
    single.add_argument(
        "--security",
        default="WPA",
        help="WPA (default), WEP or nopass for an open network",
    )
    single.add_argument(
        "--hidden", action="store_true", help="mark the network as hidden"
    )
    return parser


def _display_path(path: Path) -> str:
    """Shorten a path for console output when it sits inside the project."""
    resolved = path.resolve()
    if resolved.is_relative_to(PROJECT_DIR):
        return str(resolved.relative_to(PROJECT_DIR))
    return str(resolved)


def _render_all(
    networks: list[tuple[Network, str]],
    args: argparse.Namespace,
    config,
) -> int:
    """Render (network, filename) pairs; returns the number of failures."""
    renderer = PdfRenderer(config, TEMPLATES_DIR, FONTS_DIR)
    renderer.load_template(args.template)  # fail fast on a bad template name
    print(f"Rendering {len(networks)} page(s) into {args.output_dir}", flush=True)

    failures = 0
    with renderer:
        for network, filename in networks:
            destination = args.output_dir / filename
            try:
                renderer.render(network, destination, args.template)
            except (RenderError, QrError) as exc:
                print(f"  failed: {network.ssid}: {exc}", flush=True)
                failures += 1
                continue
            print(f"  {_display_path(destination)}", flush=True)
    return failures


def run_single(args: argparse.Namespace, config) -> int:
    if not args.ssid.strip():
        raise QrError("--ssid must not be empty")
    network = Network(
        ssid=args.ssid,
        password=args.password,
        comment=args.comment,
        security=normalize_security(args.security),
        hidden=args.hidden,
    )
    filename = pdf_filename(network.ssid, network.comment)
    return 1 if _render_all([(network, filename)], args, config) else 0


def run_bulk(args: argparse.Namespace, config) -> int:
    files = collect_csv_files(args.paths, DEFAULT_INPUT)
    if not files:
        print(f"No CSV files found in {DEFAULT_INPUT}", file=sys.stderr)
        return 1

    jobs: list[tuple[Network, str]] = []
    taken: set[str] = set()
    for file in files:
        networks, warnings = read_networks(file)
        print(f"{_display_path(file)}: {len(networks)} network(s)")
        for warning in warnings:
            print(f"  warning: {warning}")
        for network in networks:
            name = unique_filename(pdf_filename(network.ssid, network.comment), taken)
            jobs.append((network, name))

    if not jobs:
        print("Nothing to render.", file=sys.stderr)
        return 1

    failures = _render_all(jobs, args, config)
    print(f"Done: {len(jobs) - failures} written, {failures} failed")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        if args.mode == "single":
            return run_single(args, config)
        return run_bulk(args, config)
    except (ConfigError, CsvError, QrError, RenderError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
