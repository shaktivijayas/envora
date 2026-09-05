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
    # This repo has no Dockerfile/compose file — its only port signal is the
    # `process.env.PORT || 5006` fallback idiom in index.js, a source-level
    # match, not a declared binding. MEDIUM is the honest ceiling per the
    # spec's Ports confidence rule, not a detector gap to chase toward HIGH.
    assert any(d.confidence in (Confidence.HIGH, Confidence.MEDIUM) for d in result.ports)


def test_pnpm_monorepo_package_manager_detected_at_high_confidence(cached_clone):
    # Substitution note: belgattitude/nextjs-monorepo-example has since migrated
    # to yarn@4.6.0 (root .yarnrc.yml + yarn.lock, no pnpm-lock.yaml at all), so
    # it no longer exercises the pnpm signal this test targets. Swapped in
    # unjs/nitro, a small (~7MB) real pnpm workspace (root package.json +
    # pnpm-lock.yaml + pnpm-workspace.yaml), for the same node/pnpm combination.
    repo_path = cached_clone("https://github.com/unjs/nitro.git")

    result = analyze(repo_path)

    assert any(d.value == "node" for d in result.stack)
    assert result.package_manager.value == "pnpm"
    assert result.package_manager.confidence == Confidence.HIGH


def test_fastapi_poetry_detected_at_high_confidence(cached_clone):
    # Substitution note: tiangolo/full-stack-fastapi-template has since migrated
    # its backend from Poetry to uv (root pyproject.toml + uv.lock, no
    # poetry.lock), and gained a root package.json/bun.lock for its frontend
    # tooling, so it no longer exercises the python/poetry signal this test
    # targets. Swapped in nsidnev/fastapi-realworld-example-app, a small real
    # FastAPI backend still using Poetry (root pyproject.toml with
    # [tool.poetry] + poetry.lock, no competing root package.json).
    repo_path = cached_clone("https://github.com/nsidnev/fastapi-realworld-example-app.git")

    result = analyze(repo_path)

    assert any(d.value == "python" for d in result.stack)
    assert result.package_manager.value == "poetry"
    assert result.package_manager.confidence == Confidence.HIGH


def test_rust_cargo_stack_detected(cached_clone):
    repo_path = cached_clone("https://github.com/tokio-rs/mini-redis.git")

    result = analyze(repo_path)

    assert any(d.value == "rust" and d.confidence == Confidence.HIGH for d in result.stack)


def test_go_module_stack_detected(cached_clone):
    repo_path = cached_clone("https://github.com/gothinkster/golang-gin-realworld-example-app.git")

    result = analyze(repo_path)

    assert any(d.value == "go" and d.confidence == Confidence.HIGH for d in result.stack)
