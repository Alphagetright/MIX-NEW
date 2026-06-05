# -*- coding: utf-8 -*-
"""Multi-dimensional severity evaluation combining impact scope, fix cost,
data quality impact, and risk level into a single severity grade."""

from typing import Any, Dict, List, Optional, Tuple


class ImpactScorer:
    """Score the impact scope of a given error."""

    def __init__(self, impact_weights: Optional[Dict[str, float]] = None):
        self._weights = impact_weights or {
            "single_record": 1.0,
            "multi_record": 3.0,
            "field_corruption": 4.0,
            "structural": 5.0,
        }

    def score(self, impact_type: str) -> float:
        """Return the numeric weight for *impact_type* (default 1.0)."""
        return self._weights.get(impact_type, 1.0)


class FixCostEstimator:
    """Estimate the cost (in abstract units) to fix a given error."""

    def __init__(self, cost_levels: Optional[Dict[str, float]] = None):
        self._levels = cost_levels or {
            "trivial": 1.0,
            "easy": 2.0,
            "moderate": 3.0,
            "complex": 4.0,
            "impossible": 5.0,
        }

    def estimate(self, cost_level: str) -> float:
        """Return numeric estimate for the named cost level."""
        return self._levels.get(cost_level, 3.0)


class RiskAssessor:
    """Assess the risk level of an error based on its properties."""

    def __init__(self, risk_weights: Optional[Dict[str, float]] = None):
        self._weights = risk_weights or {
            "none": 0.0,
            "low": 1.0,
            "medium": 3.0,
            "high": 4.0,
            "critical": 5.0,
        }

    def assess(self, risk_label: str) -> float:
        return self._weights.get(risk_label, 0.0)


class SeverityMatrix:
    """Combine separate dimension scores into a single severity grade."""

    DIMENSION_WEIGHTS = {
        "impact": 0.35,
        "fix_cost": 0.20,
        "data_quality": 0.25,
        "risk": 0.20,
    }

    @classmethod
    def combine(cls, impact: float, fix_cost: float,
                data_quality: float, risk: float) -> Tuple[float, str]:
        """Compute weighted composite and return (score, label)."""
        score = (
            impact * cls.DIMENSION_WEIGHTS["impact"]
            + fix_cost * cls.DIMENSION_WEIGHTS["fix_cost"]
            + data_quality * cls.DIMENSION_WEIGHTS["data_quality"]
            + risk * cls.DIMENSION_WEIGHTS["risk"]
        )
        if score >= 4.0:
            label = "Critical"
        elif score >= 3.0:
            label = "Major"
        elif score >= 2.0:
            label = "Minor"
        elif score >= 1.0:
            label = "Warning"
        else:
            label = "Info"
        return (round(score, 2), label)


class SeverityEvaluator:
    """High-level severity evaluation orchestrator."""

    def __init__(self):
        self._impact_scorer = ImpactScorer()
        self._fix_cost_estimator = FixCostEstimator()
        self._risk_assessor = RiskAssessor()

    @property
    def impact_scorer(self) -> ImpactScorer:
        return self._impact_scorer

    @property
    def fix_cost_estimator(self) -> FixCostEstimator:
        return self._fix_cost_estimator

    @property
    def risk_assessor(self) -> RiskAssessor:
        return self._risk_assessor

    def evaluate(self, impact_type: str, cost_level: str,
                 data_quality_score: float, risk_label: str) -> Dict[str, Any]:
        """Run the full evaluation and return dimension breakdown + final grade."""
        impact = self._impact_scorer.score(impact_type)
        cost = self._fix_cost_estimator.estimate(cost_level)
        risk = self._risk_assessor.assess(risk_label)
        composite, label = SeverityMatrix.combine(impact, cost, data_quality_score, risk)
        return {
            "impact_score": impact,
            "fix_cost_score": cost,
            "data_quality_score": data_quality_score,
            "risk_score": risk,
            "composite_score": composite,
            "severity_label": label,
        }
