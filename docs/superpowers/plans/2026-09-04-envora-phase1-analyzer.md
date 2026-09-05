# Envora Phase 1 — Analyzer Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Envora's deterministic repository analyzer (clone + detect stack/package-manager/framework/runtime/ports/env-vars/services) with no AI involved, validated against 5 real repos plus one synthetic negative-path fixture.

**Architecture:** A `cloner` module shallow-clones a repo to a temp dir; an `analyzer` package runs one shared filtered file walk and a set of independent, pure detector functions over it (manifest/lockfile checks first, scoped regex second), each returning `Detection(value, confidence, evidence)` — never a bare guess. A thin Typer CLI wires clone → analyze → JSON output. Everything is proven by unit tests against synthetic fixtures plus integration tests against real cloned repos.

**Tech Stack:** Python 3.11+, uv (venv/deps/lockfile), Typer (CLI), GitPython (cloning), pytest (testing), stdlib `tomllib`/`json` (manifest parsing) — no other runtime dependencies.

**Spec:** `docs/superpowers/specs/2026-09-04-envora-phase1-design.md`

## Global Constraints

- Python floor: 3.11+ (enables stdlib `tomllib`, no extra TOML dependency).
- Package manager for Envora's own project: `uv`.
- License: MIT.
- CLI framework: Typer.
- Repo cloning: GitPython, `--depth 1`.
- Phase 1 scope only: no LLM calls, no Dockerfile/compose/devcontainer/.env.example generation, no FastAPI service layer, no frontend.
- Every detector returns `Detection(value, confidence, evidence)` — a missing/ambiguous signal is `Detection(value=None, confidence=Confidence.LOW, evidence=[...])`, never an exception and never a silent guess.
- `Confidence` is the enum `HIGH`/`MEDIUM`/`LOW` — not a float.
- Manifest/lockfile evidence always outranks regex evidence (HIGH over MEDIUM/LOW) when both are available.
- Malformed manifest (invalid JSON/TOML) degrades the relevant `Detection` to `LOW` with evidence `"<file> present but unparseable: <error>"` — distinct from "absent."
- Walk exclusions: `node_modules`, `.git`, `dist`, `build`, `venv`, `.venv`, `__pycache__`, `.next`, `target`, `vendor`.
- File content scans are capped by the named constant `MAX_SCAN_FILE_BYTES` (default `1_000_000`), never a magic number inline.
- Port regexes are scoped to binding contexts only — never a bare digit scan.
- `AnalysisResult.stack` is `list[Detection]` (not singular), even though Phase 1's detector only ever populates one entry for non-monorepo repos.

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `README.md`
- Create: `src/envora/__init__.py`
- Create: `src/envora/analyzer/__init__.py`
- Create: `tests/unit/__init__.py` (empty, allows relative fixtures if ever needed)
- Create: `tests/integration/__init__.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: an installable `envora` package at `src/envora`, a working `uv` environment, and a `pytest` runner with an `integration` marker registered — every later task builds inside this.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "envora"
version = "0.1.0"
description = "AI-powered repository bootstrapping engine — deterministic analysis first, AI second."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
dependencies = [
    "typer>=0.12",
    "gitpython>=3.1",
]

[project.scripts]
envora = "envora.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/envora"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: real-repo tests that clone from GitHub; run explicitly via `pytest -m integration`, excluded by default",
]
addopts = "-m 'not integration'"

[dependency-groups]
dev = [
    "pytest>=8.0",
]
```

- [ ] **Step 2: Write `.gitignore`**

```
__pycache__/
*.pyc
.venv/
.cache/
dist/
build/
*.egg-info/
```

- [ ] **Step 3: Write `LICENSE`**

```
MIT License

Copyright (c) 2026 shaktivijayas

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 4: Write `README.md`**

```markdown
# Envora

AI-powered repository bootstrapping engine. Given a GitHub repo URL, Envora
clones it, deterministically analyzes its structure, and (in later phases)
generates a working Dockerfile, docker-compose.yml, devcontainer.json, and
.env.example — validating that the generated environment actually builds.

**Phase 1 (current):** deterministic analyzer core only. No AI, no file
generation yet. See `docs/superpowers/specs/2026-09-04-envora-phase1-design.md`.

## Usage (Phase 1)

\`\`\`
uv run envora analyze https://github.com/<owner>/<repo>
\`\`\`

## Development

\`\`\`
uv sync
uv run pytest              # unit tests only
uv run pytest -m integration   # real-repo integration tests (network required)
\`\`\`
```

- [ ] **Step 5: Create package skeleton**

Create `src/envora/__init__.py` (empty) and `src/envora/analyzer/__init__.py` (empty).
Create `tests/unit/__init__.py` and `tests/integration/__init__.py` (both empty).

- [ ] **Step 6: Install and verify**

Run: `uv sync`
Expected: creates `.venv/` and `uv.lock`, no errors.

Run: `uv run pytest`
Expected: `no tests ran` (or `collected 0 items`) — exits 0, no errors.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore LICENSE README.md src tests uv.lock
git commit -m "Scaffold Envora project: pyproject.toml, package skeleton, pytest config

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GcMr2Q57NisUppAGHy4KTw"
```

- [ ] **Step 8: Create the GitHub repo and push**

Confirm with the user before running this — it creates a repo visible on their GitHub account.

Run: `gh repo create shaktivijayas/envora --public --source=. --remote=origin`
Run: `git push -u origin master`
Expected: repo created at `github.com/shaktivijayas/envora`, local `master` branch pushed and tracking `origin/master`.

---

## Task 2: Detection model (`models.py`)

**Files:**
- Create: `src/envora/analyzer/models.py`
- Test: `tests/unit/test_models.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Confidence` (enum: `HIGH`, `MEDIUM`, `LOW`), `Detection(value: str | None, confidence: Confidence, evidence: list[str])`, `AnalysisResult(stack: list[Detection], package_manager: Detection, framework: Detection, runtime_version: Detection, ports: list[Detection], env_vars: list[Detection], services: list[Detection])` — every later task imports these from `envora.analyzer.models`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_models.py
from envora.analyzer.models import AnalysisResult, Confidence, Detection


def test_confidence_is_str_enum_with_three_levels():
    assert Confidence.HIGH == "high"
    assert Confidence.MEDIUM == "medium"
    assert Confidence.LOW == "low"


def test_detection_is_frozen_and_holds_evidence():
    detection = Detection(value="npm", confidence=Confidence.HIGH, evidence=["package-lock.json present"])
    assert detection.value == "npm"
    assert detection.confidence == Confidence.HIGH
    assert detection.evidence == ["package-lock.json present"]


def test_detection_none_value_for_absent_signal():
    detection = Detection(value=None, confidence=Confidence.LOW, evidence=["no manifest found"])
    assert detection.value is None


def test_analysis_result_stack_is_a_list():
    result = AnalysisResult(
        stack=[Detection(value="node", confidence=Confidence.HIGH, evidence=["package.json present"])],
        package_manager=Detection(value="npm", confidence=Confidence.HIGH, evidence=["package-lock.json present"]),
        framework=Detection(value=None, confidence=Confidence.LOW, evidence=["no framework signal"]),
        runtime_version=Detection(value=None, confidence=Confidence.LOW, evidence=["no runtime signal"]),
        ports=[],
        env_vars=[],
        services=[],
    )
    assert isinstance(result.stack, list)
    assert result.stack[0].value == "node"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'envora.analyzer.models'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/envora/analyzer/models.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_models.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/envora/analyzer/models.py tests/unit/test_models.py
git commit -m "Add Detection/Confidence/AnalysisResult model

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GcMr2Q57NisUppAGHy4KTw"
```

---

## Task 3: Manifest parsing helper (`parsing.py`)

**Files:**
- Create: `src/envora/analyzer/parsing.py`
- Test: `tests/unit/test_parsing.py`

**Interfaces:**
- Consumes: nothing (stdlib `json`/`tomllib` only).
- Produces: `parse_json(path: Path) -> tuple[dict | None, str | None]`, `parse_toml(path: Path) -> tuple[dict | None, str | None]` — both return `(data, None)` on success or `(None, error_message)` on failure. `framework.py` and `runtime_version.py` (Tasks 8, 9) use these to implement malformed-manifest handling without duplicating try/except logic.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_parsing.py
from envora.analyzer.parsing import parse_json, parse_toml


def test_parse_json_valid(tmp_path):
    path = tmp_path / "package.json"
    path.write_text('{"name": "demo", "dependencies": {"next": "14.0.0"}}', encoding="utf-8")

    data, error = parse_json(path)

    assert error is None
    assert data == {"name": "demo", "dependencies": {"next": "14.0.0"}}


def test_parse_json_invalid_returns_error_not_exception(tmp_path):
    path = tmp_path / "package.json"
    path.write_text('{"name": "demo",,,}', encoding="utf-8")

    data, error = parse_json(path)

    assert data is None
    assert error is not None
    assert "demo" not in error or True  # error just needs to be a non-empty message
    assert isinstance(error, str) and len(error) > 0


def test_parse_toml_valid(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text('[project]\nrequires-python = ">=3.11"\n', encoding="utf-8")

    data, error = parse_toml(path)

    assert error is None
    assert data["project"]["requires-python"] == ">=3.11"


def test_parse_toml_invalid_returns_error_not_exception(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text("[project\nrequires-python = ", encoding="utf-8")

    data, error = parse_toml(path)

    assert data is None
    assert isinstance(error, str) and len(error) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_parsing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'envora.analyzer.parsing'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/envora/analyzer/parsing.py
from __future__ import annotations

import json
import tomllib
from pathlib import Path


def parse_json(path: Path) -> tuple[dict | None, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, str(exc)
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, str(exc)


def parse_toml(path: Path) -> tuple[dict | None, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, str(exc)
    try:
        return tomllib.loads(text), None
    except tomllib.TOMLDecodeError as exc:
        return None, str(exc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_parsing.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/envora/analyzer/parsing.py tests/unit/test_parsing.py
git commit -m "Add JSON/TOML parsing helper that returns errors, never raises

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GcMr2Q57NisUppAGHy4KTw"
```

---

## Task 4: Filtered file walk (`walk.py`)

**Files:**
- Create: `src/envora/analyzer/walk.py`
- Test: `tests/unit/test_walk.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `EXCLUDED_DIRS: set[str]`, `MAX_SCAN_FILE_BYTES: int`, `walk_repo(repo_path: Path) -> list[Path]` (absolute paths to every non-excluded file), `read_text_safe(path: Path) -> str | None` (returns `None` for oversized/unreadable/binary files instead of raising). Tasks 10-12 (ports/env_vars/services) and Task 8-9 (framework/runtime_version, for reading individual manifest files) depend on this.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_walk.py
from envora.analyzer.walk import MAX_SCAN_FILE_BYTES, read_text_safe, walk_repo


def test_walk_repo_finds_files(tmp_path):
    (tmp_path / "app.py").write_text("print('hi')", encoding="utf-8")
    nested = tmp_path / "src"
    nested.mkdir()
    (nested / "main.py").write_text("print('hi')", encoding="utf-8")

    files = walk_repo(tmp_path)

    names = {f.name for f in files}
    assert "app.py" in names
    assert "main.py" in names


def test_walk_repo_excludes_node_modules_and_friends(tmp_path):
    for excluded_dir in ("node_modules", ".git", "dist", "build", "venv", ".venv", "__pycache__", ".next", "target", "vendor"):
        d = tmp_path / excluded_dir
        d.mkdir()
        (d / "should_not_appear.txt").write_text("x", encoding="utf-8")
    (tmp_path / "real_file.py").write_text("print('hi')", encoding="utf-8")

    files = walk_repo(tmp_path)

    names = {f.name for f in files}
    assert "should_not_appear.txt" not in names
    assert "real_file.py" in names


def test_read_text_safe_returns_content_for_normal_file(tmp_path):
    path = tmp_path / "readme.txt"
    path.write_text("hello world", encoding="utf-8")

    assert read_text_safe(path) == "hello world"


def test_read_text_safe_returns_none_for_oversized_file(tmp_path):
    path = tmp_path / "big.txt"
    path.write_bytes(b"x" * (MAX_SCAN_FILE_BYTES + 1))

    assert read_text_safe(path) is None


def test_read_text_safe_returns_none_for_missing_file(tmp_path):
    assert read_text_safe(tmp_path / "does_not_exist.txt") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_walk.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'envora.analyzer.walk'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/envora/analyzer/walk.py
from __future__ import annotations

import os
from pathlib import Path

EXCLUDED_DIRS: set[str] = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "venv",
    ".venv",
    "__pycache__",
    ".next",
    "target",
    "vendor",
}

MAX_SCAN_FILE_BYTES = 1_000_000


def walk_repo(repo_path: Path) -> list[Path]:
    files: list[Path] = []
    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for filename in filenames:
            files.append(Path(root) / filename)
    return files


def read_text_safe(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_SCAN_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_walk.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/envora/analyzer/walk.py tests/unit/test_walk.py
git commit -m "Add filtered file walk with excluded dirs and size-capped safe read

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GcMr2Q57NisUppAGHy4KTw"
```

---

## Task 5: Repo cloner (`cloner.py`)

**Files:**
- Create: `src/envora/cloner.py`
- Test: `tests/unit/test_cloner.py`

**Interfaces:**
- Consumes: `git` (GitPython), stdlib `tempfile`/`shutil`.
- Produces: `class CloneError(Exception)` (has `.url` and `.cause`), `class ClonedRepo` (fields `path: Path`, `branch: str`, `url: str`; usable as a context manager that removes the temp dir on exit), `clone(url: str) -> ClonedRepo`. Task 14 (`cli.py`) and Task 15 (integration tests) depend on this.

- [ ] **Step 1: Write the failing test**

Tests clone from a local filesystem git repo (built inline) rather than a live GitHub URL, so this suite has no network dependency and isn't flaky.

```python
# tests/unit/test_cloner.py
import git
import pytest

from envora.cloner import CloneError, clone


@pytest.fixture
def local_source_repo(tmp_path):
    source = tmp_path / "source_repo"
    source.mkdir()
    repo = git.Repo.init(source, initial_branch="main")
    (source / "README.md").write_text("hello", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("initial commit")
    return source


def test_clone_succeeds_and_returns_path_and_branch(local_source_repo):
    with clone(str(local_source_repo)) as cloned:
        assert cloned.path.is_dir()
        assert (cloned.path / "README.md").is_file()
        assert cloned.branch == "main"
        assert cloned.url == str(local_source_repo)
        temp_dir = cloned.path

    assert not temp_dir.exists()  # context manager cleans up on exit


def test_clone_raises_clone_error_for_nonexistent_source(tmp_path):
    bad_path = tmp_path / "does_not_exist"

    with pytest.raises(CloneError) as exc_info:
        clone(str(bad_path))

    assert exc_info.value.url == str(bad_path)
    assert exc_info.value.cause is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_cloner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'envora.cloner'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/envora/cloner.py
from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import git


class CloneError(Exception):
    def __init__(self, url: str, cause: Exception) -> None:
        super().__init__(f"failed to clone {url}: {cause}")
        self.url = url
        self.cause = cause


@dataclass
class ClonedRepo:
    path: Path
    branch: str
    url: str

    def __enter__(self) -> "ClonedRepo":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


def clone(url: str) -> ClonedRepo:
    temp_dir = Path(tempfile.mkdtemp(prefix="envora-"))
    try:
        repo = git.Repo.clone_from(url, temp_dir, depth=1)
        branch = repo.active_branch.name
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise CloneError(url, exc) from exc
    return ClonedRepo(path=temp_dir, branch=branch, url=url)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_cloner.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/envora/cloner.py tests/unit/test_cloner.py
git commit -m "Add shallow-clone cloner with CloneError and self-cleaning ClonedRepo

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GcMr2Q57NisUppAGHy4KTw"
```

---

## Task 6: Stack detector (`stack.py`)

**Files:**
- Create: `src/envora/analyzer/stack.py`
- Test: `tests/unit/test_stack.py`

**Interfaces:**
- Consumes: `Confidence`, `Detection` from `envora.analyzer.models` (Task 2).
- Produces: `detect_stack(repo_path: Path) -> list[Detection]`. Task 13 (`analyzer.py`) calls this directly.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_stack.py
from envora.analyzer.models import Confidence
from envora.analyzer.stack import detect_stack


def test_detects_node_from_package_json(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")

    detections = detect_stack(tmp_path)

    assert len(detections) == 1
    assert detections[0].value == "node"
    assert detections[0].confidence == Confidence.HIGH


def test_detects_python_from_pyproject_toml(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    detections = detect_stack(tmp_path)

    assert detections[0].value == "python"
    assert detections[0].confidence == Confidence.HIGH


def test_detects_rust_from_cargo_toml(tmp_path):
    (tmp_path / "Cargo.toml").write_text("[package]\nname='x'\n", encoding="utf-8")

    detections = detect_stack(tmp_path)

    assert detections[0].value == "rust"


def test_detects_go_from_go_mod(tmp_path):
    (tmp_path / "go.mod").write_text("module example.com/x\n", encoding="utf-8")

    detections = detect_stack(tmp_path)

    assert detections[0].value == "go"


def test_detects_multiple_stacks_when_both_manifests_present(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    detections = detect_stack(tmp_path)

    values = {d.value for d in detections}
    assert values == {"node", "python"}


def test_no_manifest_found_returns_low_confidence_none(tmp_path):
    detections = detect_stack(tmp_path)

    assert len(detections) == 1
    assert detections[0].value is None
    assert detections[0].confidence == Confidence.LOW
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_stack.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'envora.analyzer.stack'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/envora/analyzer/stack.py
from __future__ import annotations

from pathlib import Path

from envora.analyzer.models import Confidence, Detection

# Root-level manifests only (no subdirectory/monorepo walk — see spec
# Non-goals). Each manifest found produces its own HIGH-confidence
# Detection; when multiple stacks' manifests are present, all of them
# are returned — no single value is chosen among them.
_STACK_MANIFESTS: list[tuple[str, tuple[str, ...]]] = [
    ("node", ("package.json",)),
    ("python", ("pyproject.toml", "setup.py", "requirements.txt")),
    ("rust", ("Cargo.toml",)),
    ("go", ("go.mod",)),
    ("java", ("pom.xml", "build.gradle")),
]


def detect_stack(repo_path: Path) -> list[Detection]:
    detections: list[Detection] = []
    for stack_name, manifests in _STACK_MANIFESTS:
        found = [m for m in manifests if (repo_path / m).is_file()]
        if found:
            detections.append(
                Detection(
                    value=stack_name,
                    confidence=Confidence.HIGH,
                    evidence=[f"{m} present at repo root" for m in found],
                )
            )

    if not detections:
        return [
            Detection(
                value=None,
                confidence=Confidence.LOW,
                evidence=[
                    "no package.json, pyproject.toml, setup.py, requirements.txt, "
                    "Cargo.toml, go.mod, pom.xml, or build.gradle found at repo root",
                ],
            )
        ]
    return detections
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_stack.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/envora/analyzer/stack.py tests/unit/test_stack.py
git commit -m "Add stack detector supporting multi-manifest repos

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GcMr2Q57NisUppAGHy4KTw"
```

---

## Task 7: Package manager detector (`package_manager.py`)

**Files:**
- Create: `src/envora/analyzer/package_manager.py`
- Test: `tests/unit/test_package_manager.py`

**Interfaces:**
- Consumes: `Confidence`, `Detection` from `envora.analyzer.models`.
- Produces: `detect_package_manager(repo_path: Path) -> Detection`. Task 13 calls this directly.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_package_manager.py
import pytest

from envora.analyzer.models import Confidence
from envora.analyzer.package_manager import detect_package_manager


@pytest.mark.parametrize(
    ("lockfile", "expected_manager"),
    [
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("package-lock.json", "npm"),
        ("poetry.lock", "poetry"),
        ("Pipfile.lock", "pipenv"),
    ],
)
def test_lockfile_maps_to_high_confidence_manager(tmp_path, lockfile, expected_manager):
    (tmp_path / lockfile).write_text("", encoding="utf-8")

    detection = detect_package_manager(tmp_path)

    assert detection.value == expected_manager
    assert detection.confidence == Confidence.HIGH


def test_package_json_with_no_lockfile_defaults_to_npm_at_low_confidence(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")

    detection = detect_package_manager(tmp_path)

    assert detection.value == "npm"
    assert detection.confidence == Confidence.LOW
    assert "no lockfile found" in detection.evidence[0]


def test_bare_requirements_txt_maps_to_pip(tmp_path):
    (tmp_path / "requirements.txt").write_text("flask\n", encoding="utf-8")

    detection = detect_package_manager(tmp_path)

    assert detection.value == "pip"
    assert detection.confidence == Confidence.MEDIUM


def test_no_manifest_or_lockfile_returns_low_confidence_none(tmp_path):
    detection = detect_package_manager(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_package_manager.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'envora.analyzer.package_manager'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/envora/analyzer/package_manager.py
from __future__ import annotations

from pathlib import Path

from envora.analyzer.models import Confidence, Detection

_LOCKFILE_MAP: list[tuple[str, str]] = [
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("package-lock.json", "npm"),
    ("poetry.lock", "poetry"),
    ("Pipfile.lock", "pipenv"),
]


def detect_package_manager(repo_path: Path) -> Detection:
    for lockfile, manager in _LOCKFILE_MAP:
        if (repo_path / lockfile).is_file():
            return Detection(
                value=manager,
                confidence=Confidence.HIGH,
                evidence=[f"{lockfile} present at repo root"],
            )

    if (repo_path / "package.json").is_file():
        return Detection(
            value="npm",
            confidence=Confidence.LOW,
            evidence=["no lockfile found, defaulting to npm convention"],
        )

    if (repo_path / "requirements.txt").is_file():
        return Detection(
            value="pip",
            confidence=Confidence.MEDIUM,
            evidence=["requirements.txt present at repo root"],
        )

    return Detection(
        value=None,
        confidence=Confidence.LOW,
        evidence=["no recognized lockfile or manifest found"],
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_package_manager.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/envora/analyzer/package_manager.py tests/unit/test_package_manager.py
git commit -m "Add package manager detector with explicit no-lockfile case

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GcMr2Q57NisUppAGHy4KTw"
```

---

## Task 8: Framework detector (`framework.py`)

**Files:**
- Create: `src/envora/analyzer/framework.py`
- Test: `tests/unit/test_framework.py`

**Interfaces:**
- Consumes: `Confidence`, `Detection` from `envora.analyzer.models`; `parse_json`, `parse_toml` from `envora.analyzer.parsing` (Task 3); `read_text_safe` from `envora.analyzer.walk` (Task 4).
- Produces: `detect_framework(repo_path: Path) -> Detection`. Task 13 calls this directly.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_framework.py
import json

from envora.analyzer.framework import detect_framework
from envora.analyzer.models import Confidence


def test_config_and_manifest_agree_gives_high_confidence(tmp_path):
    (tmp_path / "next.config.js").write_text("module.exports = {}", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"next": "14.0.0"}}), encoding="utf-8"
    )

    detection = detect_framework(tmp_path)

    assert detection.value == "nextjs"
    assert detection.confidence == Confidence.HIGH
    assert len(detection.evidence) == 2


def test_config_alone_gives_medium_confidence(tmp_path):
    (tmp_path / "manage.py").write_text("# django manage.py", encoding="utf-8")

    detection = detect_framework(tmp_path)

    assert detection.value == "django"
    assert detection.confidence == Confidence.MEDIUM


def test_manifest_alone_gives_medium_confidence(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"next": "14.0.0"}}), encoding="utf-8"
    )

    detection = detect_framework(tmp_path)

    assert detection.value == "nextjs"
    assert detection.confidence == Confidence.MEDIUM


def test_conflicting_config_and_manifest_gives_low_confidence(tmp_path):
    (tmp_path / "next.config.js").write_text("module.exports = {}", encoding="utf-8")
    (tmp_path / "manage.py").write_text("# stale leftover", encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {}}), encoding="utf-8")

    detection = detect_framework(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW
    assert "conflicting" in detection.evidence[0]


def test_fastapi_detected_via_pyproject_dependency(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["fastapi>=0.100"]\n', encoding="utf-8"
    )

    detection = detect_framework(tmp_path)

    assert detection.value == "fastapi"
    assert detection.confidence == Confidence.MEDIUM


def test_malformed_package_json_degrades_to_low_with_evidence(tmp_path):
    (tmp_path / "package.json").write_text("{not valid json,,,", encoding="utf-8")

    detection = detect_framework(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW
    assert "unparseable" in detection.evidence[0]


def test_no_signal_returns_low_confidence_none(tmp_path):
    detection = detect_framework(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_framework.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'envora.analyzer.framework'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/envora/analyzer/framework.py
from __future__ import annotations

import json
from pathlib import Path

from envora.analyzer.models import Confidence, Detection
from envora.analyzer.parsing import parse_json, parse_toml
from envora.analyzer.walk import read_text_safe

_CONFIG_FRAMEWORKS: list[tuple[str, str]] = [
    ("next.config.js", "nextjs"),
    ("next.config.mjs", "nextjs"),
    ("next.config.ts", "nextjs"),
    ("manage.py", "django"),
]

_MANIFEST_DEP_FRAMEWORKS: dict[str, str] = {
    "next": "nextjs",
    "django": "django",
    "fastapi": "fastapi",
    "flask": "flask",
}


def _config_signal(repo_path: Path) -> tuple[str, str] | None:
    for filename, framework in _CONFIG_FRAMEWORKS:
        if (repo_path / filename).is_file():
            return framework, f"{filename} present at repo root"
    return None


def _manifest_signal(repo_path: Path) -> tuple[tuple[str, str] | None, str | None]:
    package_json = repo_path / "package.json"
    if package_json.is_file():
        data, error = parse_json(package_json)
        if error is not None:
            return None, f"package.json present but unparseable: {error}"
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        for dep_name, framework in _MANIFEST_DEP_FRAMEWORKS.items():
            if dep_name in deps:
                return (framework, f'"{dep_name}" listed in package.json dependencies'), None

    pyproject = repo_path / "pyproject.toml"
    if pyproject.is_file():
        data, error = parse_toml(pyproject)
        if error is not None:
            return None, f"pyproject.toml present but unparseable: {error}"
        haystack = json.dumps(data).lower()
        for dep_name, framework in _MANIFEST_DEP_FRAMEWORKS.items():
            if dep_name in haystack:
                return (framework, f'"{dep_name}" referenced in pyproject.toml'), None

    requirements = repo_path / "requirements.txt"
    if requirements.is_file():
        text = (read_text_safe(requirements) or "").lower()
        for dep_name, framework in _MANIFEST_DEP_FRAMEWORKS.items():
            if dep_name in text:
                return (framework, f'"{dep_name}" referenced in requirements.txt'), None

    return None, None


def detect_framework(repo_path: Path) -> Detection:
    config = _config_signal(repo_path)
    manifest, manifest_error = _manifest_signal(repo_path)

    if manifest_error:
        evidence = [manifest_error]
        if config:
            evidence.append(config[1])
        return Detection(value=None, confidence=Confidence.LOW, evidence=evidence)

    if config and manifest:
        config_framework, config_evidence = config
        manifest_framework, manifest_evidence = manifest
        if config_framework == manifest_framework:
            return Detection(
                value=config_framework,
                confidence=Confidence.HIGH,
                evidence=[config_evidence, manifest_evidence],
            )
        return Detection(
            value=None,
            confidence=Confidence.LOW,
            evidence=[
                f"conflicting framework signals: {config_evidence} indicates {config_framework}, "
                f"but {manifest_evidence} indicates {manifest_framework}",
            ],
        )

    if config:
        framework, evidence = config
        return Detection(value=framework, confidence=Confidence.MEDIUM, evidence=[evidence])

    if manifest:
        framework, evidence = manifest
        return Detection(value=framework, confidence=Confidence.MEDIUM, evidence=[evidence])

    return Detection(
        value=None,
        confidence=Confidence.LOW,
        evidence=["no framework config file or manifest dependency match found"],
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_framework.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/envora/analyzer/framework.py tests/unit/test_framework.py
git commit -m "Add framework detector with config/manifest agreement tiebreak

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GcMr2Q57NisUppAGHy4KTw"
```

---

## Task 9: Runtime version detector (`runtime_version.py`)

**Files:**
- Create: `src/envora/analyzer/runtime_version.py`
- Test: `tests/unit/test_runtime_version.py`

**Interfaces:**
- Consumes: `Confidence`, `Detection` from `envora.analyzer.models`; `parse_json`, `parse_toml` from `envora.analyzer.parsing`; `read_text_safe` from `envora.analyzer.walk`.
- Produces: `detect_runtime_version(repo_path: Path) -> Detection`. Task 13 calls this directly.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_runtime_version.py
import json

from envora.analyzer.models import Confidence
from envora.analyzer.runtime_version import detect_runtime_version


def test_node_engines_field_high_confidence(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"engines": {"node": "20.x"}}), encoding="utf-8")

    detection = detect_runtime_version(tmp_path)

    assert detection.value == "20.x"
    assert detection.confidence == Confidence.HIGH


def test_nvmrc_alone_medium_confidence(tmp_path):
    (tmp_path / ".nvmrc").write_text("18\n", encoding="utf-8")

    detection = detect_runtime_version(tmp_path)

    assert detection.value == "18"
    assert detection.confidence == Confidence.MEDIUM


def test_node_conflicting_sources_manifest_wins_medium_confidence(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"engines": {"node": "20.x"}}), encoding="utf-8")
    (tmp_path / ".nvmrc").write_text("18\n", encoding="utf-8")

    detection = detect_runtime_version(tmp_path)

    assert detection.value == "20.x"
    assert detection.confidence == Confidence.MEDIUM
    assert "conflicting" in detection.evidence[0]


def test_python_requires_python_high_confidence(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.11"\n', encoding="utf-8")

    detection = detect_runtime_version(tmp_path)

    assert detection.value == ">=3.11"
    assert detection.confidence == Confidence.HIGH


def test_python_version_file_alone_medium_confidence(tmp_path):
    (tmp_path / ".python-version").write_text("3.11.4\n", encoding="utf-8")

    detection = detect_runtime_version(tmp_path)

    assert detection.value == "3.11.4"
    assert detection.confidence == Confidence.MEDIUM


def test_malformed_package_json_degrades_to_low(tmp_path):
    (tmp_path / "package.json").write_text("{not valid,,,", encoding="utf-8")

    detection = detect_runtime_version(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW
    assert "unparseable" in detection.evidence[0]


def test_no_signal_returns_low_confidence_none(tmp_path):
    detection = detect_runtime_version(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_runtime_version.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'envora.analyzer.runtime_version'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/envora/analyzer/runtime_version.py
from __future__ import annotations

import re
from pathlib import Path

from envora.analyzer.models import Confidence, Detection
from envora.analyzer.parsing import parse_json, parse_toml
from envora.analyzer.walk import read_text_safe

_VERSION_PATTERN = re.compile(r"(\d+(?:\.\d+)*)")


def _node_manifest_version(repo_path: Path) -> tuple[str | None, str | None]:
    package_json = repo_path / "package.json"
    if not package_json.is_file():
        return None, None
    data, error = parse_json(package_json)
    if error is not None:
        return None, f"package.json present but unparseable: {error}"
    node_version = data.get("engines", {}).get("node")
    if node_version:
        return node_version, f'engines.node = "{node_version}" in package.json'
    return None, None


def _node_pin_file(repo_path: Path) -> tuple[str | None, str | None]:
    nvmrc = repo_path / ".nvmrc"
    if not nvmrc.is_file():
        return None, None
    text = (read_text_safe(nvmrc) or "").strip()
    match = _VERSION_PATTERN.search(text)
    if not match:
        return None, None
    return match.group(1), f'.nvmrc = "{text}"'


def _python_manifest_version(repo_path: Path) -> tuple[str | None, str | None]:
    pyproject = repo_path / "pyproject.toml"
    if not pyproject.is_file():
        return None, None
    data, error = parse_toml(pyproject)
    if error is not None:
        return None, f"pyproject.toml present but unparseable: {error}"
    requires_python = data.get("project", {}).get("requires-python")
    if requires_python:
        return requires_python, f'requires-python = "{requires_python}" in pyproject.toml'
    poetry_python = data.get("tool", {}).get("poetry", {}).get("dependencies", {}).get("python")
    if poetry_python:
        return poetry_python, f'[tool.poetry.dependencies] python = "{poetry_python}" in pyproject.toml'
    return None, None


def _python_pin_file(repo_path: Path) -> tuple[str | None, str | None]:
    pin_file = repo_path / ".python-version"
    if not pin_file.is_file():
        return None, None
    text = (read_text_safe(pin_file) or "").strip()
    if not text:
        return None, None
    return text, f'.python-version = "{text}"'


def detect_runtime_version(repo_path: Path) -> Detection:
    for manifest_fn, pin_fn in (
        (_node_manifest_version, _node_pin_file),
        (_python_manifest_version, _python_pin_file),
    ):
        manifest_value, manifest_evidence = manifest_fn(repo_path)
        if manifest_evidence and manifest_value is None:
            return Detection(value=None, confidence=Confidence.LOW, evidence=[manifest_evidence])

        pin_value, pin_evidence = pin_fn(repo_path)

        if manifest_value and pin_value:
            if manifest_value == pin_value:
                return Detection(
                    value=manifest_value,
                    confidence=Confidence.HIGH,
                    evidence=[manifest_evidence, pin_evidence],
                )
            return Detection(
                value=manifest_value,
                confidence=Confidence.MEDIUM,
                evidence=[
                    f"conflicting runtime version sources: {manifest_evidence} vs {pin_evidence}; "
                    "manifest source takes precedence",
                ],
            )

        if manifest_value:
            return Detection(value=manifest_value, confidence=Confidence.HIGH, evidence=[manifest_evidence])

        if pin_value:
            return Detection(value=pin_value, confidence=Confidence.MEDIUM, evidence=[pin_evidence])

    return Detection(
        value=None,
        confidence=Confidence.LOW,
        evidence=["no runtime version signal found (engines.node, .nvmrc, requires-python, .python-version)"],
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_runtime_version.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/envora/analyzer/runtime_version.py tests/unit/test_runtime_version.py
git commit -m "Add runtime version detector with manifest-wins conflict tiebreak

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GcMr2Q57NisUppAGHy4KTw"
```

---

## Task 10: Ports detector (`ports.py`)

**Files:**
- Create: `src/envora/analyzer/ports.py`
- Test: `tests/unit/test_ports.py`

**Interfaces:**
- Consumes: `Confidence`, `Detection` from `envora.analyzer.models`; `read_text_safe` from `envora.analyzer.walk`.
- Produces: `detect_ports(repo_path: Path, files: list[Path]) -> list[Detection]` — takes the already-walked file list rather than walking itself (Task 13's orchestrator walks once and passes the list to this, `env_vars.py`, and `services.py`).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_ports.py
from envora.analyzer.models import Confidence
from envora.analyzer.ports import detect_ports


def test_detects_express_listen_call(tmp_path):
    app = tmp_path / "index.js"
    app.write_text("app.listen(3000, () => console.log('up'))", encoding="utf-8")

    detections = detect_ports(tmp_path, [app])

    assert detections[0].value == "3000"
    assert detections[0].confidence == Confidence.HIGH


def test_detects_uvicorn_port_kwarg(tmp_path):
    main = tmp_path / "main.py"
    main.write_text("uvicorn.run(app, host='0.0.0.0', port=8000)", encoding="utf-8")

    detections = detect_ports(tmp_path, [main])

    assert any(d.value == "8000" for d in detections)


def test_detects_dockerfile_expose(tmp_path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM node:20\nEXPOSE 4000\n", encoding="utf-8")

    detections = detect_ports(tmp_path, [dockerfile])

    assert any(d.value == "4000" for d in detections)


def test_ignores_bare_numbers_that_are_not_binding_contexts(tmp_path):
    src = tmp_path / "constants.py"
    src.write_text("MAX_RETRIES = 5000\nTIMEOUT = 30000\n", encoding="utf-8")

    detections = detect_ports(tmp_path, [src])

    assert detections[0].value is None
    assert detections[0].confidence == Confidence.LOW


def test_no_files_returns_low_confidence_none(tmp_path):
    detections = detect_ports(tmp_path, [])

    assert detections[0].value is None
    assert detections[0].confidence == Confidence.LOW
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_ports.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'envora.analyzer.ports'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/envora/analyzer/ports.py
from __future__ import annotations

import re
from pathlib import Path

from envora.analyzer.models import Confidence, Detection
from envora.analyzer.walk import read_text_safe

_GENERAL_PORT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"app\.listen\(\s*(\d{2,5})"),
    re.compile(r"\.listen\(\s*(?:port\s*=\s*)?(\d{2,5})"),
    re.compile(r"PORT\s*[=:]\s*(\d{2,5})"),
    re.compile(r"uvicorn\.run\([^)]*port\s*=\s*(\d{2,5})"),
    re.compile(r"--port[= ](\d{2,5})"),
    re.compile(r'\.Run\(":(\d{2,5})"\)'),
    re.compile(r"net\.Listen\([^)]*:(\d{2,5})"),
]

_DOCKER_FILENAMES = {"Dockerfile", "docker-compose.yml", "docker-compose.yaml"}
_DOCKER_PORT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"EXPOSE\s+(\d{2,5})"),
    re.compile(r":(\d{2,5})(?=[\"'\s]|$)"),
]


def detect_ports(repo_path: Path, files: list[Path]) -> list[Detection]:
    found: dict[str, list[str]] = {}

    for file_path in files:
        text = read_text_safe(file_path)
        if text is None:
            continue

        rel_path = file_path.relative_to(repo_path).as_posix()
        patterns = _DOCKER_PORT_PATTERNS if file_path.name in _DOCKER_FILENAMES else _GENERAL_PORT_PATTERNS

        for pattern in patterns:
            for match in pattern.finditer(text):
                port = match.group(1)
                evidence_line = f"{rel_path}: matched `{match.group(0).strip()}`"
                found.setdefault(port, []).append(evidence_line)

    if not found:
        return [
            Detection(
                value=None,
                confidence=Confidence.LOW,
                evidence=["no port-binding pattern found in source or Docker config"],
            )
        ]

    return [
        Detection(value=port, confidence=Confidence.HIGH, evidence=evidence)
        for port, evidence in sorted(found.items())
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_ports.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/envora/analyzer/ports.py tests/unit/test_ports.py
git commit -m "Add ports detector scoped to binding contexts, not bare digits

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GcMr2Q57NisUppAGHy4KTw"
```

---

## Task 11: Env vars detector (`env_vars.py`)

**Files:**
- Create: `src/envora/analyzer/env_vars.py`
- Test: `tests/unit/test_env_vars.py`

**Interfaces:**
- Consumes: `Confidence`, `Detection` from `envora.analyzer.models`; `read_text_safe` from `envora.analyzer.walk`.
- Produces: `detect_env_vars(repo_path: Path, files: list[Path]) -> list[Detection]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_env_vars.py
from envora.analyzer.env_vars import detect_env_vars
from envora.analyzer.models import Confidence


def test_detects_env_example_vars_at_high_confidence(tmp_path):
    env_file = tmp_path / ".env.example"
    env_file.write_text("DATABASE_URL=postgres://localhost/db\nPORT=3000\n", encoding="utf-8")

    detections = detect_env_vars(tmp_path, [env_file])

    values = {d.value for d in detections}
    assert values == {"DATABASE_URL", "PORT"}
    assert all(d.confidence == Confidence.HIGH for d in detections)


def test_detects_process_env_reference_in_source(tmp_path):
    src = tmp_path / "config.js"
    src.write_text("const port = process.env.PORT;", encoding="utf-8")

    detections = detect_env_vars(tmp_path, [src])

    assert detections[0].value == "PORT"
    assert detections[0].confidence == Confidence.MEDIUM


def test_detects_os_getenv_reference_in_source(tmp_path):
    src = tmp_path / "config.py"
    src.write_text('secret = os.getenv("SECRET_KEY")', encoding="utf-8")

    detections = detect_env_vars(tmp_path, [src])

    assert detections[0].value == "SECRET_KEY"


def test_detects_os_environ_bracket_reference(tmp_path):
    src = tmp_path / "config.py"
    src.write_text('db = os.environ["DATABASE_URL"]', encoding="utf-8")

    detections = detect_env_vars(tmp_path, [src])

    assert detections[0].value == "DATABASE_URL"


def test_no_env_var_references_returns_low_confidence_none(tmp_path):
    detections = detect_env_vars(tmp_path, [])

    assert detections[0].value is None
    assert detections[0].confidence == Confidence.LOW
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_env_vars.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'envora.analyzer.env_vars'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/envora/analyzer/env_vars.py
from __future__ import annotations

import re
from pathlib import Path

from envora.analyzer.models import Confidence, Detection
from envora.analyzer.walk import read_text_safe

_SOURCE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"process\.env\.(\w+)"),
    re.compile(r"os\.getenv\(\s*[\"'](\w+)[\"']"),
    re.compile(r"os\.environ\[\s*[\"'](\w+)[\"']\s*\]"),
]

_DOTENV_LINE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=")
_DOTENV_FILENAMES = {".env.example", ".env.sample", ".env.template"}


def detect_env_vars(repo_path: Path, files: list[Path]) -> list[Detection]:
    found: dict[str, list[str]] = {}

    for file_path in files:
        text = read_text_safe(file_path)
        if text is None:
            continue

        rel_path = file_path.relative_to(repo_path).as_posix()

        if file_path.name in _DOTENV_FILENAMES:
            for line in text.splitlines():
                match = _DOTENV_LINE.match(line)
                if match:
                    found.setdefault(match.group(1), []).append(f"{rel_path}: `{line.strip()}`")
            continue

        for pattern in _SOURCE_PATTERNS:
            for match in pattern.finditer(text):
                var_name = match.group(1)
                found.setdefault(var_name, []).append(f"{rel_path}: matched `{match.group(0)}`")

    if not found:
        return [
            Detection(
                value=None,
                confidence=Confidence.LOW,
                evidence=["no environment variable references found in .env.example or source"],
            )
        ]

    detections = []
    for var_name, evidence in sorted(found.items()):
        confidence = Confidence.HIGH if any(".env" in e for e in evidence) else Confidence.MEDIUM
        detections.append(Detection(value=var_name, confidence=confidence, evidence=evidence))
    return detections
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_env_vars.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/envora/analyzer/env_vars.py tests/unit/test_env_vars.py
git commit -m "Add env vars detector over .env.example and source patterns

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GcMr2Q57NisUppAGHy4KTw"
```

---

## Task 12: Services detector (`services.py`)

**Files:**
- Create: `src/envora/analyzer/services.py`
- Test: `tests/unit/test_services.py`

**Interfaces:**
- Consumes: `Confidence`, `Detection` from `envora.analyzer.models`; `read_text_safe` from `envora.analyzer.walk`.
- Produces: `detect_services(repo_path: Path, files: list[Path]) -> list[Detection]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_services.py
from envora.analyzer.models import Confidence
from envora.analyzer.services import detect_services


def test_detects_postgres_connection_string(tmp_path):
    src = tmp_path / "db.py"
    src.write_text('DATABASE_URL = "postgres://user:pass@localhost/db"', encoding="utf-8")

    detections = detect_services(tmp_path, [src])

    assert detections[0].value == "postgres"
    assert detections[0].confidence == Confidence.MEDIUM


def test_detects_redis_connection_string(tmp_path):
    src = tmp_path / "cache.py"
    src.write_text('REDIS_URL = "redis://localhost:6379"', encoding="utf-8")

    detections = detect_services(tmp_path, [src])

    assert detections[0].value == "redis"


def test_docker_compose_image_corroborates_and_raises_confidence(tmp_path):
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("services:\n  db:\n    image: postgres:16\n", encoding="utf-8")
    src = tmp_path / "db.py"
    src.write_text('DATABASE_URL = "postgres://user:pass@db/app"', encoding="utf-8")

    detections = detect_services(tmp_path, [compose, src])

    postgres = next(d for d in detections if d.value == "postgres")
    assert postgres.confidence == Confidence.HIGH
    assert len(postgres.evidence) == 2


def test_compose_image_alone_gives_high_confidence(tmp_path):
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("services:\n  cache:\n    image: redis:7\n", encoding="utf-8")

    detections = detect_services(tmp_path, [compose])

    assert detections[0].value == "redis"
    assert detections[0].confidence == Confidence.HIGH


def test_no_services_returns_low_confidence_none(tmp_path):
    detections = detect_services(tmp_path, [])

    assert detections[0].value is None
    assert detections[0].confidence == Confidence.LOW
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_services.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'envora.analyzer.services'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/envora/analyzer/services.py
from __future__ import annotations

import re
from pathlib import Path

from envora.analyzer.models import Confidence, Detection
from envora.analyzer.walk import read_text_safe

_CONNECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"postgres(?:ql)?://"), "postgres"),
    (re.compile(r"redis://"), "redis"),
    (re.compile(r"mongodb(?:\+srv)?://"), "mongodb"),
    (re.compile(r"mysql://"), "mysql"),
]

_COMPOSE_FILENAMES = {"docker-compose.yml", "docker-compose.yaml"}
_COMPOSE_IMAGE_LINE = re.compile(r"image:\s*[\"']?([\w./-]+)")

_IMAGE_TO_SERVICE: dict[str, str] = {
    "postgres": "postgres",
    "redis": "redis",
    "mongo": "mongodb",
    "mysql": "mysql",
    "mariadb": "mysql",
}


def _service_from_image(image: str) -> str | None:
    base = image.split("/")[-1].split(":")[0]
    return _IMAGE_TO_SERVICE.get(base)


def detect_services(repo_path: Path, files: list[Path]) -> list[Detection]:
    found: dict[str, list[str]] = {}

    for file_path in files:
        text = read_text_safe(file_path)
        if text is None:
            continue

        rel_path = file_path.relative_to(repo_path).as_posix()

        for pattern, service in _CONNECTION_PATTERNS:
            if pattern.search(text):
                found.setdefault(service, []).append(f"{rel_path}: connection string pattern `{service}://`")

        if file_path.name in _COMPOSE_FILENAMES:
            for match in _COMPOSE_IMAGE_LINE.finditer(text):
                service = _service_from_image(match.group(1))
                if service:
                    found.setdefault(service, []).append(f"{rel_path}: `image: {match.group(1)}`")

    if not found:
        return [
            Detection(
                value=None,
                confidence=Confidence.LOW,
                evidence=["no service connection strings or docker-compose service images found"],
            )
        ]

    detections = []
    for service, evidence in sorted(found.items()):
        confidence = Confidence.HIGH if len(evidence) > 1 or any("image:" in e for e in evidence) else Confidence.MEDIUM
        detections.append(Detection(value=service, confidence=confidence, evidence=evidence))
    return detections
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_services.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/envora/analyzer/services.py tests/unit/test_services.py
git commit -m "Add services detector from connection strings and compose images

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GcMr2Q57NisUppAGHy4KTw"
```

---

## Task 13: Analyzer orchestrator (`analyzer.py`)

**Files:**
- Create: `src/envora/analyzer/analyzer.py`
- Test: `tests/unit/test_analyzer.py`

**Interfaces:**
- Consumes: `AnalysisResult` from `envora.analyzer.models`; `walk_repo` from `envora.analyzer.walk`; `detect_stack`, `detect_package_manager`, `detect_framework`, `detect_runtime_version`, `detect_ports`, `detect_env_vars`, `detect_services` from Tasks 6-12.
- Produces: `analyze(repo_path: Path) -> AnalysisResult`. Task 14 (`cli.py`) and Task 15 (integration tests) call this directly.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_analyzer.py
import json

from envora.analyzer.analyzer import analyze
from envora.analyzer.models import Confidence


def test_analyze_combines_all_detectors_for_a_node_express_repo(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {}, "engines": {"node": "20.x"}}), encoding="utf-8"
    )
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    (tmp_path / "index.js").write_text(
        "const port = process.env.PORT;\napp.listen(3000, () => {});",
        encoding="utf-8",
    )
    (tmp_path / ".env.example").write_text("PORT=3000\nDATABASE_URL=postgres://localhost/db\n", encoding="utf-8")

    result = analyze(tmp_path)

    assert result.stack[0].value == "node"
    assert result.package_manager.value == "npm"
    assert result.package_manager.confidence == Confidence.HIGH
    assert result.runtime_version.value == "20.x"
    assert any(d.value == "3000" for d in result.ports)
    assert any(d.value == "PORT" for d in result.env_vars)
    assert any(d.value == "postgres" for d in result.services)


def test_analyze_on_empty_repo_degrades_everything_to_low(tmp_path):
    result = analyze(tmp_path)

    assert all(d.confidence == Confidence.LOW for d in result.stack)
    assert result.package_manager.confidence == Confidence.LOW
    assert result.framework.confidence == Confidence.LOW
    assert result.runtime_version.confidence == Confidence.LOW
    assert all(d.value is None for d in result.ports)
    assert all(d.value is None for d in result.env_vars)
    assert all(d.value is None for d in result.services)


def test_analyze_excludes_node_modules_from_port_scan(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    node_modules = tmp_path / "node_modules" / "some-lib"
    node_modules.mkdir(parents=True)
    (node_modules / "server.js").write_text("app.listen(9999)", encoding="utf-8")

    result = analyze(tmp_path)

    assert all(d.value != "9999" for d in result.ports)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_analyzer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'envora.analyzer.analyzer'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/envora/analyzer/analyzer.py
from __future__ import annotations

from pathlib import Path

from envora.analyzer.env_vars import detect_env_vars
from envora.analyzer.framework import detect_framework
from envora.analyzer.models import AnalysisResult
from envora.analyzer.package_manager import detect_package_manager
from envora.analyzer.ports import detect_ports
from envora.analyzer.runtime_version import detect_runtime_version
from envora.analyzer.services import detect_services
from envora.analyzer.stack import detect_stack
from envora.analyzer.walk import walk_repo


def analyze(repo_path: Path) -> AnalysisResult:
    files = walk_repo(repo_path)
    return AnalysisResult(
        stack=detect_stack(repo_path),
        package_manager=detect_package_manager(repo_path),
        framework=detect_framework(repo_path),
        runtime_version=detect_runtime_version(repo_path),
        ports=detect_ports(repo_path, files),
        env_vars=detect_env_vars(repo_path, files),
        services=detect_services(repo_path, files),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_analyzer.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/envora/analyzer/analyzer.py tests/unit/test_analyzer.py
git commit -m "Add analyzer orchestrator: single shared walk, all detectors combined

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GcMr2Q57NisUppAGHy4KTw"
```

---

## Task 14: CLI (`cli.py`)

**Files:**
- Create: `src/envora/cli.py`
- Test: `tests/unit/test_cli.py`

**Interfaces:**
- Consumes: `clone`, `CloneError` from `envora.cloner` (Task 5); `analyze` from `envora.analyzer.analyzer` (Task 13).
- Produces: Typer `app` object (entry point registered in `pyproject.toml` as the `envora` script), command `envora analyze <repo-url>`.

- [ ] **Step 1: Write the failing test**

Uses `monkeypatch` so this test needs no network — it substitutes `clone` with a fake that points at a local fixture directory, and separately verifies the `CloneError` path.

```python
# tests/unit/test_cli.py
import json

from typer.testing import CliRunner

import envora.cli as cli_module
from envora.cli import app
from envora.cloner import ClonedRepo, CloneError

runner = CliRunner()


def test_analyze_command_prints_json_result(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text('{"dependencies": {}}', encoding="utf-8")

    def fake_clone(url: str) -> ClonedRepo:
        return ClonedRepo(path=tmp_path, branch="main", url=url)

    monkeypatch.setattr(cli_module, "clone", fake_clone)

    result = runner.invoke(app, ["analyze", "https://github.com/example/repo"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["stack"][0]["value"] == "node"


def test_analyze_command_reports_clone_error_cleanly(monkeypatch):
    def fake_clone(url: str) -> ClonedRepo:
        raise CloneError(url, RuntimeError("network unreachable"))

    monkeypatch.setattr(cli_module, "clone", fake_clone)

    result = runner.invoke(app, ["analyze", "https://github.com/example/does-not-exist"])

    assert result.exit_code == 1
    assert "Error" in result.output
    assert "Traceback" not in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'envora.cli'`

- [ ] **Step 3: Write minimal implementation**

Note: `ClonedRepo` (Task 5) is a plain dataclass whose `__exit__` removes `self.path` — in the fake used by the test above, that path is the test's own `tmp_path`, which pytest cleans up itself, so this is safe for tests but the real CLI path always clones into a fresh temp dir per Task 5's `clone()`.

```python
# src/envora/cli.py
from __future__ import annotations

import json
from dataclasses import asdict

import typer

from envora.analyzer.analyzer import analyze
from envora.cloner import CloneError, clone

app = typer.Typer(help="Envora: deterministic repository analysis.")


@app.command("analyze")
def analyze_command(
    repo_url: str = typer.Argument(..., help="GitHub repo URL to analyze"),
) -> None:
    try:
        with clone(repo_url) as cloned:
            result = analyze(cloned.path)
    except CloneError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_cli.py -v`
Expected: 2 passed

- [ ] **Step 5: Manual smoke test**

Run: `uv run envora analyze https://github.com/heroku/node-js-getting-started`
Expected: valid JSON printed to stdout with `stack`, `package_manager`, etc.; exits 0. (Requires network — this is a manual sanity check, not part of the automated suite.)

- [ ] **Step 6: Commit**

```bash
git add src/envora/cli.py tests/unit/test_cli.py
git commit -m "Add envora analyze CLI command

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GcMr2Q57NisUppAGHy4KTw"
```

---

## Task 15: Integration tests — Phase 1 completion gate

**Files:**
- Create: `tests/integration/conftest.py`
- Create: `tests/integration/fixtures/ambiguous_repo/script.py`
- Create: `tests/integration/test_real_repos.py`

**Interfaces:**
- Consumes: `clone` is not used directly here (cache fixture clones straight via GitPython for persistence); `analyze` from `envora.analyzer.analyzer`; `Confidence` from `envora.analyzer.models`.
- Produces: the `cached_clone` pytest fixture (usable by any future integration test), and the suite that constitutes the Phase 1 completion gate defined in the spec.

- [ ] **Step 1: Write the clone-cache fixture**

```python
# tests/integration/conftest.py
from __future__ import annotations

import shutil
from pathlib import Path

import git
import pytest

CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache" / "test-repos"


@pytest.fixture
def cached_clone():
    def _get(repo_url: str) -> Path:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        repo_name = repo_url.rstrip("/").removesuffix(".git").split("/")[-1]
        existing = sorted(CACHE_DIR.glob(f"{repo_name}-*"))
        if existing:
            return existing[0]

        temp_clone_path = CACHE_DIR / f"{repo_name}-tmp"
        if temp_clone_path.exists():
            shutil.rmtree(temp_clone_path)
        temp_repo = git.Repo.clone_from(repo_url, temp_clone_path, depth=1)
        sha = temp_repo.head.commit.hexsha
        temp_repo.close()

        dest = CACHE_DIR / f"{repo_name}-{sha[:8]}"
        shutil.move(str(temp_clone_path), str(dest))
        return dest

    return _get
```

- [ ] **Step 2: Write the ambiguous-repo negative fixture**

```python
# tests/integration/fixtures/ambiguous_repo/script.py
def main() -> None:
    print("hello world")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write the failing test**

```python
# tests/integration/test_real_repos.py
from __future__ import annotations

from pathlib import Path

import pytest

from envora.analyzer.analyzer import analyze
from envora.analyzer.models import Confidence

pytestmark = pytest.mark.integration

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_ambiguous_repo_degrades_to_low_confidence_everywhere():
    result = analyze(FIXTURES_DIR / "ambiguous_repo")

    assert all(d.confidence == Confidence.LOW for d in result.stack)
    assert result.package_manager.confidence == Confidence.LOW
    assert result.framework.confidence == Confidence.LOW
    assert result.runtime_version.confidence == Confidence.LOW
    assert all(d.value is None for d in result.ports)
    assert all(d.value is None for d in result.env_vars)
    assert all(d.value is None for d in result.services)


def test_node_express_npm_detected_at_high_confidence(cached_clone):
    repo_path = cached_clone("https://github.com/heroku/node-js-getting-started.git")

    result = analyze(repo_path)

    assert any(d.value == "node" and d.confidence == Confidence.HIGH for d in result.stack)
    assert result.package_manager.value == "npm"
    assert result.package_manager.confidence == Confidence.HIGH
    assert any(d.confidence == Confidence.HIGH for d in result.ports)


def test_pnpm_monorepo_package_manager_detected_at_high_confidence(cached_clone):
    repo_path = cached_clone("https://github.com/belgattitude/nextjs-monorepo-example.git")

    result = analyze(repo_path)

    assert any(d.value == "node" for d in result.stack)
    assert result.package_manager.value == "pnpm"
    assert result.package_manager.confidence == Confidence.HIGH


def test_fastapi_poetry_detected_at_high_confidence(cached_clone):
    repo_path = cached_clone("https://github.com/tiangolo/full-stack-fastapi-template.git")

    result = analyze(repo_path)

    assert any(d.value == "python" for d in result.stack)
    assert result.package_manager.confidence == Confidence.HIGH


def test_rust_cargo_stack_detected(cached_clone):
    repo_path = cached_clone("https://github.com/tokio-rs/mini-redis.git")

    result = analyze(repo_path)

    assert any(d.value == "rust" and d.confidence == Confidence.HIGH for d in result.stack)


def test_go_module_stack_detected(cached_clone):
    repo_path = cached_clone("https://github.com/gothinkster/golang-gin-realworld-example-app.git")

    result = analyze(repo_path)

    assert any(d.value == "go" and d.confidence == Confidence.HIGH for d in result.stack)
```

- [ ] **Step 4: Run test to verify the ambiguous-repo case fails first (no network needed)**

Run: `uv run pytest tests/integration/test_real_repos.py::test_ambiguous_repo_degrades_to_low_confidence_everywhere -v -m integration`
Expected: passes immediately since it exercises `analyze()`, which already exists from Task 13 — this step is a sanity check that the marker and fixture wiring work, not a red/green cycle like earlier tasks.

- [ ] **Step 5: Run the full real-repo suite (requires network)**

Run: `uv run pytest tests/integration/test_real_repos.py -v -m integration`
Expected: all 6 tests pass. If any of the 5 real-repo tests fails because the detected package-manager/stack/port values differ from what's asserted, **inspect the actual cloned repo** under `.cache/test-repos/<repo>-<sha>/` (e.g. `cat .cache/test-repos/node-js-getting-started-*/package.json`) and either fix the relevant detector (if it's genuinely wrong) or tighten/correct the assertion to match the real repo's real structure — per the spec, this loop does not stop until all 5 real repos plus the ambiguous fixture pass for the right reasons.

If any of the 5 named repos no longer clones (renamed, deleted, made private), swap in an equivalent small real app for that same stack/package-manager combination and update both this test and the spec's completion-gate list.

- [ ] **Step 6: Commit**

```bash
git add tests/integration/conftest.py tests/integration/fixtures tests/integration/test_real_repos.py
git commit -m "Add Phase 1 completion gate: 5 real-repo integration tests + ambiguous-repo negative fixture

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GcMr2Q57NisUppAGHy4KTw"
```

- [ ] **Step 7: Push everything to GitHub**

Run: `git push`
Expected: all commits from Tasks 1-15 land on `github.com/shaktivijayas/envora`, satisfying the Phase 1 exit criteria below.

---

## Phase 1 exit criteria

Do not begin Phase 2 (LLM gap-filling) until:
- `uv run pytest` (unit suite, default) passes with zero failures.
- `uv run pytest -m integration` passes with zero failures, including all 5 real repos and the ambiguous-repo negative fixture.
- The GitHub repo `github.com/shaktivijayas/envora` exists and has been pushed to, mirroring local commits.
