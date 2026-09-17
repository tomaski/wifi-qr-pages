# WiFi QR Pages

CLI tool that turns WiFi credentials into printable A4 PDF pages with a QR code
your guests can scan to join the network. Pages are rendered from Jinja2 HTML
templates in `templates/`, so the layout is edited as HTML/CSS, not code.

```
WiFi QRcode
scan to connect
   [ QR code ]
WiFi name     | My Network
WiFi Password | s3cret-pass
       Living room
```

## Install

```bash
./setup.sh
```

Requires [uv](https://docs.astral.sh/uv/) and a system Python 3.14 on `PATH`
(`brew install uv python@3.14`). Everything the app needs is installed **inside
this directory**:

| Path | Contents |
|---|---|
| `.venv/` | virtual environment (jinja2, segno, playwright) |
| `.tools/browsers/` | headless Chromium used as the PDF engine |
| `.tools/cache/`, `.tools/tmp/` | caches and temp files (redirected from `$HOME`) |
| `templates/fonts/` | Inter + JetBrains Mono (OFL), embedded into the PDFs |

Nothing is written to `$HOME`, no shell profile is touched, no fonts are
installed system-wide: deleting this folder removes the tool completely.

## Usage

Single page:

```bash
./qrpages single --ssid "My Network" --password "s3cret-pass" --comment "Living room"
```

Bulk — every `*.csv` in `input/` (or the paths you pass), one page per row:

```bash
./qrpages bulk
./qrpages bulk input/office.csv ~/some/other/folder
```

PDFs land in `output/` as `SSID-comment.pdf` (`SSID.pdf` when there is no
comment); spaces and filesystem-unsafe characters become `_`, and duplicates get
a `-2`, `-3`, … suffix.

Options shared by both modes: `--config PATH`, `--template NAME`,
`--output-dir DIR`. Run `./qrpages --help` or `./qrpages bulk --help` for details.

### CSV format

Header row required. Only `ssid` is mandatory; `,`, `;` and tab separators are
detected automatically.

```csv
ssid,password,comment,security,hidden
Home Net,Il10O-pass-1,Living room,WPA,false
Cafe Public,,Free access - no password,nopass,false
```

| Column | Aliases | Meaning |
|---|---|---|
| `ssid` | `name`, `wifi name` | network name (required) |
| `password` | `pass`, `key` | leave empty for open networks |
| `comment` | `description` | printed under the credentials, used in the file name |
| `security` | — | `WPA` (default), `WEP`, or `nopass`/`open` |
| `hidden` | — | `true`/`yes`/`1` marks the network as hidden |

Rows without an ssid or with an unknown security type are reported as warnings
and skipped; the rest of the file still renders.

## Configuration — `config.toml`

```toml
template = "a4.html.j2"       # file in templates/

[typography]                  # colors of the non-monospace text
header_color = "#000000"      # "WiFi QRcode"
subheader_color = "#555555"   # "scan to connect"
comment_color = "#333333"

[qr]
error_correction = "M"        # L (7%) | M (15%) | Q (25%) | H (30%)
color = "#000000"
background = "#FFFFFF"

[display]
credentials = true            # show the WiFi name / WiFi Password block
comment = true                # show the comment line
```

Sizes, spacing and the black/light-grey credential pills live in the template's
CSS, where every value is a fixed millimetre measurement.

## Templates

`templates/a4.html.j2` is a self-contained A4 page: `@page { size: 210mm 297mm }`,
all lengths in `mm`, fonts embedded from `templates/fonts/`. Available variables:

| Variable | Description |
|---|---|
| `ssid`, `password`, `comment` | the network's data |
| `qr_svg` | inline `<svg>` with a `viewBox` — size it with CSS (`.qr > svg`) |
| `typography`, `qr`, `display` | the config sections |
| `fonts_url` | `file://` URL of `templates/fonts` for `@font-face` |

Copy it to e.g. `templates/a5.html.j2`, adjust, and select it with
`--template a5.html.j2` or the `template` key in `config.toml`.

## Tests

```bash
./run-tests.sh
```

Covers CSV parsing, WiFi payload escaping, file naming and config validation
(stdlib `unittest`, no extra dependencies).

## Notes

- The generated page box is 209.9 × 297.0 mm: Chromium rounds millimetres to
  whole CSS pixels when it writes the PDF. That is 0.05 % under A4 and prints
  without scaling on any A4 printer.
- Passwords are rendered in JetBrains Mono, which distinguishes `I l 1`,
  `0 O` and `5 S` — important when someone types the password by hand.
- A password in a QR code is only as private as the sheet of paper it is printed
  on; `display.credentials = false` prints the code without the plain-text
  credentials.
