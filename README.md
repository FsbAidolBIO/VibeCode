![VibeCode — zero-dependency developer toolkit](assets/banner.svg)

[![CI](https://github.com/FsbAidolBIO/VibeCode/actions/workflows/ci.yml/badge.svg)](https://github.com/FsbAidolBIO/VibeCode/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Dependencies: zero](https://img.shields.io/badge/deps-zero-success.svg)](pyproject.toml)
[![Single-file web app](https://img.shields.io/badge/web-1%20file%20%E2%80%A2%20offline-violet.svg)](index.html)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

# ✨ VibeCode

**A developer toolkit with zero dependencies and maximum vibes.**

Two things, both genuinely useful, both work out of the box:

| | What | Deps | Run it |
|---|---|---|---|
| 💻 | **Terminal CLI** — `vibecode.py`: project analyzer, repo vibe-check, ASCII banners, pomodoro, live dashboard… | *none* (Python stdlib) | `python vibecode.py --help` |
| 🌐 | **Web playground** — `index.html`: JSON formatter, regex tester, Base64, password generator, pomodoro, sorting visualizer, Markdown preview, color tools | *none* (single file, offline) | double-click it, or `python vibecode.py serve` |

No `pip install`. No `npm install`. No signup, no tracking, no build step. Clone it, run it, love it.

---

## ⚡ Quick start

```bash
git clone https://github.com/FsbAidolBIO/VibeCode.git
cd VibeCode

python vibecode.py vibe-check . --roast   # brutally honest repo review 🔥
python vibecode.py analyze .              # what is this project made of?
python vibecode.py serve                  # open the web playground 🌐
```

## 💻 CLI — 10 commands, 1 file, 0 deps

Just Python 3.9+ and vibes:

| Command | What it does |
|---|---|
| `analyze [path]` | Languages, line counts, biggest files, ASCII charts (`--json` for scripts) |
| `vibe-check [path]` | Scores any repo 0–100: README, tests, CI, license, fresh commits… (`--roast` for pain) |
| `banner TEXT` | Big ASCII banners from a built-in pixel font — no `figlet` needed |
| `dashboard` | Live terminal dashboard: clock, CPU/RAM/disk, git branch, project stats |
| `pomodoro` | 25/5 focus timer with progress bar right in your terminal 🍅 |
| `stats` | System snapshot: OS, Python, CPUs, load, memory, disk |
| `json` | Validate / pretty-print / minify JSON from file or stdin |
| `b64` | Unicode-safe Base64 encode/decode (emoji survive 🌊) |
| `passgen` | Cryptographically secure passwords + entropy estimate |
| `serve` | Serves the web playground locally and opens your browser |

Real output, zero mockups:

```
$ python vibecode.py analyze . --top 5

  📊  VibeCode analyze  —  /home/user/VibeCode

   Files:  11   Lines:  2556   Size:  112.8 KB
   (skipped 1 binary file(s))

   Languages
   Python            3 files    1,238 lines  ██████████████████████
   HTML              1 files      904 lines  ████████████████░░░░░░
   Markdown          2 files      263 lines  █████░░░░░░░░░░░░░░░░░
   YAML              1 files       52 lines  █░░░░░░░░░░░░░░░░░░░░░
   SVG               1 files       41 lines  █░░░░░░░░░░░░░░░░░░░░░
   Other             2 files       31 lines  █░░░░░░░░░░░░░░░░░░░░░
   TOML              1 files       27 lines  ░░░░░░░░░░░░░░░░░░░░░░

   Largest files (top 5)
     48.9 KB      904 lines  index.html
     37.5 KB    1,001 lines  vibecode.py
     10.7 KB      225 lines  README.md
      8.5 KB      237 lines  tests/test_vibecode.py
      2.1 KB       41 lines  assets/banner.svg

   Verdict: a cute little project 💚
```

```
$ python vibecode.py vibe-check . --roast

  🔮  Vibe-check  —  /home/user/VibeCode

   ✔  README file            +15
   ✔  License                +10
   ✔  .gitignore             +10
   ✔  Tests                  +15
   ✔  CI workflow            +10
   ✔  Recent commit (<30d)   +10
   ✔  Real code (>3 files)   +10
   ✔  Docs / contributing    +5
   ✔  Project manifest       +5
   ✔  Clean git tree         +10

   Score: 100/100  [████████████████████]
   Tier:  LEGENDARY  🏆 This repo belongs in a museum. Flawless.
```

```
$ python vibecode.py banner "SHIP IT" --char "#"

 ####  #   #  #####  ####          #####  #####
#      #   #    #    #   #           #      #
 ###   #####    #    ####            #      #
    #  #   #    #    #               #      #
####   #   #  #####  #             #####    #
```

```
$ python vibecode.py dashboard . --once

╭────────────────────────────────────────────────────────────╮
│ ✨ VibeCode Dashboard — Wednesday, 09 September 2026        │
│ 🕐 19:54:01                                                 │
│ ────────────────────────────────────────────────────────── │
│ SYSTEM   CPUs: 2   Load: 0.06 / 0.02 / 0.00                │
│   Memory: 283 / 3939 MB used                               │
│   Disk:   817.4 MB / 20.3 GB used ░░░░░░░░░░░░             │
│ ────────────────────────────────────────────────────────── │
│ GIT      branch: main  •  clean ✔                          │
│   Last: a3a4bca ✨ VibeCode v1.0.0: zero-dependency CLI + si…
│ ────────────────────────────────────────────────────────── │
│ PROJECT  /home/user/VibeCode                               │
│   11 files • 2,556 lines  •  top: Python, HTML             │
│ ────────────────────────────────────────────────────────── │
│ “Ship early, ship often, touch grass.” — VibeCode          │
│ Press Ctrl+C to exit                                       │
╰────────────────────────────────────────────────────────────╯
```

> Want it as a real command? `pip install .` (or `pipx install .`) gives you a global `vibecode` — still zero dependencies.

## 🌐 Web playground — 9 tools in one file

![VibeCode playground visual](assets/hero.png)

`index.html` is the whole app. Save it, send it to a friend on a USB stick, open it on a plane — it just works:

| Tool | Highlights |
|---|---|
| 🏠 Home | Animated hero, feature map, typing effect |
| 📦 JSON | Format / minify / validate, sample, copy, download (`Ctrl+Enter` to format) |
| 🔍 Regex | Live highlighting, match list, capture groups, `g i m s` flags |
| 🔐 Base64 | Unicode-safe encode/decode |
| 🎲 Password | `crypto.getRandomValues()`, length slider, live entropy meter |
| 🍅 Pomodoro | Focus/break cycles, progress ring, WebAudio chime, cycle dots |
| 📊 Sorting | Animated bubble / selection / insertion / quick sort with counters |
| 📝 Markdown | Live preview, built-in mini parser, copy-as-HTML |
| 🎨 Colors | Palette generator (5 schemes, click-to-copy) + WCAG contrast checker |

Run it:

```bash
python vibecode.py serve          # serves + opens http://localhost:8000/
# ...or just double-click index.html. That's it. That's the install.
```

> 💡 Tip: enable **GitHub Pages** (Settings → Pages → Deploy from branch) and your playground gets a public URL for free.

## 🏆 We dogfood hard

This repo scores **100/100 LEGENDARY** on its own `vibe-check` — and CI fails the build if it ever drops below 80:

```yaml
- name: Dogfood — repo must pass its own vibe-check
  run: |
    python vibecode.py vibe-check . --json | python -c "...assert score >= 80..."
```

Plus 24 unit tests (stdlib `unittest`, no pytest needed) and an embedded-JS syntax check for `index.html` on every push, across Python 3.9/3.11/3.12.

## 📁 Structure

```
VibeCode/
├── vibecode.py            # the CLI — 10 commands, stdlib only
├── index.html             # the web playground — 9 tools, single file
├── tests/
│   └── test_vibecode.py   # 24 tests, unittest, zero deps
├── assets/
│   ├── banner.svg         # README banner (hand-made, crisp)
│   └── hero.png           # playground artwork
├── .github/workflows/ci.yml  # tests + JS check + vibe-check gate
├── CONTRIBUTING.md        # keep it dependency-free 🙏
├── pyproject.toml         # optional: pip install . → global `vibecode`
├── LICENSE                # MIT
└── README.md              # you are here 👋
```

## 🗺 Roadmap

- [ ] `vibecode todo` — markdown TODO manager in the terminal
- [ ] `vibecode git-stats` — who wrote what, punchcard charts
- [ ] More playground tools: cron parser, JWT decoder, lorem generator
- [ ] i18n for the playground (🇷🇺 first)
- [ ] Your idea here — open an issue!

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). TL;DR: **no new dependencies** — if it needs `pip`/`npm`, it doesn't ship. PRs welcome! 💜

## 🇷🇺 По-русски

**VibeCode** — это тулкит разработчика с нулем зависимостей:

- 💻 **CLI на Python** (`vibecode.py`): анализ проекта, `vibe-check` репозитория (оценка 0–100, есть режим `--roast` 🌶), ASCII-баннеры, помодоро-таймер, живой дашборд в терминале, генератор паролей, Base64, форматирование JSON.
- 🌐 **Веб-площадка** (`index.html`): 9 инструментов в одном файле — работает даже без интернета, просто открой в браузере.
- ✅ 24 автотеста, CI на каждый пуш, MIT-лицензия.

```bash
git clone https://github.com/FsbAidolBIO/VibeCode.git && cd VibeCode
python vibecode.py vibe-check . --roast
python vibecode.py serve
```

## 📄 License

MIT — do whatever you want, just keep the vibe. See [LICENSE](LICENSE).

---

<p align="center">If this made you smile — <b>⭐ star the repo</b> and share the vibe.<br>Built with Python, vanilla JS and an unreasonable love for side projects. 💜</p>
