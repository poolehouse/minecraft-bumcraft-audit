# Security Policy

## ⚠️ Important: insecure defaults in the audited implementation

The Bumcraft server implementation ships with **hard-coded default credentials**:

* RCON password: `[REDACTED]` (in `server.properties`, `.rcon-cli.env`, and both Python scripts)
* CurseForge API key: empty placeholder (`CF_API_KEY=`)

**Rotate all credentials before deployment.** Do not expose RCON (25575/tcp) or the RCON HTTP API (8090/tcp) to the public internet without authentication and TLS.

## Supported versions

This is a community documentation/audit repository, not a software product with formal releases. Security patches are applied by the server operator to the production copies of the files audited here.

## Reporting a vulnerability

If you discover a security issue in the Bumcraft server implementation or this documentation:

1. **Do not** open a public GitHub issue for the vulnerability.
2. Contact the repository maintainer directly.
3. Include steps to reproduce, affected files, and suggested remediation.

## General best practices for this stack

* Store `CF_API_KEY`, `RCON_PASSWORD`, and Ollama endpoints in a secrets manager or CI secrets — never in git.
* Run the RCON API behind authentication (the current `mc_rcon_api.py` has none).
* Narrow `allow_origins` in `mc_rcon_api.py` if the API is internet-facing.
* Schedule automated world/config backups and test restores.
* Right-size the JVM heap (currently 24 GB) to avoid host OOM.
