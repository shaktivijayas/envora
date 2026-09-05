# Envora — Phase 1 Design: Analyzer Core (No AI)

## Purpose

Envora is an AI-powered repository bootstrapping engine: given an arbitrary
GitHub repo URL, it clones the repo, deterministically analyzes its
structure, uses an LLM only for ambiguous inference steps, and outputs a
working Dockerfile, docker-compose.yml, devcontainer.json, .env.example,
and a human-readable setup report — then validates that the generated
environment actually builds and runs.

Core design principle: **deterministic parsing first, AI second,
validation always.** The LLM never freehands a Dockerfile from scratch; it
only fills gaps static analysis can't resolve, constrained to JSON
schemas, never interpolated into generated files without validation.

**This spec covers Phase 1 only** — the analyzer core, with no AI
involved. Phase 2 (LLM gap-filling) and Phase 3 (file generation +
validation) are out of scope here and must not be started until Phase 1's
completion gate (below) passes.

## Non-goals for this phase

- No LLM calls of any kind.
- No Dockerfile / docker-compose.yml / devcontainer.json / .env.example
  generation.
- No FastAPI service layer (the tech stack lists FastAPI for the
  eventual API; Phase 1 is CLI-only).
- No frontend.
- No subdirectory/monorepo manifest scanning in the stack detector —
  `stack.py` looks at repo-root manifest files only. A nested manifest
  (e.g. `apps/web/package.json`, `apps/api/pyproject.toml`) is not
  detected in Phase 1; splitting a true monorepo into per-package stack
  entries is deferred. This is a scope cut, not an oversight — don't let
  the orchestrator or later phases quietly assume root-only scanning
  extends to subdirectories without revisiting this.

## Project setup

- Location: `C:\Users\shakthi\Projects\envora`
- Tooling: `uv` for venv + dependency management + lockfile
- License: MIT
- Python floor: 3.11+
- CLI framework: Typer
- Repo cloning: GitPython, `--depth 1`
- Package name / import root: `envora`
- GitHub repo: to be created at `github.com/shaktivijayas/envora`

## Project layout

```
envora/
  pyproject.toml
  README.md
  LICENSE
  .gitignore                 # includes .cache/test-repos/
  src/envora/
    __init__.py
    cli.py                    # `envora analyze <repo-url>` — prints AnalysisResult
    cloner.py                 # shallow clone + branch detection
    analyzer/
      __init__.py
      models.py                # Detection, Confidence, AnalysisResult
      walk.py                   # filtered file walk
      stack.py
      package_manager.py
      framework.py
      runtime_version.py
      ports.py
      env_vars.py
      services.py
      analyzer.py               # orchestrator
  tests/
    unit/                      # synthetic fixtures, one suite per detector
      fixtures/
    integration/                # real-repo tests, @pytest.mark.integration
      fixtures/
        ambiguous_repo/          # synthetic negative-path fixture (local, not cloned)
  .cache/
    test-repos/                 # gitignored clone cache, keyed by repo+sha
```

## Detection model

```python
class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass(frozen=True)
class Detection:
    value: str | None
    confidence: Confidence
    evidence: list[str]

@dataclass(frozen=True)
class AnalysisResult:
    stack: list[Detection]
    package_manager: Detection
    framework: Detection
    runtime_version: Detection
    ports: list[Detection]
    env_vars: list[Detection]
    services: list[Detection]
```

`stack` is `list[Detection]`, not a singular `Detection`, so a repo with
more than one stack (a Node frontend alongside a Python backend, as in
the `belgattitude/nextjs-monorepo-example` validation case) can be
represented as multiple confident detections instead of forcing the
detector to arbitrarily pick one or degrade confidence for a case it's
actually sure about. Phase 1's stack detector only ever populates this
list with a single entry for non-monorepo repos — genuine multi-stack
splitting is out of scope here — but shaping the field this way now
avoids a breaking change to `AnalysisResult` later.

Every detector returns `Detection` objects — never a bare guess. A
missing or ambiguous signal is not an error; it's a `Detection` with
`value=None` and `confidence=LOW`, carrying an evidence string that
explains why (e.g. `"no package.json, no pyproject.toml, no Cargo.toml,
no go.mod found"`).

`Confidence` is an enum, not a calibrated float, so Phase 2's "run AI
only on LOW/None" logic is a simple filter, not a threshold to tune.

## cloner.py

- `clone(url: str) -> ClonedRepo` — shallow clone (`--depth 1`) to a temp
  dir via `tempfile.mkdtemp()`, detects the default branch via GitPython.
- Returns a `ClonedRepo(path: Path, branch: str, url: str)`; usable as a
  context manager so temp dirs are cleaned up after use.
- Clone failures (bad URL, network error, private/nonexistent repo) raise
  a typed `CloneError` with the underlying cause attached. The CLI
  catches this and reports a clean message — it never propagates a raw
  GitPython traceback to the user.

## walk.py

Single filtered walk shared by all detectors, excluding:
`node_modules`, `.git`, `dist`, `build`, `venv`, `.venv`, `__pycache__`,
`.next`, `target` (Rust), `vendor` (Go).

Also size-caps individual files before regex scanning via a named
constant, `MAX_SCAN_FILE_BYTES` (default 1MB), rather than a magic
number inline — so binary or generated files don't get scanned, and the
threshold has one place to tune once real repos (e.g. the FastAPI
template's lockfiles/generated OpenAPI schemas) show it needs
adjusting.

## Per-signal detection strategy

Manifest/lockfile evidence is always preferred (HIGH) over regex
evidence (MEDIUM/LOW). Each detector degrades gracefully rather than
raising:

**Stack** — presence of `package.json` (Node), `pyproject.toml` /
`setup.py` / `requirements.txt` (Python), `Cargo.toml` (Rust), `go.mod`
(Go), `pom.xml` / `build.gradle` (Java).

**Package manager** — lockfile presence:
`pnpm-lock.yaml`→pnpm, `yarn.lock`→yarn, `package-lock.json`→npm,
`poetry.lock`→poetry, `Pipfile.lock`→pipenv, bare `requirements.txt`→pip.
**Explicit no-lockfile case:** `package.json` present with no lockfile at
all resolves to `npm` at `LOW` confidence, evidence
`"no lockfile found, defaulting to npm convention"` — a real answer with
weak evidence, not `None`.

**Framework** — config file presence (`next.config.js`, `manage.py`,
FastAPI/Flask import patterns in source) cross-checked against manifest
dependencies. Tiebreak rule: config file alone or manifest dependency
alone → `MEDIUM`; both agree → `HIGH`; both present but naming different
frameworks (e.g. a stale `next.config.js` left over from a migration,
manifest no longer lists `next`) → `LOW`, with both pieces of evidence
listed so the conflict is visible rather than silently resolved.

**Runtime version** — `engines.node` in package.json, `.nvmrc`,
`.python-version`, `requires-python` / `[tool.poetry.dependencies]
python` in pyproject.toml. Tiebreak rule when sources disagree (e.g.
`.nvmrc` says 18, `engines.node` says 20): the manifest/lockfile-adjacent
source (`package.json` engines, `pyproject.toml` requires-python) wins
over the loose version-pin file (`.nvmrc`, `.python-version`), confidence
drops to `MEDIUM`, and evidence lists both conflicting values — never a
silent pick with no trace of the disagreement.

**Ports** — regex scoped to actual binding contexts only, never a bare
digit scan:
- `app.listen(`, `.listen(port` (Node)
- `PORT=`, `PORT:` (env/config)
- `EXPOSE` (Dockerfile)
- `:\d{2,5}` specifically inside Dockerfile / docker-compose.yml lines
- `uvicorn.run(..., port=`, `flask run --port`, Django `runserver`
- `.Run(":8080")` / `net.Listen` (Go)

**Env vars** — regex over `.env.example`, `README*`, and source patterns
`process\.env\.\w+`, `os\.getenv\(["']\w+["']\)`,
`os\.environ\[["']\w+["']\]`.

**Services** — connection-string regex (`postgres(ql)?://`, `redis://`,
`mongodb://`, `mysql://`) plus an existing `docker-compose.yml`'s
`image:` lines as corroborating evidence when present.

## Malformed manifest handling

Parsing a manifest (JSON/TOML) is wrapped in a try/except. A parse
failure degrades the relevant `Detection` to `LOW` confidence with an
evidence note like `"package.json present but unparseable: <error
message>"`. This is a distinct failure mode from "signal absent" and
must be distinguishable in the evidence text — it means the file exists
and something is there, just not confidently readable.

## analyzer.py (orchestrator)

`analyze(repo_path: Path) -> AnalysisResult` — runs the shared walk once,
passes the file list to each detector, assembles the `AnalysisResult`.
Detectors are independent and side-effect-free (pure functions over the
walked file list); the orchestrator has no detection logic of its own.
The stack detector returns `list[Detection]`; for Phase 1 it always
returns a single-entry list except where multiple independent manifest
files (e.g. both `package.json` and `pyproject.toml` at the repo root)
are unambiguously present, in which case each gets its own `HIGH`/`MEDIUM`
entry per the same evidence rules as a single-stack repo.

## CLI

`envora analyze <repo-url>` — clones the repo (via `cloner.py`), runs
`analyze()`, and prints the `AnalysisResult` as formatted JSON. This is
the only CLI surface for Phase 1; it exists to make manual testing and
the integration test assertions possible, not as a finished user-facing
tool.

## Testing strategy

**Unit tests** (`tests/unit/`) — one suite per detector, against small
synthetic fixture directories built in-repo. Fast, deterministic, no
network. Table-driven where useful (e.g. one test per lockfile → package
manager mapping).

**Integration tests** (`tests/integration/`, marked
`@pytest.mark.integration`, excluded from the default `pytest` run) —
clone real repos through `cloner.py` and run the full `analyze()`
end-to-end. Clones are cached under `.cache/test-repos/<owner>-<repo>-<sha>/`
(gitignored) after first pull, so reruns and CI don't depend on GitHub
being reachable every time. These are best-effort/manual-gate tests, not
a per-commit CI blocker — run explicitly via `pytest -m integration`.

**Phase 1 completion gate.** All of the following must hold before
Phase 2 work starts:

1. Five real repos, one per stack/package-manager combination, detect
   stack + ports + package manager at `HIGH` confidence with correct
   values:
   - `heroku/node-js-getting-started` — Node/Express/npm, `PORT` env var
   - `unjs/nitro` — Node/pnpm workspaces (substituted for
     `belgattitude/nextjs-monorepo-example`, which had drifted to yarn
     by implementation time)
   - `nsidnev/fastapi-realworld-example-app` — Python/FastAPI/poetry
     (substituted for `tiangolo/full-stack-fastapi-template`, which had
     drifted to uv by implementation time)
   - `tokio-rs/mini-redis` — Rust/Cargo, listening port
   - `gothinkster/golang-gin-realworld-example-app` — Go/go.mod, Postgres

   (If any of these has gone stale/private/renamed by implementation
   time, swap in an equivalent small real app for that stack — the
   binding requirement is stack coverage, not the exact repo names.)

2. A synthetic negative-path fixture (`tests/integration/fixtures/ambiguous_repo/`
   — no lockfile, no framework markers, just a bare script) degrades to
   `LOW`/`None` rather than guessing. This is the test that actually
   proves "never a bare guess" — the happy-path repos alone can't catch
   a detector that's miscalibrated toward false confidence.

If Phase 1 doesn't reliably clear this gate, Phase 2 does not start;
detectors get fixed first.

## Error handling summary

- Clone failure → typed `CloneError`, caught and reported cleanly by the CLI.
- Missing signal → `Detection(value=None, confidence=LOW, evidence=[...])`, not an exception.
- Malformed manifest → `Detection(confidence=LOW, evidence=["... but unparseable: ..."])`, not an exception, not conflated with "absent."
- No detector ever raises for a repo it merely doesn't understand well; exceptions are reserved for genuine infrastructure failures (clone/network), not weak signal.
