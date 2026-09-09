# Contributing to VibeCode ✨

Thanks for stopping by! This project is intentionally small and dependency-free — please keep it that way.

## Ground rules

1. **`vibecode.py` is stdlib-only.** No third-party imports, ever. If it can't be done with the standard library, it doesn't belong in the CLI.
2. **`index.html` is a single file.** No CDN links, no external fonts, no images. It must work from `file://` with Wi-Fi turned off.
3. **Everything must be tested.** New CLI feature → new test in `tests/`. New web tool → add its marker to `TestWebPlayground`.
4. **Keep the vibe.** Useful first, fun second, boring never.

## Quick start

```bash
git clone https://github.com/FsbAidolBIO/VibeCode.git
cd VibeCode

# run the test suite (stdlib unittest, nothing to install)
python -m unittest discover -s tests -v

# try the CLI
python vibecode.py vibe-check . --roast
python vibecode.py dashboard . --once

# try the web playground
python vibecode.py serve --no-open   # then open http://localhost:8000/
```

## Pull requests

- Fork, branch, commit, PR — the usual dance.
- Make sure `python -m unittest discover -s tests` is green.
- Make sure the repo still scores **≥ 80/100** on its own `vibe-check` (CI enforces this — we dogfood 🐶).
- Update `README.md` if you add a command or a web tool.

## Ideas welcome

Check the Roadmap section in `README.md` — or open an issue with your wildest (but still dependency-free) idea.
