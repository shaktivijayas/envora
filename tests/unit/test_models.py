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
