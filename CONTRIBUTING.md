# Contributing to Minecraft Bumcraft Audit

Thanks for your interest! This repository documents and audits the Bumcraft Minecraft server implementation. Contributions are welcome.

## How to contribute

1. **Fork** the repository and create a feature branch from `main`.
2. **Make your changes** — documentation fixes, audit findings, remediation steps, or diagrams.
3. **Verify** any technical claims against the actual server files (`minecraft-server-bumcraft/`, `mc_ai_builder.py`, `mc_rcon_api.py`).
4. **Open a pull request** with a clear description of what changed and why.

## Documentation conventions

- Keep `docs/LLM_DISCLOSURE.md` up to date when AI assistance is used.
- Mark configuration values that are secrets as ⚠️ and never commit real credentials.
- Reference source file paths (e.g., `minecraft-server-bumcraft/docker-compose.yml`) when making claims.

## Code / config contributions

The Python services in `src/` are **verbatim copies** of the operator's running scripts. Do not modify them here to "fix" the live server — instead, document findings in `docs/` and let the operator apply changes to the production copies.

## Security

Never submit passwords, API keys, or world/player data. See `SECURITY.md` for vulnerability reporting.

## License

By contributing, you agree your contributions are licensed under the MIT License (`LICENSE`).