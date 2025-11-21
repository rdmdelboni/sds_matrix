"""Evaluation package for extraction quality assessment."""

from .metrics import (
    ConfidenceBin,
    EvaluationMetrics,
    EvaluationReport,
    FieldMetrics,
    GroundTruthLoader,
    save_report_json,
)

__all__ = [
    "GroundTruthLoader",
    "EvaluationMetrics",
    "EvaluationReport",
    "FieldMetrics",
    "ConfidenceBin",
    "save_report_json",
]
