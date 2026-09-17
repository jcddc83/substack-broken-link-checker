# Contributing

Thanks for your interest in improving the Substack Broken Link Checker.

## Development setup

```bash
git clone https://github.com/jcddc83/substack-broken-link-checker.git
cd substack-broken-link-checker
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Optional but recommended: install pre-commit hooks so the same lint
# checks CI runs fire automatically before each commit.
pip install pre-commit
pre-commit install
```

## Before opening a PR

If you installed pre-commit (above), the lint/format checks run on every
commit. Otherwise run them yourself:

- `ruff check .` — lint
- `ruff format .` — auto-format
- `pre-commit run --all-files` — runs everything pre-commit would
- `pytest` — test suite
- `substack-link-checker --help` — smoke-test the CLI

## Comparing hostnames

Almost everything here parses URLs, and there is one mistake this codebase has
made more than once. When you need a URL's host, take it from
`urlparse(url).hostname` — never from `netloc`, and never by searching the raw
link.

```python
# Wrong: matches any URL that merely mentions the host
if "example.com" in link: ...

# Wrong: netloc keeps the port and any userinfo, so
#   "example.com:443"            != "example.com"      (flag stops working)
#   "example.com@evil.example"   reads as example.com   (wrong host matches)
host = urlparse(link).netloc.lower().split(":")[0]

# Right: hostname strips userinfo and port, and lowercases
host = urlparse(link).hostname or ""
```

The first form is what CodeQL's `py/incomplete-url-substring-sanitization`
flags. Note the second form silences that alert without fixing the problem, so
please don't reach for it.

The two failure directions matter differently. Reading the host too loosely
means a third-party link gets treated as ours and **silently dropped from the
scan** — the worst outcome here, since nothing in the report says a link went
unchecked. Reading it too strictly means a `--skip-domains` or
`--retired-hosts` entry quietly stops applying.

When adding or changing host matching, cover these input forms in tests: an
explicit port, mixed case, userinfo (`https://listed.example@evil.example/`), a
lookalike suffix (`notexample.com` against `example.com`), and a relative URL
with no host at all. `tests/test_domain_filtering.py` and
`tests/test_substack_ui_links.py` have working examples.

## Filing issues

Please use the issue templates under `.github/ISSUE_TEMPLATE/`. For bugs,
include your Python version, OS, the command you ran (with the cookie
value redacted), and the full error output.

## Reporting security issues

See [SECURITY.md](SECURITY.md). Do **not** file public issues for security
vulnerabilities.

## Pull requests

- Keep PRs focused — one logical change per PR.
- Update the `README.md` and `USAGE.md` if you change CLI behavior.
- Add tests for new behavior where practical.
- Match the style of the surrounding code.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
