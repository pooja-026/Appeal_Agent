"""Vendor-neutral analysis provider interfaces and the offline mock provider."""

from copy import deepcopy
from typing import Protocol

from .models import Analysis, Case
from .references import validate_analysis_references


class MockAnalysisUnavailable(ValueError):
    """Raised when the mock provider receives a case outside its fixtures."""


class AnalysisProvider(Protocol):
    """Small replaceable interface for future analysis providers."""

    def analyze(self, case: Case) -> Analysis:
        """Analyze a structured case and return a validated analysis."""


class MockAnalysisProvider:
    """Return deterministic analyses for the three authored sample cases only."""

    def __init__(self, cases: dict[str, Case], expected: dict[str, Analysis]) -> None:
        self._cases = cases
        self._expected = expected

    def analyze(self, case: Case) -> Analysis:
        fixture = self._cases.get(case.case_id)
        if fixture is None or case.model_dump(mode="json") != fixture.model_dump(mode="json"):
            raise MockAnalysisUnavailable(
                "mock analysis unavailable for this input; submit one of the "
                "unchanged authored sample cases"
            )

        analysis = deepcopy(self._expected[case.case_id])
        validate_analysis_references(case, analysis)
        return analysis
