# Changelog

All notable changes to VibeCode. Format inspired by [Keep a Changelog](https://keepachangelog.com/).

## [1.1.0] — 2026-09-09

### Added — CLI (`vibecode.py`, now 16 commands, still stdlib-only)
- `todo` — tiny terminal TODO manager (`add`/`list`/`done`/`rm`/`clear`)
- `git-stats` — authors leaderboard, punchcard heatmap, last-12-weeks bars
- `lorem`, `uuid`, `hash`, `http` — everyday micro-utilities
- `vibe-check --fix` (+ `--yes`) — scaffolds README, LICENSE, .gitignore, sample tests
- `banner --rainbow` — neon gradient ASCII banners 🌈

### Added — playground (`index.html`, now 13 tools, still one offline file)
- ⏰ Cron parser (human description + next runs), 🔑 JWT decoder + HS256 verifier,
  📝 Lorem ipsum, Aa case converter
- Regex find/replace mode, merge-sort visualizer, gradient builder in Colors

### Tests & CI
- 42 unit tests (was 24), incl. local-HTTP and temp-git-repo integration tests
- CI smoke-test covers every new command

## [1.0.0] — 2026-09-09

- Initial release: 10-command stdlib CLI + 9-tool single-file playground,
  24 tests, CI with vibe-check dogfood gate.
