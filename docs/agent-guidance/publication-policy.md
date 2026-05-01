# Publication Policy

## Public By Default
GitHub Pages publishes static site output to the public internet. Treat everything in generated `dist/` as public, regardless of repository visibility.

## Claim Rules
- Publish only claims that are traceable to `docs/verified-sources.md` or approved files in `src/content/**`.
- Avoid private firmware details unless an explicit approved public source is added first.
- Do not imply certifications, regulatory compliance, partnerships, availability, field performance, range, reliability, security posture, or production readiness without source-backed approval.
- Use cautious language for planned or exploratory work.

## Sensitive Material
Never publish:
- Credentials, tokens, private keys, API keys, `.env` values, or secrets.
- Private source code, logs, stack traces, issue text, pull request text, or screenshots.
- Device identifiers, radio keys, addresses, endpoints, or deployment-specific configuration.
- Private user, tester, customer, or organization information.

## Review Checklist
Before publishing content:
- Confirm each technical claim has an approved source.
- Confirm images and downloads are cleared for public use.
- Confirm links do not expose private repositories or private artifacts.
- Run `pnpm build`.

