# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
privately rather than opening a public issue.

- Preferred: use GitHub's [private vulnerability reporting](https://github.com/jcddc83/substack-broken-link-checker/security/advisories/new)
  if it is enabled on this repository.
- If that link returns a 404 (private reporting not enabled), open a
  **minimal** public issue asking the maintainer for a private contact
  channel — do **not** include exploit details, proof-of-concept code, or
  any session cookies in the public issue.

Please include:

- A description of the issue and its impact
- Steps to reproduce
- Affected versions / commit
- Any suggested mitigation

You can expect an initial response within 7 days.

## Supported Versions

Only the latest release on `main` receives security fixes.

## Handling Session Cookies

This tool accepts a Substack session cookie (`substack.sid`) via the
`--cookie` flag in order to access bot-protected or paywalled posts.
**Treat this value like a password.**

Recommended practices:

- Do **not** commit cookies to source control or paste them into public
  logs, screenshots, or issue reports.
- Prefer the `SUBSTACK_COOKIE` environment variable over the `--cookie`
  CLI flag. CLI arguments are visible in shell history (`~/.bash_history`,
  `~/.zsh_history`) and in process listings (`ps aux`), where any other
  user on the machine can read them.
- Rotate the cookie by logging out and back in if you suspect it was
  exposed. Substack session cookies typically expire after a few weeks.
- The cookie is scoped to `.substack.com` and will be sent by the
  synchronous `requests` session to any `*.substack.com` host the tool
  fetches. In normal use that is only your own Substack (the
  `--base-url`), but be aware of this if you point the tool elsewhere.
- Outbound link checks use a **separate** `aiohttp` session with no
  cookies attached, so external links are checked anonymously.

If you find the tool logging the cookie value to disk or transmitting it
to any host other than the configured Substack domain, please report it
through the channels above.

## Dependencies

Dependencies are pinned with minimum versions in `pyproject.toml` and
monitored via Dependabot (`.github/dependabot.yml`). Please update to the
latest release to pick up upstream security fixes.
