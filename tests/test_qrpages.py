"""Unit tests for the non-rendering logic. Run: ./run-tests.sh"""

import tempfile
import unittest
from pathlib import Path

from qrpages.config import ConfigError, load_config
from qrpages.csvinput import CsvError, collect_csv_files, read_networks
from qrpages.naming import pdf_filename, unique_filename
from qrpages.qr import QrError, normalize_security, wifi_payload

PROJECT_DIR = Path(__file__).resolve().parents[1]


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(dir=PROJECT_DIR / ".tools" / "tmp")
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write(self, name: str, content: str) -> Path:
        path = self.tmp / name
        path.write_text(content, encoding="utf-8")
        return path


class NamingTests(unittest.TestCase):
    def test_ssid_and_comment(self):
        self.assertEqual(
            pdf_filename("Home Net", "Living room"), "Home_Net-Living_room.pdf"
        )

    def test_no_comment(self):
        self.assertEqual(pdf_filename("Home Net", ""), "Home_Net.pdf")
        self.assertEqual(pdf_filename("Home Net", None), "Home_Net.pdf")
        self.assertEqual(pdf_filename("Home Net", "   "), "Home_Net.pdf")

    def test_unsafe_characters_replaced(self):
        self.assertEqual(pdf_filename('a/b:c*d?e"f<g>h|i'), "a_b_c_d_e_f_g_h_i.pdf")

    def test_unnamed_fallback(self):
        self.assertEqual(pdf_filename("///"), "unnamed.pdf")

    def test_collisions_get_suffixes(self):
        taken: set[str] = set()
        names = [unique_filename("a.pdf", taken) for _ in range(3)]
        self.assertEqual(names, ["a.pdf", "a-2.pdf", "a-3.pdf"])


class SecurityTests(unittest.TestCase):
    def test_defaults_to_wpa(self):
        for value in (None, "", "   ", "wpa", "WPA"):
            self.assertEqual(normalize_security(value), "WPA")

    def test_open_network(self):
        for value in ("nopass", "none", "OPEN"):
            self.assertIsNone(normalize_security(value))

    def test_wep(self):
        self.assertEqual(normalize_security("wep"), "WEP")

    def test_unknown(self):
        with self.assertRaises(QrError):
            normalize_security("WPA4")


class PayloadTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(
            wifi_payload("My Net", "secret", "WPA", False),
            "WIFI:T:WPA;S:My Net;P:secret;;",
        )

    def test_open_network_omits_password(self):
        self.assertEqual(wifi_payload("Cafe", "", None, False), "WIFI:S:Cafe;;")

    def test_hidden_flag(self):
        self.assertIn("H:true", wifi_payload("Net", "pw", "WPA", True))

    def test_special_characters_are_escaped(self):
        payload = wifi_payload("a;b", "c:d\\e", "WPA", False)
        self.assertIn(r"S:a\;b", payload)
        self.assertIn(r"P:c\:d\\e", payload)


class CsvTests(TempDirTest):
    def test_comma_file(self):
        path = self.write(
            "a.csv",
            "ssid,password,comment\nHome,pw,Living room\n",
        )
        networks, warnings = read_networks(path)
        self.assertEqual(warnings, [])
        self.assertEqual(len(networks), 1)
        self.assertEqual(networks[0].ssid, "Home")
        self.assertEqual(networks[0].password, "pw")
        self.assertEqual(networks[0].comment, "Living room")
        self.assertEqual(networks[0].security, "WPA")
        self.assertFalse(networks[0].hidden)

    def test_semicolon_file_and_aliases(self):
        path = self.write("b.csv", "Name;Key;Description\nHome;pw;note\n")
        networks, _ = read_networks(path)
        self.assertEqual(
            (networks[0].ssid, networks[0].password, networks[0].comment),
            ("Home", "pw", "note"),
        )

    def test_optional_columns(self):
        path = self.write(
            "c.csv",
            "ssid,password,security,hidden\nA,,nopass,no\nB,pw,wep,YES\n",
        )
        networks, _ = read_networks(path)
        self.assertIsNone(networks[0].security)
        self.assertFalse(networks[0].hidden)
        self.assertEqual(networks[1].security, "WEP")
        self.assertTrue(networks[1].hidden)

    def test_bad_rows_are_warnings_not_failures(self):
        path = self.write(
            "d.csv",
            "ssid,password,security\n,orphan,\nOk,pw,\nBad,pw,WPA4\n",
        )
        networks, warnings = read_networks(path)
        self.assertEqual([n.ssid for n in networks], ["Ok"])
        self.assertEqual(len(warnings), 2)
        self.assertIn("line 2", warnings[0])
        self.assertIn("line 4", warnings[1])

    def test_missing_ssid_column(self):
        path = self.write("e.csv", "foo,bar\n1,2\n")
        with self.assertRaises(CsvError):
            read_networks(path)

    def test_empty_file(self):
        path = self.write("f.csv", "")
        networks, warnings = read_networks(path)
        self.assertEqual(networks, [])
        self.assertEqual(len(warnings), 1)

    def test_collect_files(self):
        self.write("one.csv", "ssid\nA\n")
        self.write("two.csv", "ssid\nB\n")
        self.write("skip.txt", "nope")
        self.assertEqual(
            [p.name for p in collect_csv_files([], self.tmp)], ["one.csv", "two.csv"]
        )
        self.assertEqual(
            [p.name for p in collect_csv_files([self.tmp / "two.csv"], self.tmp)],
            ["two.csv"],
        )
        with self.assertRaises(CsvError):
            collect_csv_files([self.tmp / "missing.csv"], self.tmp)


class ConfigTests(TempDirTest):
    def test_project_config_loads(self):
        config = load_config(PROJECT_DIR / "config.toml")
        self.assertEqual(config.template, "a4.html.j2")
        self.assertTrue(config.display.credentials)

    def test_defaults_when_keys_missing(self):
        config = load_config(self.write("min.toml", ""))
        self.assertEqual(config.qr.error_correction, "M")
        self.assertEqual(config.typography.header_color, "#000000")

    def test_error_correction_is_normalized(self):
        config = load_config(self.write("ec.toml", '[qr]\nerror_correction = "h"\n'))
        self.assertEqual(config.qr.error_correction, "H")

    def test_invalid_values(self):
        cases = [
            '[qr]\nerror_correction = "Z"\n',
            '[qr]\ncolor = "black"\n',
            "[display]\ncomment = 1\n",
            "template = 42\n",
            "[typography]\nheader_color = 1\n",
        ]
        for index, content in enumerate(cases):
            with self.subTest(content=content):
                path = self.write(f"bad{index}.toml", content)
                with self.assertRaises(ConfigError):
                    load_config(path)

    def test_missing_file(self):
        with self.assertRaises(ConfigError):
            load_config(self.tmp / "nope.toml")

    def test_malformed_toml(self):
        with self.assertRaises(ConfigError):
            load_config(self.write("broken.toml", "[qr\n"))


if __name__ == "__main__":
    unittest.main()
