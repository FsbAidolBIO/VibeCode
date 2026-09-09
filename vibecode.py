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
  todo        tiny terminal TODO manager (add/list/done/rm)
  git-stats   authors leaderboard, punchcard heatmap, weekly bars
  lorem       generate placeholder text (words/sentences/paragraphs)
  uuid        generate UUIDs (v4/v1, upper, no-dashes)
  hash        md5/sha1/sha256/sha512 of text, file or stdin
  http        fetch a URL: status, timing, headers, body preview
  completions print shell completion script (bash/zsh/fish)

Stdlib only. No pip install needed. Just run it.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import datetime
import hashlib
import json
import math
import os
import platform
import random
import re
import secrets
import shutil
import string
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import webbrowser
from collections import Counter
from pathlib import Path

__version__ = "1.2.0"


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
    if getattr(args, "fix", False):
        vibe_fix(root, getattr(args, "yes", False))
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


def render_banner(text: str, fill: str = "#", sep: str | None = None, font: str = "block") -> str:
    """Render *text* with a built-in pixel font (block 5x5 or mini 5x3)."""
    fontdict, default_sep = FONTS.get(font, FONTS["block"])
    sep = default_sep if sep is None else sep
    fill = (fill or "#")[0]
    rows = [""] * 5
    for ch in text.upper():
        glyph = fontdict.get(ch, fontdict["?"])
        for i in range(5):
            rows[i] += glyph[i].replace("#", fill) + sep
    return "\n".join(r.rstrip() for r in rows)


def cmd_banner(args: argparse.Namespace) -> int:
    if getattr(args, "rainbow", False):
        print(render_rainbow(args.text, fill=args.char, font=getattr(args, "font", "block")))
    else:
        print(paint(render_banner(args.text, fill=args.char, font=getattr(args, "font", "block")), C.MAGENTA + C.BOLD))
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

# ------------------------------------------------------------- todo

TODO_FILENAME = "todo.json"


def todo_path() -> Path:
    base = os.environ.get("VIBECODE_HOME")
    root = Path(base) if base else Path.home() / ".vibecode"
    return root / TODO_FILENAME


def load_todo(path: Path | None = None) -> list[dict]:
    path = path or todo_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save_todo(items: list[dict], path: Path | None = None) -> Path:
    path = path or todo_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def todo_add(items: list[dict], text: str) -> dict:
    nid = max([i.get("id", 0) for i in items] + [0]) + 1
    entry = {"id": nid, "text": text, "done": False,
             "created": datetime.datetime.now().isoformat(timespec="seconds")}
    items.append(entry)
    return entry


def todo_set_done(items: list[dict], tid: int, done: bool) -> bool:
    for it in items:
        if it.get("id") == tid:
            it["done"] = bool(done)
            return True
    return False


def todo_remove(items: list[dict], tid: int) -> bool:
    for n, it in enumerate(items):
        if it.get("id") == tid:
            del items[n]
            return True
    return False


def todo_clear_done(items: list[dict]) -> int:
    before = len(items)
    items[:] = [i for i in items if not i.get("done")]
    return before - len(items)


def print_todo(items: list[dict], show_all: bool = False) -> None:
    visible = items if show_all else [i for i in items if not i.get("done")]
    if not visible:
        if not items:
            print(dim("  No tasks. Touch grass instead \U0001f331"))
        else:
            print(ok("  All done! Nothing pending \U0001f389"))
        return
    print(head("\n  \u2705  TODO\n"))
    for it in visible:
        mark = ok("\u2611") if it.get("done") else dim("\u2610")
        txt = it.get("text", "")
        if it.get("done"):
            txt = dim(txt + "  (done)")
        print(f"   {mark}  #{it.get('id'):>3}  {txt}")
    left = sum(1 for i in items if not i.get("done"))
    print(dim(f"\n   {left} pending \u2022 {len(items) - left} done \u2022 stored in {todo_path()}\n"))


def cmd_todo(args: argparse.Namespace) -> int:
    action = args.todo_cmd or "list"
    items = load_todo()
    if action == "add":
        text = " ".join(args.text).strip()
        if not text:
            print(err("\u2716 Task text is empty"), file=sys.stderr)
            return 2
        entry = todo_add(items, text)
        save_todo(items)
        print(ok(f"\u2714 Added #{entry['id']}: {text}"))
        return 0
    if action == "list":
        print_todo(items, show_all=getattr(args, "all", False))
        return 0
    if action in ("done", "undone"):
        if not todo_set_done(items, args.id, action == "done"):
            print(err(f"\u2716 No task #{args.id}"), file=sys.stderr)
            return 2
        save_todo(items)
        print(ok(f"\u2714 Task #{args.id} marked {'done' if action == 'done' else 'pending'}"))
        return 0
    if action == "rm":
        if not todo_remove(items, args.id):
            print(err(f"\u2716 No task #{args.id}"), file=sys.stderr)
            return 2
        save_todo(items)
        print(ok(f"\u2714 Removed task #{args.id}"))
        return 0
    if action == "clear":
        if getattr(args, "all", False):
            n = len(items)
            items.clear()
            save_todo(items)
            print(warn(f"  Cleared all {n} task(s). Fresh start \u2728"))
            return 0
        n = todo_clear_done(items)
        save_todo(items)
        print(ok(f"\u2714 Removed {n} completed task(s)"))
        return 0
    return 2


# ---------------------------------------------------------- git-stats

DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def parse_shortlog(text: str) -> list[tuple[int, str]]:
    authors = []
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\s+(.*\S)\s*$", line)
        if m:
            authors.append((int(m.group(1)), m.group(2)))
    return authors


def punchcard_grid(lines: list[str]) -> list[list[int]]:
    grid = [[0] * 24 for _ in range(7)]
    for ln in lines:
        try:
            d, h = ln.strip().split(":")
            d, h = int(d), int(h)
            if 0 <= d < 7 and 0 <= h < 24:
                grid[d][h] += 1
        except ValueError:
            continue
    return grid


def render_punchcard(grid: list[list[int]], ascii_only: bool = False) -> str:
    peak = max((v for row in grid for v in row), default=0)
    cells = (" ", ".", ":", "*", "#") if ascii_only else (" ", "\u2591", "\u2592", "\u2593", "\u2588")

    def cell(v: int) -> str:
        if peak <= 0 or v <= 0:
            return cells[0]
        return cells[min(4, max(1, round(v / peak * 4)))]

    rows = ["       " + "".join(str(h // 10) for h in range(24)),
            "       " + "".join(str(h % 10) for h in range(24))]
    for d, name in enumerate(DAY_NAMES):
        rows.append(f"   {name} " + "".join(cell(v) for v in grid[d]))
    return "\n".join(rows)


def week_buckets(timestamps: list[int], now: float, weeks: int = 12) -> list[int]:
    buckets = [0] * weeks
    for ts in timestamps:
        w = int((now - ts) // (7 * 86400))
        if 0 <= w < weeks:
            buckets[weeks - 1 - w] += 1
    return buckets


def render_weeks(buckets: list[int], ascii_only: bool = False) -> str:
    peak = max(buckets + [0])
    out = []
    for i, c in enumerate(buckets):
        label = "this week" if i == len(buckets) - 1 else f"-{len(buckets) - 1 - i}w"
        out.append(f"   {label:>9}  {bar(c / peak if peak else 0, 20, ascii_only)} {c}")
    return "\n".join(out)


def cmd_git_stats(args: argparse.Namespace) -> int:
    root = Path(args.path)
    if _git(root, "rev-parse", "--git-dir") is None:
        print(err(f"\u2716 Not a git repo: {root}"), file=sys.stderr)
        return 2
    print(head(f"\n  \U0001f4c8  Git stats  \u2014  {root.resolve()}\n"))
    total = (_git(root, "rev-list", "--count", "--all") or "0").strip()
    first = _git(root, "log", "--reverse", "--format=%ad", "--date=short", "-1") or "?"
    last = _git(root, "log", "-1", "--format=%ad", "--date=short") or "?"
    print(f"   Commits: {paint(total, C.BOLD)}   First: {first}   Last: {last}\n")
    authors = parse_shortlog(_git(root, "shortlog", "-sne", "--all") or "")
    if authors:
        print(head("   Top authors"))
        peak = authors[0][0] or 1
        for c, a in authors[: max(1, args.authors)]:
            print(f"   {c:>5}  {paint(bar(c / peak, 16, args.ascii), C.CYAN)}  {a}")
        print()
    pc = punchcard_grid((_git(root, "log", "--all", "--format=%ad", "--date=format:%w:%H") or "").splitlines())
    if any(any(r) for r in pc):
        print(head("   Punchcard (day \u00d7 hour)"))
        print(render_punchcard(pc, args.ascii))
        print()
    stamps = []
    for ln in (_git(root, "log", "--all", "--format=%ct") or "").splitlines():
        try:
            stamps.append(int(ln.strip()))
        except ValueError:
            pass
    if stamps:
        print(head("   Last 12 weeks"))
        print(render_weeks(week_buckets(stamps, time.time(), 12), args.ascii))
        print()
    return 0


# -------------------------------------------------------------- lorem

LOREM_WORDS = ("lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor "
               "incididunt ut labore et dolore magna aliqua enim ad minim veniam quis nostrud "
               "exercitation ullamco laboris nisi aliquip ex ea commodo consequat duis aute irure "
               "in reprehenderit voluptate velit esse cillum fugiat nulla pariatur excepteur sint "
               "occaecat cupidatat non proident sunt culpa qui officia deserunt mollit anim id est "
               "laborum perspiciatis unde omnis iste natus error accusantium doloremque laudantium "
               "totam rem aperiam eaque ab illo inventore veritatis quasi architecto beatae vitae "
               "dicta explicabo nemo ipsam quia voluptas aspernatur odit aut fugit consequuntur "
               "magni dolores eos ratione sequi nesciunt neque porro quisquam numquam eius modi "
               "tempora incidunt magnam quaerat").split()


def lorem_words(n: int, rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    return " ".join(rng.choice(LOREM_WORDS) for _ in range(max(0, n)))


def lorem_sentence(rng: random.Random, min_w: int = 6, max_w: int = 14) -> str:
    words = [rng.choice(LOREM_WORDS) for _ in range(rng.randint(min_w, max_w))]
    words[0] = words[0].capitalize()
    return " ".join(words) + "."


def lorem_sentences(n: int, rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    return " ".join(lorem_sentence(rng) for _ in range(max(0, n)))


def lorem_paragraphs(n: int, rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    return "\n\n".join(" ".join(lorem_sentence(rng) for _ in range(rng.randint(3, 6)))
                       for _ in range(max(0, n)))


def cmd_lorem(args: argparse.Namespace) -> int:
    if args.words:
        print(lorem_words(args.words))
    elif args.sentences:
        print(lorem_sentences(args.sentences))
    else:
        print(lorem_paragraphs(args.paragraphs or 3))
    return 0


# --------------------------------------------------------------- uuid

def make_uuid(v1: bool = False, upper: bool = False, dashes: bool = True) -> str:
    u = str(uuid.uuid1() if v1 else uuid.uuid4())
    if not dashes:
        u = u.replace("-", "")
    return u.upper() if upper else u


def cmd_uuid(args: argparse.Namespace) -> int:
    for _ in range(max(1, args.count)):
        print(paint(make_uuid(args.v1, args.upper, not args.no_dashes), C.BOLD))
    return 0


# --------------------------------------------------------------- hash

HASH_ALGOS = ("md5", "sha1", "sha256", "sha512")


def hash_bytes(data: bytes, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    h.update(data)
    return h.hexdigest()


def hash_file(path: Path, algos: tuple[str, ...] = ("sha256",)) -> dict[str, str]:
    hs = {a: hashlib.new(a) for a in algos}
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            for h in hs.values():
                h.update(chunk)
    return {a: h.hexdigest() for a, h in hs.items()}


def cmd_hash(args: argparse.Namespace) -> int:
    algos = list(HASH_ALGOS) if args.all else [args.algo]
    try:
        if args.file:
            digests = hash_file(Path(args.file), tuple(algos))
            label = str(args.file)
        elif args.text is not None:
            data = args.text.encode("utf-8")
            digests = {a: hash_bytes(data, a) for a in algos}
            label = f"{len(data)} bytes"
        else:
            data = sys.stdin.buffer.read()
            digests = {a: hash_bytes(data, a) for a in algos}
            label = f"{len(data)} bytes (stdin)"
    except OSError as e:
        print(err(f"\u2716 Cannot read input: {e}"), file=sys.stderr)
        return 2
    if len(digests) > 1:
        for a in algos:
            print(f"   {a:<7} {paint(digests[a], C.BOLD)}")
        print(dim(f"   ({label})"))
    else:
        print(digests[algos[0]])
    return 0


# --------------------------------------------------------------- http

def fetch_url(url: str, method: str = "GET", timeout: float = 10,
              max_bytes: int = 2000) -> dict:
    if "://" not in url:
        url = "http://" + url
    req = urllib.request.Request(url, method=(method or "GET").upper())
    t0 = time.time()

    def fail(status: int, error: str, reason: str = "", headers: dict | None = None,
             body: bytes = b"") -> dict:
        return {"ok": False, "status": status, "reason": reason, "headers": headers or {},
                "body": body, "truncated": False,
                "elapsed_ms": (time.time() - t0) * 1000, "error": error}

    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(max_bytes + 1)
            return {"ok": True, "status": r.status, "reason": r.reason or "",
                    "headers": dict(r.headers.items()),
                    "body": raw[:max_bytes], "truncated": len(raw) > max_bytes,
                    "elapsed_ms": (time.time() - t0) * 1000, "error": ""}
    except urllib.error.HTTPError as e:
        try:
            raw = e.read(max_bytes + 1)
        except Exception:
            raw = b""
        hdrs: dict = {}
        try:
            if e.headers:
                hdrs = dict(e.headers.items())
        except Exception:
            pass
        msg = f"HTTP {e.code} {e.reason or ''}".strip()
        d = fail(e.code, msg, e.reason or "", hdrs, raw[:max_bytes])
        d["truncated"] = len(raw) > max_bytes
        return d
    except urllib.error.URLError as e:
        return fail(0, f"Request failed: {e.reason}")
    except Exception as e:  # e.g. socket.timeout on some platforms
        return fail(0, f"Request failed: {e}")


def header_get(headers: dict, name: str) -> str:
    low = name.lower()
    for k, v in headers.items():
        if k.lower() == low:
            return v
    return ""


def _is_textual(content_type: str | None) -> bool:
    ct = (content_type or "").lower()
    return (ct.startswith(("text/", "application/json", "application/xml",
                           "application/javascript", "application/x-www-form-urlencoded"))
            or "+json" in ct or "+xml" in ct or "svg" in ct)


def cmd_http(args: argparse.Namespace) -> int:
    d = fetch_url(args.url, args.method, args.timeout, args.body)
    if not d["ok"] and d["status"] == 0:
        print(err(f"\u2716 {d['error']}"), file=sys.stderr)
        return 1
    color = C.GREEN if d["ok"] else C.YELLOW
    print(head(f"\n  \U0001f310  {(args.method or 'GET').upper()} {args.url}\n"))
    status_txt = f"{d['status']} {d['reason']}".strip()
    print(f"   Status: {paint(status_txt, color + C.BOLD)}   Time: {d['elapsed_ms']:.0f} ms")
    ctype = header_get(d["headers"], "Content-Type") or "?"
    print(f"   Type:   {ctype}")
    if args.headers:
        print(head("\n   Headers"))
        for k in sorted(d["headers"]):
            print(f"   {k}: {d['headers'][k]}")
    if not args.no_body:
        print(head("\n   Body"))
        if _is_textual(ctype):
            text = d["body"].decode("utf-8", errors="replace")
            print("   " + text.replace("\n", "\n   "))
            if d["truncated"]:
                print(dim(f"   \u2026truncated to {args.body} bytes"))
        else:
            print(dim(f"   [non-text body ({ctype}), {len(d['body'])} byte(s) hidden]"))
    print()
    return 0 if d["ok"] else 1


# ----------------------------------------------------------- vibe fix

GITIGNORE_TEMPLATE = """\
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
# Node
node_modules/
dist/
build/
# OS & editors
.DS_Store
.vscode/
.idea/
"""

README_TEMPLATE = """\
# {name}

> One-line description of what this does.

## Quick start

```bash
# how to run it
```

## License

MIT
"""

LICENSE_TEMPLATE = """\
MIT License

Copyright (c) {year} {author}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

SMOKE_TEST = ("# Smoke tests - green by default. Replace with real ones.\n"
              "import unittest\n"
              "\n"
              "\n"
              "class TestSmoke(unittest.TestCase):\n"
              "    def test_truth(self):\n"
              "        self.assertTrue(True)\n"
              "\n"
              "    def test_math(self):\n"
              "        self.assertEqual(2 + 2, 4)\n"
              "\n"
              "\n"
              "if __name__ == \"__main__\":\n"
              "    unittest.main()\n")


def vibe_fix(root: Path, assume_yes: bool = False) -> list[str]:
    root = root.resolve()
    author = _git(root, "config", "user.name") or "VibeCode"
    year = datetime.datetime.now().year
    candidates = [
        (root / "README.md", README_TEMPLATE.format(name=root.name), "README.md skeleton"),
        (root / "LICENSE", LICENSE_TEMPLATE.format(year=year, author=author), "MIT LICENSE"),
        (root / ".gitignore", GITIGNORE_TEMPLATE, ".gitignore (python+node)"),
        (root / "tests" / "test_smoke.py", SMOKE_TEST, "tests/test_smoke.py sample"),
    ]
    missing = [(p, c, d) for p, c, d in candidates if not p.exists()]
    if not missing:
        print(ok("\u2714 Nothing to fix \u2014 all basics present."))
        return []
    print(head("\n  \U0001f6e0  vibe fix \u2014 will create:\n"))
    for _, _, d in missing:
        print(f"   + {d}")
    print()
    if not assume_yes:
        try:
            ans = input("   Create these files? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return []
        if ans not in ("y", "yes"):
            print(dim("   Aborted. Coward's way out, but ok."))
            return []
    created = []
    for path, content, desc in missing:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            created.append(desc)
            print(ok(f"   \u2714 {desc}"))
        except OSError as e:
            print(err(f"   \u2716 {desc}: {e}"))
    print()
    return created


# ------------------------------------------------------ banner rainbow

RAINBOW = [91, 93, 92, 96, 94, 95]


def strip_ansi(s: str) -> str:
    return re.sub(r"\033\[[0-9;]+m", "", s)


def render_rainbow(text: str, fill: str = "#", font: str = "block") -> str:
    if os.environ.get("NO_COLOR"):
        return render_banner(text, fill, font=font)
    fontdict, _sep = FONTS.get(font, FONTS["block"])
    fill = (fill or "#")[0]
    rows = [""] * 5
    for ch in text.upper():
        glyph = fontdict.get(ch, fontdict["?"])
        for i in range(5):
            rows[i] += glyph[i].replace("#", fill) + _sep
    out = []
    for row in rows:
        line = ""
        for col, ch in enumerate(row.rstrip()):
            if ch in (" ", "\t"):
                line += ch
            else:
                line += f"\033[{RAINBOW[col % len(RAINBOW)]}m{ch}"
        out.append(line + "\033[0m")
    return "\n".join(out)


# ------------------------------------------------------- banner mini

# Compact 5x3 pixel font. Every glyph is 5 rows of exactly 3 chars.
FONT_MINI: dict[str, list[str]] = {
    "A": [" # ", "# #", "###", "# #", "# #"],
    "B": ["## ", "# #", "## ", "# #", "## "],
    "C": [" ##", "#  ", "#  ", "#  ", " ##"],
    "D": ["## ", "# #", "# #", "# #", "## "],
    "E": ["###", "#  ", "## ", "#  ", "###"],
    "F": ["###", "#  ", "## ", "#  ", "#  "],
    "G": [" ##", "#  ", "# #", "# #", " ##"],
    "H": ["# #", "# #", "###", "# #", "# #"],
    "I": ["###", " # ", " # ", " # ", "###"],
    "J": ["###", "  #", "  #", "# #", " # "],
    "K": ["# #", "## ", "#  ", "## ", "# #"],
    "L": ["#  ", "#  ", "#  ", "#  ", "###"],
    "M": ["# #", "###", "###", "# #", "# #"],
    "N": ["## ", "# #", "# #", "# #", "# #"],
    "O": [" # ", "# #", "# #", "# #", " # "],
    "P": ["###", "# #", "###", "#  ", "#  "],
    "Q": [" # ", "# #", "# #", "# #", " ##"],
    "R": ["## ", "# #", "## ", "# #", "# #"],
    "S": [" ##", "#  ", " # ", "  #", "## "],
    "T": ["###", " # ", " # ", " # ", " # "],
    "U": ["# #", "# #", "# #", "# #", "###"],
    "V": ["# #", "# #", "# #", "# #", " # "],
    "W": ["# #", "# #", "# #", "###", "###"],
    "X": ["# #", "# #", " # ", "# #", "# #"],
    "Y": ["# #", "# #", " # ", " # ", " # "],
    "Z": ["###", "  #", " # ", "#  ", "###"],
    "0": ["###", "# #", "# #", "# #", "###"],
    "1": [" # ", "## ", " # ", " # ", "###"],
    "2": ["###", "  #", " # ", "#  ", "###"],
    "3": ["###", "  #", " # ", "  #", "###"],
    "4": ["# #", "# #", "###", "  #", "  #"],
    "5": ["###", "#  ", "###", "  #", "###"],
    "6": [" ##", "#  ", "###", "# #", " # "],
    "7": ["###", "  #", " # ", " # ", " # "],
    "8": [" # ", "# #", " # ", "# #", " # "],
    "9": [" # ", "# #", "###", "  #", "## "],
    " ": ["   ", "   ", "   ", "   ", "   "],
    "-": ["   ", "   ", "###", "   ", "   "],
    "_": ["   ", "   ", "   ", "   ", "###"],
    "!": [" # ", " # ", " # ", "   ", " # "],
    "?": ["###", "  #", " # ", "   ", " # "],
    ".": ["   ", "   ", "   ", "   ", " # "],
    ":": ["   ", " # ", "   ", " # ", "   "],
    "/": ["  #", "  #", " # ", "#  ", "#  "],
    "+": ["   ", " # ", "###", " # ", "   "],
    "*": ["   ", "# #", " # ", "# #", "   "],
    "#": ["# #", "###", "# #", "###", "# #"],
}

FONTS = {"block": (FONT, "  "), "mini": (FONT_MINI, " ")}


# ------------------------------------------------------- completions

COMPLETION_COMMANDS = [
    ("analyze", "scan a project"),
    ("vibe-check", "score repo health"),
    ("banner", "ASCII banners"),
    ("stats", "system info"),
    ("json", "JSON tools"),
    ("b64", "base64 tools"),
    ("passgen", "password generator"),
    ("pomodoro", "focus timer"),
    ("dashboard", "live dashboard"),
    ("serve", "serve playground"),
    ("todo", "TODO manager"),
    ("git-stats", "git statistics"),
    ("lorem", "placeholder text"),
    ("uuid", "UUID generator"),
    ("hash", "checksums"),
    ("http", "fetch a URL"),
    ("completions", "shell completions"),
]

COMPLETION_FLAGS: dict[str, list[str]] = {
    "analyze": ["--json", "--ascii", "--top"],
    "vibe-check": ["--roast", "--json", "--fix", "--yes"],
    "banner": ["--char", "--rainbow", "--font"],
    "stats": [],
    "json": ["--indent", "--sort-keys", "--minify", "--validate", "--out"],
    "b64": ["encode", "decode", "--file"],
    "passgen": ["--length", "--count", "--no-symbols"],
    "pomodoro": ["--focus", "--rest", "--cycles"],
    "dashboard": ["--interval", "--once"],
    "serve": ["--dir", "--host", "--port", "--no-open"],
    "todo": ["add", "list", "done", "undone", "rm", "clear"],
    "git-stats": ["--authors", "--ascii"],
    "lorem": ["--words", "--sentences", "--paragraphs"],
    "uuid": ["--count", "--v1", "--upper", "--no-dashes"],
    "hash": ["--algo", "--all", "--file"],
    "http": ["--method", "--timeout", "--headers", "--body", "--no-body"],
    "completions": ["bash", "zsh", "fish"],
}


def completions_bash() -> str:
    cmds = " ".join(n for n, _ in COMPLETION_COMMANDS)
    cases = "\n".join(
        f'    {name}) flags="{" ".join(flags + ["--help"])}";;'
        for name, flags in [(n, COMPLETION_FLAGS.get(n, [])) for n, _ in COMPLETION_COMMANDS]
    )
    return f"""# vibecode bash completion — install with:
#   vibecode completions bash >> ~/.bashrc
_vibecode_complete() {{
  local cur cmd cmds flags
  cmds="{cmds}"
  if [[ $COMP_CWORD -eq 1 ]]; then
    COMPREPLY=($(compgen -W "$cmds" -- "${{COMP_WORDS[1]}}"))
    return 0
  fi
  cmd="${{COMP_WORDS[1]}}"
  cur="${{COMP_WORDS[COMP_CWORD]}}"
  case "$cmd" in
{cases}
    *) flags="--help";;
  esac
  COMPREPLY=($(compgen -W "$flags" -- "$cur"))
}}
complete -F _vibecode_complete vibecode
"""


def completions_zsh() -> str:
    entries = "\n".join(f"    '{n}:{h}'" for n, h in COMPLETION_COMMANDS)
    cases = "\n".join(
        f"        {n}) _arguments {' '.join(repr('--' + f[2:] if f.startswith('--') else f) for f in flags + ['--help'])} && return;;"
        for n, flags in [(n, COMPLETION_FLAGS.get(n, [])) for n, _ in COMPLETION_COMMANDS]
    )
    return f"""#compdef vibecode
# vibecode zsh completion — save as _vibecode somewhere in your $fpath
_vibecode() {{
  local -a cmds
  cmds=(
{entries}
  )
  _arguments -C '1:command:->cmd' '*::arg:->args'
  case $state in
    cmd) _describe 'command' cmds;;
    args)
      case $words[2] in
{cases}
      esac;;
  esac
}}
_vibecode "$@"
"""


def completions_fish() -> str:
    out = ["# vibecode fish completion — save to ~/.config/fish/completions/vibecode.fish"]
    for n, h in COMPLETION_COMMANDS:
        out.append(f"complete -c vibecode -f -n __fish_use_subcommand -a {n} -d '{h}'")
    for n, _ in COMPLETION_COMMANDS:
        for f in COMPLETION_FLAGS.get(n, []) + ["--help"]:
            if f.startswith("--"):
                out.append(f"complete -c vibecode -n '__fish_seen_subcommand_from {n}' -l {f[2:]}")
            else:
                out.append(f"complete -c vibecode -f -n '__fish_seen_subcommand_from {n}' -a {f}")
    return "\n".join(out) + "\n"


def cmd_completions(args: argparse.Namespace) -> int:
    if args.shell == "bash":
        print(completions_bash())
    elif args.shell == "zsh":
        print(completions_zsh())
    elif args.shell == "fish":
        print(completions_fish())
    else:
        print(err(f"\u2716 Unknown shell: {args.shell} (choose bash, zsh or fish)"), file=sys.stderr)
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vibecode",
        description="VibeCode v%s \u2014 zero-dependency developer toolkit (CLI + web playground)." % __version__,
        epilog="Examples:\n"
               "  vibecode analyze .            scan current project\n"
               "  vibecode vibe-check . --roast brutally honest repo review\n"
               "  vibecode banner 'SHIP IT'     big ASCII banner\n"
               "  vibecode serve                open the web playground\n"
               "  vibecode dashboard            live terminal dashboard\n"
               "  vibecode todo add 'ship it'    tiny TODO manager\n"
               "  vibecode git-stats .           authors + punchcard\n"
               "  vibecode http example.com      fetch a URL\n"
               "  vibecode vibe-check . --fix    scaffold missing files\n"
               "  eval \"$(vibecode completions bash)\"  tab-completion\n",
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
    v.add_argument("--fix", action="store_true", help="scaffold missing basics (README, LICENSE, .gitignore, tests)")
    v.add_argument("--yes", action="store_true", help="don't ask, just create files (with --fix)")
    v.set_defaults(func=cmd_vibe_check)

    b = sub.add_parser("banner", help="render a big ASCII banner")
    b.add_argument("text", help="text to render (A-Z, 0-9, few symbols)")
    b.add_argument("--char", default="#", help="fill character (default: #)")
    b.add_argument("--rainbow", action="store_true", help="neon gradient colors")
    b.add_argument("--font", choices=["block", "mini"], default="block", help="pixel font (default: block)")
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

    t = sub.add_parser("todo", help="tiny terminal TODO manager")
    ts = t.add_subparsers(dest="todo_cmd", metavar="<action>")
    tl = ts.add_parser("list", help="list tasks")
    tl.add_argument("--all", action="store_true", help="include completed")
    ta = ts.add_parser("add", help="add a task")
    ta.add_argument("text", nargs="+", help="task text")
    td = ts.add_parser("done", help="mark task done")
    td.add_argument("id", type=int)
    tu = ts.add_parser("undone", help="mark task pending")
    tu.add_argument("id", type=int)
    tr = ts.add_parser("rm", help="remove a task")
    tr.add_argument("id", type=int)
    tc = ts.add_parser("clear", help="remove completed tasks")
    tc.add_argument("--all", action="store_true", help="remove everything")
    t.set_defaults(func=cmd_todo)

    gs = sub.add_parser("git-stats", help="authors, punchcard, weekly activity")
    gs.add_argument("path", nargs="?", default=".", help="repo directory (default: .)")
    gs.add_argument("--authors", type=int, default=8, help="top N authors (default: 8)")
    gs.add_argument("--ascii", action="store_true", help="ASCII-only heatmap")
    gs.set_defaults(func=cmd_git_stats)

    lo = sub.add_parser("lorem", help="generate placeholder text")
    lo.add_argument("--words", type=int, help="N words")
    lo.add_argument("--sentences", type=int, help="N sentences")
    lo.add_argument("--paragraphs", type=int, help="N paragraphs (default: 3)")
    lo.set_defaults(func=cmd_lorem)

    uu = sub.add_parser("uuid", help="generate UUIDs")
    uu.add_argument("--count", type=int, default=1, help="how many (default: 1)")
    uu.add_argument("--v1", action="store_true", help="time-based v1 (default: random v4)")
    uu.add_argument("--upper", action="store_true", help="UPPERCASE output")
    uu.add_argument("--no-dashes", action="store_true", help="32 hex chars, no dashes")
    uu.set_defaults(func=cmd_uuid)

    hh = sub.add_parser("hash", help="md5/sha1/sha256/sha512 of text, file or stdin")
    hh.add_argument("--algo", choices=list(HASH_ALGOS), default="sha256")
    hh.add_argument("--all", action="store_true", help="print all algos")
    hh.add_argument("text", nargs="?", help="input text (default: stdin)")
    hh.add_argument("--file", help="read input from file")
    hh.set_defaults(func=cmd_hash)

    ht = sub.add_parser("http", help="fetch a URL: status, timing, headers, body")
    ht.add_argument("url", help="URL to fetch")
    ht.add_argument("--method", default="GET", help="HTTP method (default: GET)")
    ht.add_argument("--timeout", type=float, default=10, help="seconds (default: 10)")
    ht.add_argument("--headers", action="store_true", help="show response headers")
    ht.add_argument("--body", type=int, default=500, help="body preview bytes (default: 500)")
    ht.add_argument("--no-body", action="store_true", help="skip body preview")
    ht.set_defaults(func=cmd_http)

    cp = sub.add_parser("completions", help="print shell completion script")
    cp.add_argument("shell", choices=["bash", "zsh", "fish"], help="which shell")
    cp.set_defaults(func=cmd_completions)

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
