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
