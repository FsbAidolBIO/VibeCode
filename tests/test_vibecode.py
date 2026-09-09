"""Tests for vibecode.py — stdlib unittest, no third-party deps."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
    fetch_url,
    hash_bytes,
    hash_file,
    header_get,
    load_todo,
    lorem_paragraphs,
    lorem_sentences,
    lorem_words,
    make_uuid,
    parse_shortlog,
    punchcard_grid,
    render_punchcard,
    render_rainbow,
    save_todo,
    strip_ansi,
    todo_add,
    todo_clear_done,
    todo_remove,
    todo_set_done,
    vibe_fix,
    week_buckets,
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
        for marker in ["vibecode", "json", "regex", "base64", "password", "pomodoro", "sort",
                    "markdown", "cron", "jwt", "lorem", "camelcase"]:
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


class TestTodo(unittest.TestCase):
    def test_add_done_remove_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "todo.json"
            self.assertEqual(load_todo(p), [])
            items = []
            e1 = todo_add(items, "write tests")
            e2 = todo_add(items, "ship it")
            self.assertEqual((e1["id"], e2["id"]), (1, 2))
            save_todo(items, p)
            self.assertEqual([i["text"] for i in load_todo(p)], ["write tests", "ship it"])
            self.assertTrue(todo_set_done(items, 1, True))
            self.assertFalse(todo_set_done(items, 99, True))
            self.assertEqual(todo_clear_done(items), 1)
            self.assertEqual(len(items), 1)
            self.assertTrue(todo_remove(items, 2))
            self.assertFalse(todo_remove(items, 2))
            self.assertEqual(items, [])

    def test_corrupt_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "todo.json"
            p.write_text("{oops", encoding="utf-8")
            self.assertEqual(load_todo(p), [])


class TestLorem(unittest.TestCase):
    def test_words_count(self):
        import random

        self.assertEqual(len(lorem_words(50, random.Random(1)).split()), 50)
        self.assertEqual(lorem_words(0), "")

    def test_sentences(self):
        import random

        s = lorem_sentences(3, random.Random(2))
        self.assertEqual(s.count("."), 3)
        self.assertTrue(s[0].isupper())

    def test_paragraphs(self):
        import random

        self.assertEqual(len(lorem_paragraphs(2, random.Random(3)).split("\n\n")), 2)


class TestUuidHash(unittest.TestCase):
    def test_uuid_roundtrip(self):
        import uuid as _uuid

        self.assertEqual(_uuid.UUID(make_uuid()).version, 4)
        self.assertEqual(_uuid.UUID(make_uuid(v1=True)).version, 1)
        self.assertEqual(len(make_uuid(dashes=False)), 32)
        self.assertTrue(make_uuid(upper=True).isupper())

    def test_hash_vectors(self):
        self.assertEqual(hash_bytes(b"abc", "sha256"),
                         "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        self.assertEqual(hash_bytes(b"abc", "md5"), "900150983cd24fb0d6963f7d28e17f72")
        self.assertEqual(hash_bytes(b"", "sha1"), "da39a3ee5e6b4b0d3255bfef95601890afd80709")

    def test_hash_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "a.txt"
            f.write_bytes(b"abc")
            self.assertEqual(hash_file(f, ("sha256",))["sha256"], hash_bytes(b"abc", "sha256"))


class TestGitStats(unittest.TestCase):
    def test_parse_shortlog(self):
        sample = "   42\tAda Lovelace <ada@x.dev>\n    7\tGrace Hopper <grace@x.dev>\n"
        self.assertEqual(parse_shortlog(sample),
                         [(42, "Ada Lovelace <ada@x.dev>"), (7, "Grace Hopper <grace@x.dev>")])
        self.assertEqual(parse_shortlog(""), [])

    def test_punchcard(self):
        grid = punchcard_grid(["1:09", "1:09", "6:23", "oops", "9:99"])
        self.assertEqual(grid[1][9], 2)
        self.assertEqual(grid[6][23], 1)
        art = render_punchcard(grid)
        self.assertIn("Mon", art)
        self.assertIn("\u2588", art)

    def test_weeks(self):
        now = 1_000_000_000
        buckets = week_buckets([now - 86400, now - 8 * 86400, now - 400 * 86400], now, 12)
        self.assertEqual(sum(buckets), 2)
        self.assertEqual(buckets[-1], 1)

    def test_repo_integration(self):
        if shutil.which("git") is None:
            self.skipTest("no git binary")
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            subprocess.run(["git", "init", "-q"], cwd=tmp, env=env, check=True,
                           capture_output=True)
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=T",
                            "commit", "--allow-empty", "-qm", "one"],
                           cwd=tmp, env=env, check=True, capture_output=True)
            r = subprocess.run(["git", "shortlog", "-sne", "--all"], cwd=tmp, env=env,
                               capture_output=True, text=True)
            authors = parse_shortlog(r.stdout)
            self.assertEqual(len(authors), 1)
            self.assertEqual(authors[0][0], 1)


class TestHttp(unittest.TestCase):
    @staticmethod
    def _server():
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/missing":
                    self.send_response(404)
                    self.end_headers()
                    return
                body = b'{"ok": true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        srv = HTTPServer(("127.0.0.1", 0), H)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        return srv, t

    def test_fetch_ok(self):
        srv, t = self._server()
        try:
            d = fetch_url(f"http://127.0.0.1:{srv.server_address[1]}/x", max_bytes=100)
            self.assertTrue(d["ok"])
            self.assertEqual(d["status"], 200)
            self.assertEqual(d["body"], b'{"ok": true}')
            self.assertIn("application/json", header_get(d["headers"], "content-type"))
        finally:
            srv.shutdown()
            t.join()

    def test_404_and_unreachable(self):
        srv, t = self._server()
        try:
            d = fetch_url(f"http://127.0.0.1:{srv.server_address[1]}/missing")
            self.assertFalse(d["ok"])
            self.assertEqual(d["status"], 404)
        finally:
            srv.shutdown()
            t.join()
        d = fetch_url("http://127.0.0.1:1/", timeout=2)
        self.assertFalse(d["ok"])
        self.assertEqual(d["status"], 0)


class TestVibeFix(unittest.TestCase):
    def test_fix_creates_files_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# keep me\n", encoding="utf-8")
            created = vibe_fix(root, assume_yes=True)
            self.assertEqual(set(created), {"MIT LICENSE", ".gitignore (python+node)",
                                            "tests/test_smoke.py sample"})
            self.assertTrue((root / ".gitignore").exists())
            self.assertTrue((root / "LICENSE").exists())
            self.assertTrue((root / "tests" / "test_smoke.py").exists())
            self.assertEqual((root / "README.md").read_text(encoding="utf-8"), "# keep me\n")
            score, _ = vibe_checks(root)
            self.assertGreaterEqual(score, 40)

    def test_fix_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vibe_fix(root, assume_yes=True)
            self.assertEqual(vibe_fix(root, assume_yes=True), [])


class TestRainbow(unittest.TestCase):
    def test_rainbow_shape(self):
        out = render_rainbow("HI")
        self.assertIn("\033[", out)
        self.assertEqual(strip_ansi(out), render_banner("HI"))

    def test_no_color_respected(self):
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            self.assertNotIn("\033[", render_rainbow("HI"))


if __name__ == "__main__":
    unittest.main()
