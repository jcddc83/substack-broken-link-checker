# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.1] - 2026-09-17

### Fixed
- **Links are no longer silently dropped from the scan.** The filter that
  skips Substack's own subscribe / comment / share URLs tested
  `"substack.com" in link` against the whole URL, so a third-party address
  that merely mentioned substack.com — a redirector like
  `https://example.com/?next=https://x.substack.com/share` — was treated as
  Substack chrome and skipped. Nothing in the report indicated a link had gone
  unchecked, which is the worst failure mode this tool has. The host is now
  parsed, and the path segment must match.
- **An explicit port no longer defeats the domain flags.** `--skip-domains`,
  `--broken-domains` and `triage --retired-hosts` all compared the URL's
  `netloc`, which keeps the port — so `https://wikipedia.org:443/…` did not
  match a `wikipedia.org` entry and the flag quietly stopped applying. All
  host comparisons now use the parsed hostname, which also means userinfo
  (`https://listed.example@evil.example/`) can no longer make an unlisted host
  read as a listed one.

### Added
- `CONTRIBUTING.md` documents the hostname-comparison convention, including
  that slicing `netloc` silences CodeQL's substring warning without fixing the
  underlying problem.

## [1.3.0] - 2026-09-17

Two things the tool needed to be trusted unattended: a way to turn a report
into a work list, and a way to find out when a scheduled run dies.

### Added
- **`triage` subcommand.** Groups a report's failures by the work each one
  implies, which is a different axis from how much to trust them: a dead
  target and a mangled `href` are both `broken`, but one needs a replacement
  link and the other needs the post edited. Detects URLs concatenated in a
  post's HTML and suggests the leading half as the fix, without mistaking
  Wayback and Library of Congress archive URLs — which legitimately embed a
  second `http://` in their path — for concatenations.
- `triage --retired-hosts <file>` takes hostnames you know are retired. A
  retired subdomain often serves a mismatched certificate, so the check aborts
  before reading a status and files the row *inconclusive* when it is really
  dead. Only the publisher knows which hosts those are.
- **Failure alerts for unattended runs**, via
  `python -m substack_link_checker.notify`. A scheduled run that fails silently
  is worse than none, because "no broken links this month" and "the run died on
  its first post" look identical from the outside. Expired session cookies are
  called out specifically, since that is the failure that recurs. Configured
  entirely through `NOTIFY_*` environment variables — including
  `NOTIFY_SMTP_HOST` / `NOTIFY_SMTP_PORT`, so any SMTP server works — and it
  returns rather than raises when unconfigured, so a missing alert never
  replaces the error it was trying to report. Delivery uses a finite
  timeout (`NOTIFY_SMTP_TIMEOUT`, default 30s), since smtplib otherwise
  waits forever and would hang the very failure path it exists to surface.
- `secrets.ps1.example`, a template for the PowerShell scheduled run's
  configuration and credentials.

### Changed
- **`--output` now defaults to a timestamped filename** rather than the fixed
  `broken_links_report.csv`, so a scheduled run no longer overwrites the
  previous report. A clean run still writes no file at all.
- `run_link_checker.ps1` reads `SUBSTACK_URL` and its credentials from
  `secrets.ps1` (gitignored) instead of carrying them inline, sends a failure
  alert, and propagates a real exit code so Task Scheduler's "Last Run Result"
  means something. It also finds its own directory rather than needing a
  hardcoded path.

### Fixed
- `.env.example` documented a `SUBSTACK_BASE_URL` variable that nothing has
  ever read. Removed, and the `NOTIFY_*` variables documented in its place.

## [1.2.0] - 2026-09-17

Failed checks are now sorted by how much you should trust them, so the report
is a work list rather than a pile to triage by hand.

### Added
- **Failure classification.** Every failed check is now categorised as
  `broken` (the page is genuinely gone), `blocked` (the server refused us —
  the link is probably fine) or `inconclusive` (a timeout or 5xx, which says
  more about the moment than about the link). Measured across four months of
  real reports, 49.6% of failures were HTTP 403 and 11.2% were HTTP 429
  against only 12.7% genuine 404s — so reporting everything as "broken" made
  a report that was roughly seven-eighths noise.
- Malformed addresses — two URLs concatenated in a post's HTML, so the
  hostname contains a space — are detected without a network call and
  reported as broken. The target is fine; the `href` is not.
- `CATEGORY_BROKEN`, `CATEGORY_BLOCKED`, `CATEGORY_INCONCLUSIVE` and
  `classify_error` are exported from the package for downstream use.
- CI now runs the test suite on Windows as well as Linux. The tool's only
  real deployment is a Windows scheduled task, and its worst bug to date was
  Windows-only — the regression tests guarding it could not prove anything on
  a Linux-only matrix.

### Changed
- **The CSV gains a leading `category` column**, and rows are sorted most
  actionable first. If you parse the report by column position rather than by
  header name, this will shift your indices.
- The console summary breaks failures down by category instead of printing a
  single "Broken links found" total.

### Fixed
- Post titles are no longer blank when a post renders an empty `<h1>`. The
  fallback to `<title>` only triggered on a *missing* tag, not an empty one.
- The run no longer dies on the first broken link it finds when stdout is
  redirected on Windows. A redirected stream falls back to the locale
  encoding (cp1252 on most machines), which cannot encode the `✗` mark used
  to flag a broken link, so `UnicodeEncodeError` killed the process — meaning
  the checker only survived runs in which it found nothing wrong, and a
  scheduled job could appear healthy for weeks while producing nothing. The
  CLI now configures stdout and stderr for UTF-8 with `errors="replace"`
  before any subcommand writes output.

## [1.1.0] - 2026-05-19

Post-v1.0.0 repo-hygiene release. Adds packaging, CI, tests, security
hardening, automation, and docs without changing the link-checker's
runtime behavior. See the README's "Migrating from v1.0.0" section for
the CLI invocation changes.

### Added
- `pyproject.toml` making the project pip-installable with a
  `substack-link-checker` console entry point.
- GitHub Actions CI workflow (`.github/workflows/ci.yml`) running ruff
  lint, multi-version Python smoke tests, a real `pytest` suite, and a
  build step.
- Initial `pytest` test suite (`tests/`) covering domain filtering,
  CSV report generation, history persistence, the
  `load_domains_from_file` helper, and cookie-handling guarantees.
- `SECURITY.md` documenting vulnerability reporting and safe handling of
  Substack session cookies.
- `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`.
- Issue and pull request templates under `.github/`.
- Dependabot configuration for weekly dependency and Actions updates.
- `.env.example` documenting the supported environment variables.
- Release automation workflow (`.github/workflows/release.yml`): on
  pushing a `v*.*.*` tag, builds the sdist and wheel from
  `pyproject.toml` and attaches them to the GitHub Release. Verifies the
  tag matches the project version to prevent mismatched artifacts.
- CodeQL workflow (`.github/workflows/codeql.yml`) running GitHub's
  `security-and-quality` Python query suite on every push, PR, and
  weekly. Findings surface under the repo's Security tab.
- `pre-commit` config (`.pre-commit-config.yaml`) running ruff,
  trailing-whitespace / EOF / YAML / TOML / merge-conflict / large-file
  / private-key hooks before each commit. `CONTRIBUTING.md` updated
  with install instructions.

### Changed
- **Repository layout: scripts → package.** The top-level scripts have
  been reorganised into a `substack_link_checker` package under `src/`
  (src-layout). A new unified `substack-link-checker` CLI exposes the
  five workflows as subcommands: `check`, `compare`, `import`,
  `fetch-archive`, and `demo`.
- The helper scripts at the root (`compare_posts.py`,
  `import_checked_posts.py`, `fetch_archive_urls.py`,
  `demo_link_checker.py`) are kept as thin back-compat shims that
  delegate to the package, so existing `python compare_posts.py ...`
  invocations and the bundled `run_link_checker.ps1` keep working.
- **Breaking:** `python substack_link_checker.py ...` no longer works
  (its filename collides with the new package name). Use
  `substack-link-checker check ...` or
  `python -m substack_link_checker check ...` instead. The PowerShell
  scheduled task has been updated accordingly. See the "Migrating from
  v1.0.0" section in `README.md` for the full mapping.

### Security
- `SUBSTACK_COOKIE` environment variable is now supported as a safer
  alternative to the `--cookie` CLI flag (which leaks the cookie into
  shell history and `ps aux`). README and `SECURITY.md` updated to
  recommend the env-var path.

### Fixed
- Corrected the clone URL in `README.md` (was `substack-link-checker`,
  now `substack-broken-link-checker`).
- Troubleshooting section's code blocks now use the new
  `substack-link-checker check ...` invocations instead of the
  pre-refactor `python substack_link_checker.py ...` form.
- CI smoke test step in `.github/workflows/ci.yml` was still running
  `python substack_link_checker.py --help`, which started failing once
  the package refactor removed that root-level file. Updated to invoke
  the installed `substack-link-checker` console script instead. This
  was also blocking the Dependabot PRs from going green.

## [1.0.0] - 2026-01-01

Major rewrite of the Substack broken link checker with significant
performance improvements and new features. See the
[GitHub Release](https://github.com/jcddc83/substack-broken-link-checker/releases/tag/v1.0.0)
for the full announcement.

### Added
- Async concurrent link checking with `aiohttp` (10-20x faster than
  sequential).
- Smart link caching — the same URL across multiple posts is checked once.
- Retry logic with exponential backoff for transient failures.
- Incremental scanning: `--history-file` to track checked posts and
  `--only-new` to skip ones already covered.
- `import_checked_posts.py` to import previous results from Excel/CSV.
- Domain filtering: `--skip-domains` / `--skip-domains-file` to assume OK
  for bot-blocking sites; `--broken-domains` / `--broken-domains-file` to
  auto-flag known broken domains.
- `--cookie` flag for Substack session cookie authentication (works with
  paywalled / bot-protected content).
- Helper scripts: `compare_posts.py` to find unchecked posts,
  `fetch_archive_urls.py` as an archive-page fallback, and
  `run_link_checker.ps1` for Windows Task Scheduler automation.
- Complete `README.md` / `USAGE.md` rewrite with security considerations
  and expanded troubleshooting.

[Unreleased]: https://github.com/jcddc83/substack-broken-link-checker/compare/v1.3.1...HEAD
[1.3.1]: https://github.com/jcddc83/substack-broken-link-checker/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/jcddc83/substack-broken-link-checker/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/jcddc83/substack-broken-link-checker/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/jcddc83/substack-broken-link-checker/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/jcddc83/substack-broken-link-checker/releases/tag/v1.0.0
