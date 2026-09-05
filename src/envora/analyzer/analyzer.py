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
