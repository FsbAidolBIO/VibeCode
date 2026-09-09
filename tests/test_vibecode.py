"""Tests for vibecode.py — stdlib unittest, no third-party deps."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import vibecode
from vibecode import (
    analyze_path,
    b64decode_text,
    b64encode_text,
    dashboard_data,
    dump_json,
    format_time,
    generate_password,
    language_for_ext,
    parse_json,
    password_entropy,
    password_pool,
    progress_bar,
    render_banner,
    render_dashboard,
    tier_for_score,
    vibe_checks,
    FONT,
)

ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestHelpers(unittest.TestCase):
    def test_language_for_ext(self):
        self.assertEqual(language_for_ext(".py"), "Python")
        self.assertEqual(language_for_ext(".TS"), "TypeScript")
        self.assertEqual(language_for_ext(".xyz"), "Other")

    def test_format_time(self):
        self.assertEqual(format_time(65), "01:05")
        self.assertEqual(format_time(5), "00:05")
        self.assertEqual(format_time(3661), "01:01:01")

    def test_progress_bar(self):
        self.assertEqual(progress_bar(0.5, 10), "\u2588" * 5 + "\u2591" * 5)
        self.assertEqual(progress_bar(0.0, 4), "\u2591" * 4)
        self.assertEqual(progress_bar(1.0, 4), "\u2588" * 4)

    def test_tier_for_score(self):
        self.assertEqual(tier_for_score(95)[0], "LEGENDARY")
        self.assertEqual(tier_for_score(80)[0], "FIRE")
        self.assertEqual(tier_for_score(65)[0], "SOLID")
        self.assertEqual(tier_for_score(45)[0], "MEH")
        self.assertEqual(tier_for_score(25)[0], "SUS")
        self.assertEqual(tier_for_score(5)[0], "ZOMBIE")


class TestAnalyze(unittest.TestCase):
    def test_analyze_temp_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "main.py", "print(1)\n" * 10)
            write(root / "sub" / "nested.py", "x = 1\n" * 4)
            write(root / "app.js", "console.log(1);\n" * 5)
            write(root / "README.md", "# hi\n\nyo\n")
            (root / "data.bin").write_bytes(b"\x00\x01\x02binary")
            write(root / ".git" / "config", "[core]\n")
            write(root / "node_modules" / "x.js", "nope\n" * 100)

            data = analyze_path(root)
            self.assertEqual(data["files"], 4)
            self.assertEqual(data["lines"], 10 + 4 + 5 + 3)
            self.assertEqual(data["binary_skipped"], 1)
            self.assertEqual(data["langs"]["Python"], {"files": 2, "lines": 14})
            self.assertEqual(data["langs"]["JavaScript"], {"files": 1, "lines": 5})
            self.assertEqual(data["langs"]["Markdown"], {"files": 1, "lines": 3})
            # JSON-serializable for --json output
            json.dumps(data)

    def test_analyze_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = analyze_path(Path(tmp))
            self.assertEqual(data["files"], 0)
            self.assertEqual(data["langs"], {})


class TestVibeCheck(unittest.TestCase):
    def _healthy_repo(self, root: Path) -> None:
        write(root / "README.md", "# test\n")
        write(root / "LICENSE", "MIT\n")
        write(root / ".gitignore", "*.pyc\n")
        write(root / "tests" / "test_x.py", "def test_x(): pass\n")
        write(root / "pyproject.toml", "[project]\nname='x'\n")
        write(root / "docs" / "index.md", "# docs\n")
        for i in range(7):
            write(root / "src" / f"mod{i}.py", "x = 1\n")

    def test_healthy_repo_scores_high(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._healthy_repo(root)
            score, checks = vibe_checks(root)
            self.assertGreaterEqual(score, 60)
            self.assertEqual(len(checks), 10)
            self.assertLessEqual(score, 100)

    def test_code_check_counts_web_sources(self):
        import vibecode as _v
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "a.py", "x = 1\n")
            write(root / "b.py", "x = 2\n")
            write(root / "index.html", "<h1>hi</h1>\n")
            write(root / "app.css", "a{}\n")
            self.assertGreater(_v._count_code_files(root), 3)
            _, checks = vibe_checks(root)
            code = next(c for c in checks if c["key"] == "code")
            self.assertTrue(code["passed"])

    def test_empty_dir_scores_low(self):
        with tempfile.TemporaryDirectory() as tmp:
            score, _ = vibe_checks(Path(tmp))
            self.assertLessEqual(score, 20)


class TestBanner(unittest.TestCase):
    def test_font_glyphs_are_5x5(self):
        for ch, glyph in FONT.items():
            self.assertEqual(len(glyph), 5, f"glyph {ch!r} must have 5 rows")
            for row in glyph:
                self.assertEqual(len(row), 5, f"glyph {ch!r} row {row!r} must be 5 wide")

    def test_render_banner_shape(self):
        out = render_banner("Hi!")
        rows = out.split("\n")
        self.assertEqual(len(rows), 5)
        self.assertIn("#", out)

    def test_render_banner_custom_fill_and_unknown_char(self):
        out = render_banner("A~B", fill="*")
        self.assertIn("*", out)
        self.assertNotIn("#", out.replace("?", ""))  # fill replaced everywhere


class TestJsonTools(unittest.TestCase):
    def test_roundtrip(self):
        obj = parse_json('{"b": 2, "a": [1, 2]}')
        self.assertEqual(obj, {"b": 2, "a": [1, 2]})
        pretty = dump_json(obj, indent=2, sort_keys=True)
        self.assertLess(pretty.index('"a"'), pretty.index('"b"'))
        mini = dump_json(obj, sort_keys=True, minify=True)
        self.assertEqual(mini, '{"a":[1,2],"b":2}')

    def test_invalid_raises(self):
        with self.assertRaises(json.JSONDecodeError):
            parse_json("{nope")


class TestB64(unittest.TestCase):
    def test_roundtrip_unicode(self):
        s = "Hello, Vibe! Привет 🌊"
        self.assertEqual(b64decode_text(b64encode_text(s)), s)

    def test_invalid_raises(self):
        with self.assertRaises(Exception):
            b64decode_text("!!! not base64 !!!")


class TestPassgen(unittest.TestCase):
    def test_length_and_charset(self):
        pool = set(password_pool(True))
        for _ in range(5):
            p = generate_password(20, True)
            self.assertEqual(len(p), 20)
            self.assertTrue(set(p) <= pool)

    def test_no_symbols(self):
        import string as _string

        pool = set(password_pool(False))
        self.assertFalse(pool & set(_string.punctuation))
        p = generate_password(12, False)
        self.assertEqual(len(p), 12)
        self.assertTrue(set(p) <= pool)

    def test_entropy_monotonic(self):
        self.assertGreater(password_entropy(20, 90), password_entropy(8, 26))
        self.assertGreater(password_entropy(8, 26), 0)


class TestDashboard(unittest.TestCase):
    def test_dashboard_data_and_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "a.py", "x = 1\n")
            d = dashboard_data(root)
            for key in ("time", "date", "cpu", "disk", "branch", "files", "lines", "quote"):
                self.assertIn(key, d)
            html = render_dashboard(d, root)
            self.assertIn("VibeCode", html)
            self.assertIn(d["time"], html)


class TestWebPlayground(unittest.TestCase):
    def test_index_html_exists_and_has_tools(self):
        index = ROOT / "index.html"
        self.assertTrue(index.exists(), "index.html web playground must exist")
        content = index.read_text(encoding="utf-8").lower()
        for marker in ["vibecode", "json", "regex", "base64", "password", "pomodoro", "sort", "markdown"]:
            self.assertIn(marker, content, f"index.html should contain {marker!r}")


class TestCliSmoke(unittest.TestCase):
    def test_main_version_and_help(self):
        with self.assertRaises(SystemExit) as ctx:
            vibecode.main(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertEqual(vibecode.main([]), 0)

    def test_cmd_analyze_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp) / "a.py", "x = 1\n")
            self.assertEqual(vibecode.main(["analyze", tmp, "--json"]), 0)

    def test_cmd_vibe_check_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(vibecode.main(["vibe-check", tmp, "--json"]), 0)


if __name__ == "__main__":
    unittest.main()
