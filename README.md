# Envora

AI-powered repository bootstrapping engine. Given a GitHub repo URL, Envora
clones it, deterministically analyzes its structure, and (in later phases)
generates a working Dockerfile, docker-compose.yml, devcontainer.json, and
.env.example — validating that the generated environment actually builds.

**Phase 1 (current):** deterministic analyzer core only. No AI, no file
generation yet. See `docs/superpowers/specs/2026-09-04-envora-phase1-design.md`.

## Usage (Phase 1)

```
uv run envora analyze https://github.com/<owner>/<repo>
```

## Development

```
uv sync
uv run pytest              # unit tests only
uv run pytest -m integration   # real-repo integration tests (network required)
```
