#!/usr/bin/env python3
"""VibeCode - zero-dependency developer toolkit.

A single-file CLI with genuinely useful commands:
  analyze     scan a project: languages, lines, sizes, ASCII charts
  vibe-check  score a repo's health (0-100) with verdicts
  banner      render big ASCII banners (built-in pixel font)
  stats       show system info (CPU, RAM, disk, python...)
  json        validate / pretty-print / minify JSON
  b64         base64 encode / decode (unicode-safe)
  passgen     generate secure passwords + entropy estimate
  pomodoro    terminal focus timer with progress bar
  dashboard   live terminal dashboard: clock, system, git, project
  serve       serve the VibeCode web playground locally

Stdlib only. No pip install needed. Just run it.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import datetime
import json
import math
import os
import platform
import re
import secrets
import shutil
import string
import subprocess
import sys
import time
import webbrowser
from collections import Counter
from pathlib import Path

__version__ = "1.0.0"


# ---------------------------------------------------------------- colors

class C:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return sys.stdout.isatty()


def paint(text: str, code: str) -> str:
    if not _supports_color():
        return text
    return f"{code}{text}{C.END}"


def ok(text: str) -> str:
    return paint(text, C.GREEN)


def warn(text: str) -> str:
    return paint(text, C.YELLOW)


def err(text: str) -> str:
    return paint(text, C.RED)


def head(text: str) -> str:
    return paint(text, C.CYAN + C.BOLD)


def dim(text: str) -> str:
    return paint(text, C.DIM)


# ------------------------------------------------------------- helpers

def human_size(n: int) -> str:
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def bar(frac: float, width: int = 24, ascii_only: bool = False) -> str:
    frac = max(0.0, min(1.0, frac))
    filled = int(round(frac * width))
    if ascii_only:
        return "#" * filled + "-" * (width - filled)
    return "\u2588" * filled + "\u2591" * (width - filled)


def progress_bar(frac: float, width: int = 30) -> str:
    return bar(frac, width)


def format_time(total_seconds: float) -> str:
    total_seconds = max(0, int(total_seconds))
    m, s = divmod(total_seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def clear_screen() -> None:
    if os.name == "nt":
        os.system("cls")
    else:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


def is_binary_sample(chunk: bytes) -> bool:
    return b"\x00" in chunk


def count_lines(text: str) -> int:
    if not text:
        return 0
    n = text.count("\n")
    if not text.endswith("\n"):
        n += 1
    return n


# ------------------------------------------------------------- analyze

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".tox",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build",
    ".next", ".nuxt", "target", "out", "coverage", ".idea", ".vscode",
    "vendor", "Pods", ".turbo", ".parcel-cache", ".svelte-kit",
}

EXT_LANG = {
    ".py": "Python", ".pyi": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript",
    ".html": "HTML", ".htm": "HTML",
    ".css": "CSS", ".scss": "SCSS", ".sass": "Sass", ".less": "Less",
    ".json": "JSON", ".jsonc": "JSON",
    ".md": "Markdown", ".mdx": "Markdown", ".rst": "Docs", ".txt": "Text",
    ".yml": "YAML", ".yaml": "YAML", ".toml": "TOML",
    ".ini": "INI", ".cfg": "Config", ".conf": "Config", ".env": "Config",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala",
    ".c": "C", ".h": "C/C++ Header", ".cpp": "C++", ".hpp": "C++",
    ".cc": "C++", ".cxx": "C++", ".cs": "C#", ".go": "Go", ".rs": "Rust",
    ".rb": "Ruby", ".php": "PHP", ".swift": "Swift", ".m": "Obj-C",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".fish": "Shell",
    ".ps1": "PowerShell", ".bat": "Batch", ".cmd": "Batch",
    ".sql": "SQL", ".xml": "XML", ".svg": "SVG", ".vue": "Vue",
    ".svelte": "Svelte", ".r": "R", ".jl": "Julia", ".pl": "Perl",
    ".lua": "Lua", ".dart": "Dart", ".hs": "Haskell", ".ex": "Elixir",
    ".exs": "Elixir", ".erl": "Erlang", ".clj": "Clojure", ".elm": "Elm",
    ".dockerfile": "Docker", ".containerfile": "Docker",
    ".makefile": "Make", ".mk": "Make", ".cmake": "CMake",
    ".gradle": "Gradle", ".groovy": "Groovy",
    ".csv": "CSV", ".tsv": "CSV", ".graphql": "GraphQL", ".gql": "GraphQL",
    ".proto": "Protobuf", ".thrift": "Thrift", ".sol": "Solidity",
    ".tf": "Terraform", ".tfvars": "Terraform", ".nix": "Nix",
    ".vim": "Vim", ".el": "Emacs Lisp",
}

CODE_EXTS = {
    ".py", ".js", ".jsx", ".mjs", ".ts", ".tsx", ".java", ".kt", ".kts",
    ".c", ".h", ".cpp", ".hpp", ".cc", ".cs", ".go", ".rs", ".rb", ".php",
    ".swift", ".scala", ".sh", ".bash", ".zsh", ".sql", ".vue", ".svelte",
    ".r", ".lua", ".dart", ".hs", ".ex", ".exs", ".erl", ".clj", ".pl",
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
}


def language_for_ext(ext: str) -> str:
    return EXT_LANG.get(ext.lower(), "Other")


def analyze_path(root: Path) -> dict:
    """Walk *root* and collect per-language stats. Pure-ish: returns a dict."""
    root = root.resolve()
    lang_files: Counter = Counter()
    lang_lines: Counter = Counter()
    total_files = 0
    total_lines = 0
    total_bytes = 0
    binary_skipped = 0
    largest: list[tuple[int, int, str]] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name == ".DS_Store":
                continue
            fpath = Path(dirpath) / name
            try:
                size = fpath.stat().st_size
            except OSError:
                continue
            try:
                with open(fpath, "rb") as fh:
                    sample = fh.read(2048)
            except OSError:
                continue
            if is_binary_sample(sample):
                binary_skipped += 1
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lines = count_lines(text)
            ext = fpath.suffix
            # special filenames without extensions
            if name.lower() in ("dockerfile", "makefile"):
                ext = "." + name.lower()
            lang = language_for_ext(ext)
            lang_files[lang] += 1
            lang_lines[lang] += lines
            total_files += 1
            total_lines += lines
            total_bytes += size
            try:
                rel = str(fpath.relative_to(root))
            except ValueError:
                rel = str(fpath)
            largest.append((size, lines, rel))

    largest.sort(reverse=True)
    langs = {
        lang: {"files": lang_files[lang], "lines": lang_lines[lang]}
        for lang in sorted(lang_files, key=lambda l: lang_lines[l], reverse=True)
    }
    return {
        "root": str(root),
        "files": total_files,
        "lines": total_lines,
        "bytes": total_bytes,
        "binary_skipped": binary_skipped,
        "langs": langs,
        "largest": [
            {"path": rel, "bytes": size, "lines": lines}
            for size, lines, rel in largest
        ],
    }


def print_analysis(data: dict, ascii_only: bool = False, top: int = 8) -> None:
    print(head(f"\n  \U0001f4ca  VibeCode analyze  \u2014  {data['root']}\n"))
    print(f"   Files:  {paint(str(data['files']), C.BOLD)}   "
          f"Lines:  {paint(str(data['lines']), C.BOLD)}   "
          f"Size:  {paint(human_size(data['bytes']), C.BOLD)}")
    if data["binary_skipped"]:
        print(dim(f"   (skipped {data['binary_skipped']} binary file(s))"))
    print()
    if not data["langs"]:
        print(warn("   No text files found. Empty vibes."))
        return
    max_lines = max(v["lines"] for v in data["langs"].values()) or 1
    print(head("   Languages"))
    for lang, v in data["langs"].items():
        pct = v["lines"] / max_lines
        print(f"   {lang:<14} {v['files']:>4} files  {v['lines']:>7,} lines  "
              f"{paint(bar(pct, 22, ascii_only), C.MAGENTA)}")
    print()
    print(head(f"   Largest files (top {top})"))
    for item in data["largest"][:top]:
        print(f"   {human_size(item['bytes']):>9}  {item['lines']:>7,} lines  {dim(item['path'])}")
    # fun footer
    lines = data["lines"]
    if lines > 100_000:
        verdict = "absolute unit of a codebase \U0001f99a"
    elif lines > 20_000:
        verdict = "a serious project \U0001f525"
    elif lines > 3_000:
        verdict = "a healthy side project \U0001f331"
    elif lines > 300:
        verdict = "a cute little project \U0001f49a"
    elif lines > 0:
        verdict = "just getting started \u2728"
    else:
        verdict = "emptiness... full of potential \U0001f573\ufe0f"
    print(f"\n   Verdict: {verdict}\n")


def cmd_analyze(args: argparse.Namespace) -> int:
    root = Path(args.path)
    if not root.exists():
        print(err(f"✖ Path does not exist: {root}"), file=sys.stderr)
        return 2
    data = analyze_path(root)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print_analysis(data, ascii_only=args.ascii, top=args.top)
    return 0


# ---------------------------------------------------------- vibe-check

def _git(root: Path, *git_args: str) -> str | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), *git_args],
            capture_output=True, text=True, timeout=8,
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def _has_recent_commit(root: Path, days: int = 30) -> bool:
    out = _git(root, "log", "-1", "--format=%ct")
    if not out:
        return False
    try:
        ts = int(out.strip().split()[0])
    except (ValueError, IndexError):
        return False
    age_days = (time.time() - ts) / 86400
    return age_days <= days


def _count_code_files(root: Path, limit: int = 64) -> int:
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if Path(name).suffix.lower() in CODE_EXTS:
                n += 1
                if n >= limit:
                    return n
    return n


def _has_tests(root: Path) -> bool:
    if (root / "tests").is_dir() or (root / "test").is_dir():
        return True
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            low = name.lower()
            if (low.startswith("test_") or low.endswith("_test.py")
                    or low.endswith(".test.js") or low.endswith(".test.ts")
                    or low.endswith(".spec.js") or low.endswith(".spec.ts")
                    or low.endswith("_test.go") or low.endswith("test.java")):
                return True
    return False


def vibe_checks(root: Path) -> tuple[int, list[dict]]:
    """Return (score 0-100, list of check dicts)."""
    root = root.resolve()
    is_repo = (root / ".git").exists() or _git(root, "rev-parse", "--git-dir") is not None

    def exists(*names: str) -> bool:
        return any((root / n).exists() for n in names)

    def glob_exists(pattern: str) -> bool:
        return any(root.glob(pattern))

    status = _git(root, "status", "--porcelain") if is_repo else None

    checks = [
        {"key": "readme", "label": "README file",
         "passed": glob_exists("README*"),
         "points": 15, "hint": "Add a README.md so humans know what this is",
         "roast": "no README? bold of you to assume anyone will guess"},
        {"key": "license", "label": "License",
         "passed": glob_exists("LICEN[CS]E*") or exists("COPYING"),
         "points": 10, "hint": "Add an MIT/Apache license file",
         "roast": "no license = nobody can legally use this. oops"},
        {"key": "gitignore", "label": ".gitignore",
         "passed": exists(".gitignore"),
         "points": 10, "hint": "Add a .gitignore before node_modules ends up on GitHub",
         "roast": "living dangerously without a .gitignore, I see"},
        {"key": "tests", "label": "Tests",
         "passed": _has_tests(root),
         "points": 15, "hint": "Add a tests/ folder with at least one test",
         "roast": "'it works on my machine' is not a testing strategy"},
        {"key": "ci", "label": "CI workflow",
         "passed": (root / ".github" / "workflows").is_dir(),
         "points": 10, "hint": "Add .github/workflows/ci.yml",
         "roast": "no CI? merging straight to main like it's 2009"},
        {"key": "fresh", "label": "Recent commit (<30d)",
         "passed": _has_recent_commit(root) if is_repo else False,
         "points": 10, "hint": "Commit something — show signs of life",
         "roast": "last commit was basically in the mesozoic era"},
        {"key": "code", "label": "Real code (>3 files)",
         "passed": _count_code_files(root) > 3,
         "points": 10, "hint": "Write some code — every legend starts somewhere",
         "roast": "this repo is 90% vibes, 10% code"},
        {"key": "docs", "label": "Docs / contributing",
         "passed": (root / "docs").is_dir() or exists("CONTRIBUTING.md", "CONTRIBUTING", "CHANGELOG.md"),
         "points": 5, "hint": "Add docs/ or CONTRIBUTING.md",
         "roast": "docs? never heard of her"},
        {"key": "manifest", "label": "Project manifest",
         "passed": exists("pyproject.toml", "setup.py", "setup.cfg", "package.json",
                           "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "composer.json"),
         "points": 5, "hint": "Add pyproject.toml / package.json / Cargo.toml...",
         "roast": "no manifest — is this a project or a folder of secrets?"},
        {"key": "clean", "label": "Clean git tree",
         "passed": (status == "") if is_repo else False,
         "points": 10, "hint": "Commit or stash your changes" if is_repo else "Run: git init",
         "roast": "uncommitted changes everywhere. chaos goblin energy"},
    ]
    score = sum(c["points"] for c in checks if c["passed"])
    return min(100, score), checks


def tier_for_score(score: int) -> tuple[str, str]:
    if score >= 90:
        return "LEGENDARY", "\U0001f3c6 This repo belongs in a museum. Flawless."
    if score >= 75:
        return "FIRE", "\U0001f525 Certified fresh. Ship it with confidence."
    if score >= 60:
        return "SOLID", "\U0001f44d Respectable. A little polish and it's elite."
    if score >= 40:
        return "MEH", "\U0001f60f It exists. That's... a start."
    if score >= 20:
        return "SUS", "\U0001f9f9 This repo is held together by hope."
    return "ZOMBIE", "\U0001f9df Is this repo alive? Blink twice if yes."


def print_vibe_check(root: Path, score: int, checks: list[dict], roast: bool = False) -> None:
    print(head(f"\n  \U0001f52e  Vibe-check  \u2014  {root}\n"))
    for c in checks:
        mark = ok("\u2714") if c["passed"] else err("\u2718")
        pts = f"+{c['points']}" if c["passed"] else f" +0/{c['points']}"
        print(f"   {mark}  {c['label']:<22} {dim(pts)}")
        if not c["passed"]:
            print(dim(f"       \u2514\u2500 {(c['roast'] if roast else c['hint'])}"))
    tier, msg = tier_for_score(score)
    color = C.GREEN if score >= 75 else (C.YELLOW if score >= 40 else C.RED)
    print(f"\n   Score: {paint(f'{score}/100', color + C.BOLD)}  {paint('[' + bar(score / 100, 20) + ']', color)}")
    print(f"   Tier:  {paint(tier, color + C.BOLD)}  {msg}\n")


def cmd_vibe_check(args: argparse.Namespace) -> int:
    root = Path(args.path)
    if not root.exists():
        print(err(f"✖ Path does not exist: {root}"), file=sys.stderr)
        return 2
    score, checks = vibe_checks(root)
    if args.json:
        print(json.dumps({"root": str(root.resolve()), "score": score,
                          "tier": tier_for_score(score)[0],
                          "checks": [{k: c[k] for k in ("key", "label", "passed", "points")} for c in checks]},
                         indent=2))
    else:
        print_vibe_check(root.resolve(), score, checks, roast=args.roast)
    return 0


# -------------------------------------------------------------- banner

FONT: dict[str, list[str]] = {
    "A": [" ### ", "#   #", "#####", "#   #", "#   #"],
    "B": ["#### ", "#   #", "#### ", "#   #", "#### "],
    "C": [" ####", "#    ", "#    ", "#    ", " ####"],
    "D": ["#### ", "#   #", "#   #", "#   #", "#### "],
    "E": ["#####", "#    ", "#### ", "#    ", "#####"],
    "F": ["#####", "#    ", "#### ", "#    ", "#    "],
    "G": [" ####", "#    ", "#  ##", "#   #", " ####"],
    "H": ["#   #", "#   #", "#####", "#   #", "#   #"],
    "I": ["#####", "  #  ", "  #  ", "  #  ", "#####"],
    "J": ["  ###", "   # ", "   # ", "#  # ", " ##  "],
    "K": ["#   #", "#  # ", "###  ", "#  # ", "#   #"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "#   #", "#   #"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", " ### "],
    "P": ["#### ", "#   #", "#### ", "#    ", "#    "],
    "Q": [" ### ", "#   #", "#   #", "#  ##", " ## #"],
    "R": ["#### ", "#   #", "#### ", "#  # ", "#   #"],
    "S": [" ####", "#    ", " ### ", "    #", "#### "],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#   #", "#   #", "#   #", "#   #", " ### "],
    "V": ["#   #", "#   #", "#   #", " # # ", "  #  "],
    "W": ["#   #", "#   #", "# # #", "## ##", "#   #"],
    "X": ["#   #", "#   #", "  #  ", "#   #", "#   #"],
    "Y": ["#   #", "#   #", "  #  ", "  #  ", "  #  "],
    "Z": ["#####", "   # ", "  #  ", " #   ", "#####"],
    "0": [" ### ", "#  ##", "# # #", "##  #", " ### "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", " ### "],
    "2": [" ### ", "#   #", "   # ", "  #  ", "#####"],
    "3": ["#### ", "    #", " ### ", "    #", "#### "],
    "4": ["   # ", "  ## ", " # # ", "#####", "   # "],
    "5": ["#####", "#    ", "#### ", "    #", "#### "],
    "6": [" ####", "#    ", "#### ", "#   #", " ### "],
    "7": ["#####", "   # ", "  #  ", " #   ", "#    "],
    "8": [" ### ", "#   #", " ### ", "#   #", " ### "],
    "9": [" ### ", "#   #", " ####", "    #", "#### "],
    " ": ["     ", "     ", "     ", "     ", "     "],
    "-": ["     ", "     ", "#####", "     ", "     "],
    "_": ["     ", "     ", "     ", "     ", "#####"],
    "!": ["  #  ", "  #  ", "  #  ", "     ", "  #  "],
    "?": [" ### ", "#   #", "  ## ", "     ", "  #  "],
    ".": ["     ", "     ", "     ", "     ", "  #  "],
    ":": ["     ", "  #  ", "     ", "  #  ", "     "],
    "/": ["    #", "    #", "  #  ", " #   ", " #   "],
    "+": ["     ", "  #  ", "#####", "  #  ", "     "],
    "*": ["     ", "# # #", "  #  ", "# # #", "     "],
    "#": [" # # ", "#####", " # # ", "#####", " # # "],
}


def render_banner(text: str, fill: str = "#", sep: str = "  ") -> str:
    """Render *text* with the built-in 5x5 pixel font."""
    fill = (fill or "#")[0]
    rows = [""] * 5
    for ch in text.upper():
        glyph = FONT.get(ch, FONT["?"])
        for i in range(5):
            rows[i] += glyph[i].replace("#", fill) + sep
    return "\n".join(r.rstrip() for r in rows)


def cmd_banner(args: argparse.Namespace) -> int:
    print(paint(render_banner(args.text, fill=args.char), C.MAGENTA + C.BOLD))
    return 0


# --------------------------------------------------------------- stats

def build_stats() -> dict:
    info: dict = {}
    info["os"] = f"{platform.system()} {platform.release()} ({platform.machine()})"
    info["python"] = platform.python_version()
    info["cpu_count"] = os.cpu_count() or 1
    try:
        load = os.getloadavg()  # type: ignore[attr-defined]
        info["load"] = f"{load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}"
    except (AttributeError, OSError):
        info["load"] = "n/a"
    info["memory"] = "n/a"
    try:
        meminfo = Path("/proc/meminfo").read_text().splitlines()
        vals = {}
        for line in meminfo:
            k, _, v = line.partition(":")
            vals[k.strip()] = v.strip().split()[0] if v.strip() else "0"
        total = int(vals.get("MemTotal", 0)) // 1024
        avail = int(vals.get("MemAvailable", 0)) // 1024
        if total:
            info["memory"] = f"{total - avail} / {total} MB used"
    except Exception:
        pass
    try:
        du = shutil.disk_usage(os.getcwd())
        info["disk"] = f"{human_size(du.used)} / {human_size(du.total)} used"
        info["disk_frac"] = du.used / du.total if du.total else 0
    except OSError:
        info["disk"] = "n/a"
        info["disk_frac"] = 0
    try:
        ts = shutil.get_terminal_size()
        info["terminal"] = f"{ts.columns}x{ts.lines}"
    except OSError:
        info["terminal"] = "n/a"
    info["time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return info


def print_stats(info: dict) -> None:
    print(head("\n  \U0001f5a5\ufe0f  System stats\n"))
    rows = [
        ("OS", info["os"]),
        ("Python", info["python"]),
        ("CPUs", str(info["cpu_count"])),
        ("Load avg", info["load"]),
        ("Memory", info["memory"]),
        ("Terminal", info["terminal"]),
        ("Time", info["time"]),
    ]
    for k, v in rows:
        print(f"   {k:<9} {paint(v, C.BOLD)}")
    print(f"   {'Disk':<9} {paint(info['disk'], C.BOLD)}  {paint(bar(info['disk_frac'], 18), C.CYAN)}")
    print()


def cmd_stats(_args: argparse.Namespace) -> int:
    print_stats(build_stats())
    return 0


# ---------------------------------------------------------------- json

def parse_json(raw: str):
    return json.loads(raw)


def dump_json(obj, indent: int = 2, sort_keys: bool = False, minify: bool = False) -> str:
    if minify:
        return json.dumps(obj, sort_keys=sort_keys, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=False)


def cmd_json(args: argparse.Namespace) -> int:
    try:
        raw = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    except OSError as e:
        print(err(f"✖ Cannot read input: {e}"), file=sys.stderr)
        return 2
    try:
        obj = parse_json(raw)
    except json.JSONDecodeError as e:
        print(err(f"✖ Invalid JSON: {e}"), file=sys.stderr)
        return 2
    if args.validate:
        print(ok("✔ Valid JSON"))
        return 0
    out = dump_json(obj, indent=args.indent, sort_keys=args.sort_keys, minify=args.minify)
    if args.out:
        try:
            Path(args.out).write_text(out + "\n", encoding="utf-8")
        except OSError as e:
            print(err(f"✖ Cannot write output: {e}"), file=sys.stderr)
            return 2
        print(ok(f"✔ Wrote {args.out}"))
    else:
        print(out)
    return 0


# ----------------------------------------------------------------- b64

def b64encode_text(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


def b64decode_text(s: str) -> str:
    return base64.b64decode(s.strip(), validate=True).decode("utf-8")


def cmd_b64(args: argparse.Namespace) -> int:
    try:
        if args.text is not None:
            raw = args.text
        elif args.file:
            raw = Path(args.file).read_text(encoding="utf-8")
        else:
            raw = sys.stdin.read()
    except OSError as e:
        print(err(f"✖ Cannot read input: {e}"), file=sys.stderr)
        return 2
    try:
        if args.action == "encode":
            print(b64encode_text(raw))
        else:
            print(b64decode_text(raw))
    except (binascii.Error, UnicodeDecodeError, ValueError) as e:
        print(err(f"✖ Cannot decode: {e}"), file=sys.stderr)
        return 2
    return 0


# ------------------------------------------------------------- passgen

AMBIGUOUS = set("Il1O0|`'\"")


def password_pool(use_symbols: bool = True) -> str:
    pool = string.ascii_letters + string.digits
    if use_symbols:
        pool += string.punctuation
    return "".join(ch for ch in pool if ch not in AMBIGUOUS)


def generate_password(length: int = 20, use_symbols: bool = True) -> str:
    pool = password_pool(use_symbols)
    return "".join(secrets.choice(pool) for _ in range(length))


def password_entropy(length: int, pool_size: int) -> float:
    if length <= 0 or pool_size <= 1:
        return 0.0
    return length * math.log2(pool_size)


def strength_label(bits: float) -> str:
    if bits < 50:
        return "weak \U0001f62c"
    if bits < 80:
        return "decent \U0001f610"
    if bits < 110:
        return "strong \U0001f60e"
    return "godlike \U0001f525"


def cmd_passgen(args: argparse.Namespace) -> int:
    length = max(4, args.length)
    pool = password_pool(use_symbols=not args.no_symbols)
    bits = password_entropy(length, len(pool))
    for _ in range(max(1, args.count)):
        print(paint(generate_password(length, not args.no_symbols), C.BOLD))
    print(dim(f"  ~{bits:.0f} bits of entropy \u2014 {strength_label(bits)}"))
    return 0


# ------------------------------------------------------------ pomodoro

def run_phase(label: str, seconds: int) -> None:
    end = time.time() + seconds
    while True:
        remaining = end - time.time()
        if remaining <= 0:
            break
        frac = 1 - remaining / seconds if seconds else 1
        sys.stdout.write(f"\r   {label} {paint(progress_bar(frac), C.GREEN)} {format_time(remaining)}  ")
        sys.stdout.flush()
        time.sleep(min(1.0, remaining))
    sys.stdout.write(f"\r   {label} {paint(progress_bar(1.0), C.GREEN)} {format_time(0)}  \n")
    sys.stdout.flush()


def bell(n: int = 3) -> None:
    sys.stdout.write("\a" * n)
    sys.stdout.flush()


def cmd_pomodoro(args: argparse.Namespace) -> int:
    focus = max(1, args.focus * 60)
    rest = max(1, args.rest * 60)
    cycles = max(1, args.cycles)
    print(head(f"\n  \U0001f345  Pomodoro \u2014 {args.focus}m focus / {args.rest}m rest x{cycles}\n"))
    done = 0
    try:
        for i in range(1, cycles + 1):
            print(f"   {paint(f'Focus {i}/{cycles}', C.BOLD)} \u2014 stay in the zone...")
            run_phase("FOCUS", focus)
            bell()
            done += 1
            print(ok("   \u2714 Focus complete! Touch grass briefly."))
            if i < cycles:
                print(f"   {paint('Break', C.BOLD)} \u2014 breathe, stretch, hydrate...")
                run_phase("BREAK", rest)
                bell(2)
                print(ok("   \u2714 Break over. Back to glory.\n"))
    except KeyboardInterrupt:
        print(warn(f"\n\n   Stopped. Completed {done} focus session(s). Respect."))
        return 0
    print(head(f"\n  \U0001f3c6 All {cycles} cycles done. You absolute machine.\n"))
    return 0


# ----------------------------------------------------------- dashboard

QUOTES = [
    "\u201cFirst, solve the problem. Then, write the code.\u201d \u2014 J. Johnson",
    "\u201cCode is like humor: explain it and it's bad.\u201d \u2014 C. House",
    "\u201cSimplicity is the soul of efficiency.\u201d \u2014 A. Freeman",
    "\u201cMake it work, make it right, make it fast.\u201d \u2014 K. Beck",
    "\u201cThe best code is no code at all.\u201d \u2014 J. Atwood",
    "\u201cTalk is cheap. Show me the code.\u201d \u2014 L. Torvalds",
    "\u201cShip early, ship often, touch grass.\u201d \u2014 VibeCode",
    "\u201cDone is better than perfect.\u201d \u2014 S. Sandberg",
]


def dashboard_data(root: Path) -> dict:
    now = datetime.datetime.now()
    stats = build_stats()
    branch = _git(root, "branch", "--show-current")
    status = _git(root, "status", "--porcelain")
    last = _git(root, "log", "-1", "--format=%h %s")
    try:
        proj = analyze_path(root)
        top_langs = list(proj["langs"].items())[:2]
    except Exception:
        proj = {"files": 0, "lines": 0}
        top_langs = []
    return {
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%A, %d %B %Y"),
        "quote": QUOTES[now.minute % len(QUOTES)],
        "cpu": stats["cpu_count"],
        "load": stats["load"],
        "memory": stats["memory"],
        "disk": stats["disk"],
        "disk_frac": stats["disk_frac"],
        "branch": branch or "n/a",
        "dirty": (len(status.splitlines()) if status else 0) if branch else 0,
        "last_commit": last or "n/a",
        "files": proj["files"],
        "lines": proj["lines"],
        "top_langs": [(lang, v["lines"]) for lang, v in top_langs],
    }


def render_dashboard(d: dict, root: Path) -> str:
    W = 62
    top = paint("\u256d" + "\u2500" * (W - 2) + "\u256e", C.CYAN)

    def row(text: str = "") -> str:
        # strip ANSI for width calc
        plain = re.sub(r"\033\[[0-9;]+m", "", text)
        pad = max(0, W - 4 - len(plain))
        return paint("\u2502 ", C.CYAN) + text + " " * pad + paint(" \u2502", C.CYAN)

    bottom = paint("\u2570" + "\u2500" * (W - 2) + "\u256f", C.CYAN)
    sep = paint("\u2502 " + "\u2500" * (W - 4) + " \u2502", C.CYAN)
    last_commit = d["last_commit"]
    last_short = last_commit[: W - 11] + "…" if len(last_commit) > W - 10 else last_commit
    lines = [
        top,
        row(paint(f"✨ VibeCode Dashboard — {d['date']}", C.BOLD)),
        row(paint(f"🕐 {d['time']}", C.BOLD + C.GREEN)),
        sep,
        row(head("SYSTEM") + f"   CPUs: {d['cpu']}   Load: {d['load']}"),
        row(f"  Memory: {d['memory']}"),
        row(f"  Disk:   {d['disk']} {paint(bar(d['disk_frac'], 12), C.CYAN)}"),
        sep,
        row(head("GIT") + f"      branch: {paint(d['branch'], C.BOLD)}"
            + (f"  •  {d['dirty']} uncommitted" if d["dirty"] else "  •  clean ✔")),
        row(f"  Last: {last_short}"),
    sep,
    row(head("PROJECT") + f"  {root}"),
    row(f"  {d['files']} files \u2022 {d['lines']:,} lines"
        + (f"  \u2022  top: {', '.join(lang for lang, _ in d['top_langs'])}" if d["top_langs"] else "")),
    sep,
    row(dim(d["quote"])),
    row(dim("Press Ctrl+C to exit")),
    bottom,
]
    # truncate rows that overflow (visual safety)
    safe = []
    for ln in lines:
        plain = re.sub(r"\033\[[0-9;]+m", "", ln)
        if len(plain) > W:
            # crude cut, may cut inside ANSI: rebuild without color for safety
            ln = plain[: W - 1] + "\u2026"
        safe.append(ln)
    return "\n".join(safe)


def cmd_dashboard(args: argparse.Namespace) -> int:
    root = Path(args.path)
    if args.once:
        print(render_dashboard(dashboard_data(root), root.resolve()))
        return 0
    print(dim("Starting live dashboard... Ctrl+C to exit.\n"))
    try:
        while True:
            clear_screen()
            print(render_dashboard(dashboard_data(root), root.resolve()))
            time.sleep(max(1, args.interval))
    except KeyboardInterrupt:
        print(warn("\n\nDashboard closed. Stay vibing. \U0001f44b"))
    return 0


# --------------------------------------------------------------- serve

def cmd_serve(args: argparse.Namespace) -> int:
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    root = Path(args.dir).resolve()
    index = root / "index.html"
    if not index.exists():
        print(err(f"✖ No index.html in {root}"), file=sys.stderr)
        return 2
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    ThreadingHTTPServer.allow_reuse_address = True
    try:
        srv = ThreadingHTTPServer((args.host, args.port), handler)
    except OSError as e:
        print(err(f"✖ Cannot bind {args.host}:{args.port}: {e}"), file=sys.stderr)
        return 2
    port = srv.server_address[1]
    url = f"http://{'localhost' if args.host in ('127.0.0.1', '0.0.0.0') else args.host}:{port}/"
    print(head("\n  \U0001f680  VibeCode playground"))
    print(f"   Serving {paint(str(root), C.BOLD)}")
    print(f"   Open    {paint(url, C.GREEN + C.BOLD)}\n")
    if not args.no_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print(warn("\n   Server stopped. Bye! \U0001f44b"))
    return 0


# ----------------------------------------------------------------- cli

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vibecode",
        description="VibeCode v%s \u2014 zero-dependency developer toolkit (CLI + web playground)." % __version__,
        epilog="Examples:\n"
               "  vibecode analyze .            scan current project\n"
               "  vibecode vibe-check . --roast brutally honest repo review\n"
               "  vibecode banner 'SHIP IT'     big ASCII banner\n"
               "  vibecode serve                open the web playground\n"
               "  vibecode dashboard            live terminal dashboard\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    a = sub.add_parser("analyze", help="scan a project: languages, lines, sizes")
    a.add_argument("path", nargs="?", default=".", help="project directory (default: .)")
    a.add_argument("--json", action="store_true", help="machine-readable JSON output")
    a.add_argument("--ascii", action="store_true", help="ASCII-only bars (no unicode)")
    a.add_argument("--top", type=int, default=8, help="show N largest files (default: 8)")
    a.set_defaults(func=cmd_analyze)

    v = sub.add_parser("vibe-check", help="score a repo's health 0-100")
    v.add_argument("path", nargs="?", default=".", help="project directory (default: .)")
    v.add_argument("--roast", action="store_true", help="brutally honest hints")
    v.add_argument("--json", action="store_true", help="machine-readable JSON output")
    v.set_defaults(func=cmd_vibe_check)

    b = sub.add_parser("banner", help="render a big ASCII banner")
    b.add_argument("text", help="text to render (A-Z, 0-9, few symbols)")
    b.add_argument("--char", default="#", help="fill character (default: #)")
    b.set_defaults(func=cmd_banner)

    s = sub.add_parser("stats", help="show system info")
    s.set_defaults(func=cmd_stats)

    j = sub.add_parser("json", help="validate / pretty-print / minify JSON")
    j.add_argument("file", nargs="?", help="input file (default: stdin)")
    j.add_argument("--indent", type=int, default=2, help="indent width (default: 2)")
    j.add_argument("--sort-keys", action="store_true", help="sort object keys")
    j.add_argument("--minify", action="store_true", help="compact output, no whitespace")
    j.add_argument("--validate", action="store_true", help="only check validity")
    j.add_argument("--out", help="write result to file instead of stdout")
    j.set_defaults(func=cmd_json)

    e = sub.add_parser("b64", help="base64 encode / decode")
    e.add_argument("action", choices=["encode", "decode"], help="what to do")
    e.add_argument("text", nargs="?", help="input text (default: stdin)")
    e.add_argument("--file", help="read input from file")
    e.set_defaults(func=cmd_b64)

    g = sub.add_parser("passgen", help="generate secure passwords")
    g.add_argument("--length", type=int, default=20, help="password length (default: 20)")
    g.add_argument("--count", type=int, default=1, help="how many passwords (default: 1)")
    g.add_argument("--no-symbols", action="store_true", help="letters + digits only")
    g.set_defaults(func=cmd_passgen)

    m = sub.add_parser("pomodoro", help="terminal focus timer")
    m.add_argument("--focus", type=int, default=25, help="focus minutes (default: 25)")
    m.add_argument("--rest", type=int, default=5, help="break minutes (default: 5)")
    m.add_argument("--cycles", type=int, default=4, help="number of cycles (default: 4)")
    m.set_defaults(func=cmd_pomodoro)

    d = sub.add_parser("dashboard", help="live terminal dashboard")
    d.add_argument("path", nargs="?", default=".", help="project directory (default: .)")
    d.add_argument("--interval", type=int, default=2, help="refresh seconds (default: 2)")
    d.add_argument("--once", action="store_true", help="render once and exit")
    d.set_defaults(func=cmd_dashboard)

    w = sub.add_parser("serve", help="serve the web playground locally")
    w.add_argument("--dir", default=str(Path(__file__).resolve().parent),
                   help="directory with index.html (default: script dir)")
    w.add_argument("--host", default="127.0.0.1", help="bind host (default: 127.0.0.1)")
    w.add_argument("--port", type=int, default=8000, help="port (default: 8000, 0 = auto)")
    w.add_argument("--no-open", action="store_true", help="don't auto-open the browser")
    w.set_defaults(func=cmd_serve)

    return p


def print_splash() -> None:
    print(head(f"\n  \u2728 VibeCode v{__version__} \u2014 zero-dependency developer toolkit"))
    print(dim("     Run 'vibecode <command> --help' for details. Try: analyze, vibe-check, serve, dashboard\n"))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        print_splash()
        parser.print_help()
        return 0
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
