"""Evaluation metrics for field extraction quality assessment.

Provides accuracy, precision, recall, confidence calibration, and distribution
analysis against ground truth data.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..database.duckdb_manager import DuckDBManager
from ..utils.logger import logger

@dataclass
class FieldMetrics:
    """Metrics for a single field across all documents."""

    field_name: str
    total_samples: int
    correct: int
    incorrect: int
    missing: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    avg_confidence: float
    avg_confidence_correct: float
    avg_confidence_incorrect: float

@dataclass
class ConfidenceBin:
    """Confidence calibration bin."""

    range_min: float
    range_max: float
    count: int
    correct_count: int
    actual_accuracy: float

@dataclass
class EvaluationReport:
    """Complete evaluation report."""

    overall_accuracy: float
    overall_precision: float
    overall_recall: float
    overall_f1: float
    field_metrics: dict[str, FieldMetrics]
    confidence_calibration: list[ConfidenceBin]
    confidence_distribution: dict[str, int]
    validation_status_dist: dict[str, int]

class GroundTruthLoader:
    """Load and manage ground truth data for evaluation."""

    def __init__(self, ground_truth_path: Path | str) -> None:
        """Initialize with path to ground truth JSON file.

        Expected format:
        {
            "document_name.pdf": {
                "numero_onu": "1203",
                "numero_cas": "1234-56-7",
                "classificacao_onu": "3",
                ...
            }
        }
        """
        self.path = Path(ground_truth_path)
        self.ground_truth: dict[str, dict[str, str]] = {}
        self._load()

    def _load(self) -> None:
        """Load ground truth from JSON file."""
        if not self.path.exists():
            logger.warning("Ground truth file not found: %s", self.path)
            return

        try:
            with open(self.path, encoding="utf-8") as f:
                self.ground_truth = json.load(f)
            logger.info(
                "Loaded ground truth for %d documents",
                len(self.ground_truth),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load ground truth: %s", exc)
            self.ground_truth = {}

    def get_expected_value(
        self, document_name: str, field_name: str
    ) -> str | None:
        """Get expected value for a document field."""
        doc_truth = self.ground_truth.get(document_name, {})
        return doc_truth.get(field_name)

    def has_ground_truth(self, document_name: str) -> bool:
        """Check if ground truth exists for document."""
        return document_name in self.ground_truth

    def get_all_documents(self) -> list[str]:
        """Get list of all documents with ground truth."""
        return list(self.ground_truth.keys())

class EvaluationMetrics:
    """Calculate evaluation metrics for extraction quality."""

    def __init__(
        self, db: DuckDBManager, ground_truth: GroundTruthLoader
    ) -> None:
        """Initialize with database and ground truth."""
        self.db = db
        self.ground_truth = ground_truth

    def _normalize_value(self, value: str | None) -> str:
        """Normalize value for comparison."""
        if not value:
            return ""
        return str(value).strip().upper().replace(" ", "")

    def _values_match(self, extracted: str | None, expected: str | None) -> bool:
        """Check if extracted value matches expected (normalized)."""
        return self._normalize_value(extracted) == self._normalize_value(expected)

    def evaluate_document(
        self, document_id: int, document_name: str
    ) -> dict[str, dict[str, Any]]:
        """Evaluate all fields for a single document.

        Returns:
            dict mapping field_name to evaluation results
        """
        if not self.ground_truth.has_ground_truth(document_name):
            logger.warning(
                "No ground truth for document: %s",
                document_name,
            )
            return {}

        field_details = self.db.get_field_details(document_id)
        results: dict[str, dict[str, Any]] = {}

        for field_name, details in field_details.items():
            expected = self.ground_truth.get_expected_value(
                document_name, field_name
            )
            if expected is None:
                continue

            extracted = details.get("value")
            confidence = float(details.get("confidence", 0.0) or 0.0)
            is_correct = self._values_match(extracted, expected)

            results[field_name] = {
                "expected": expected,
                "extracted": extracted,
                "confidence": confidence,
                "correct": is_correct,
                "validation_status": details.get("validation_status"),
            }

        return results

    def calculate_field_metrics(
        self, field_name: str
    ) -> FieldMetrics | None:
        """Calculate metrics for a specific field across all documents."""
        total = 0
        correct = 0
        incorrect = 0
        missing = 0
        confidence_sum = 0.0
        confidence_correct_sum = 0.0
        confidence_incorrect_sum = 0.0
        correct_with_conf = 0
        incorrect_with_conf = 0

        true_positives = 0
        false_positives = 0
        false_negatives = 0

        for doc_name in self.ground_truth.get_all_documents():
            expected = self.ground_truth.get_expected_value(doc_name, field_name)
            if expected is None:
                continue

            total += 1

            # Get document ID
            doc_result = self.db.conn.execute(
                "SELECT id FROM documents WHERE filename = ?",
                [doc_name],
            ).fetchone()

            if not doc_result:
                missing += 1
                false_negatives += 1
                continue

            document_id = doc_result[0]
            field_details = self.db.get_field_details(document_id)
            details = field_details.get(field_name, {})

            extracted = details.get("value")
            confidence = float(details.get("confidence", 0.0) or 0.0)
            confidence_sum += confidence

            if not extracted or extracted == "NAO ENCONTRADO":
                missing += 1
                false_negatives += 1
            elif self._values_match(extracted, expected):
                correct += 1
                true_positives += 1
                confidence_correct_sum += confidence
                correct_with_conf += 1
            else:
                incorrect += 1
                false_positives += 1
                confidence_incorrect_sum += confidence
                incorrect_with_conf += 1

        if total == 0:
            return None

        accuracy = correct / total
        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0.0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        return FieldMetrics(
            field_name=field_name,
            total_samples=total,
            correct=correct,
            incorrect=incorrect,
            missing=missing,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            avg_confidence=confidence_sum / total,
            avg_confidence_correct=(
                confidence_correct_sum / correct_with_conf
                if correct_with_conf > 0
                else 0.0
            ),
            avg_confidence_incorrect=(
                confidence_incorrect_sum / incorrect_with_conf
                if incorrect_with_conf > 0
                else 0.0
            ),
        )

    def calculate_confidence_calibration(
        self, bins: int = 10
    ) -> list[ConfidenceBin]:
        """Analyze confidence calibration across all extractions.

        Bins extractions by confidence and calculates actual accuracy in each bin.
        Well-calibrated: 80% confidence → 80% actual accuracy.
        """
        bin_size = 1.0 / bins
        bin_data: dict[int, dict[str, int]] = defaultdict(
            lambda: {"total": 0, "correct": 0}
        )

        for doc_name in self.ground_truth.get_all_documents():
            doc_result = self.db.conn.execute(
                "SELECT id FROM documents WHERE filename = ?",
                [doc_name],
            ).fetchone()

            if not doc_result:
                continue

            document_id = doc_result[0]
            field_details = self.db.get_field_details(document_id)

            for field_name, details in field_details.items():
                expected = self.ground_truth.get_expected_value(
                    doc_name, field_name
                )
                if expected is None:
                    continue

                extracted = details.get("value")
                confidence = float(details.get("confidence", 0.0) or 0.0)

                bin_idx = min(int(confidence / bin_size), bins - 1)
                bin_data[bin_idx]["total"] += 1

                if self._values_match(extracted, expected):
                    bin_data[bin_idx]["correct"] += 1

        calibration: list[ConfidenceBin] = []
        for i in range(bins):
            data = bin_data.get(i, {"total": 0, "correct": 0})
            total = data["total"]
            correct = data["correct"]

            calibration.append(
                ConfidenceBin(
                    range_min=i * bin_size,
                    range_max=(i + 1) * bin_size,
                    count=total,
                    correct_count=correct,
                    actual_accuracy=correct / total if total > 0 else 0.0,
                )
            )

        return calibration

    def generate_report(
        self, fields: list[str] | None = None
    ) -> EvaluationReport:
        """Generate comprehensive evaluation report.

        Args:
            fields: list of fields to evaluate (None = all fields)

        Returns:
            Complete evaluation report
        """
        if fields is None:
            # Get all unique field names from ground truth
            fields_set = set()
            for doc_truth in self.ground_truth.ground_truth.values():
                fields_set.update(doc_truth.keys())
            fields = list(fields_set)

        # Calculate per-field metrics
        field_metrics: dict[str, FieldMetrics] = {}
        for field in fields:
            metrics = self.calculate_field_metrics(field)
            if metrics:
                field_metrics[field] = metrics

        # Calculate overall metrics
        total_correct = sum(m.correct for m in field_metrics.values())
        total_samples = sum(m.total_samples for m in field_metrics.values())
        total_tp = sum(m.correct for m in field_metrics.values())
        total_fp = sum(m.incorrect for m in field_metrics.values())
        total_fn = sum(m.missing for m in field_metrics.values())

        overall_accuracy = total_correct / total_samples if total_samples > 0 else 0.0
        overall_precision = (
            total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        )
        overall_recall = (
            total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        )
        overall_f1 = (
            2 * overall_precision * overall_recall / (overall_precision + overall_recall)
            if (overall_precision + overall_recall) > 0
            else 0.0
        )

        # Confidence calibration
        calibration = self.calculate_confidence_calibration()

        # Confidence distribution
        conf_dist: dict[str, int] = {
            "0.0-0.3": 0,
            "0.3-0.5": 0,
            "0.5-0.7": 0,
            "0.7-0.9": 0,
            "0.9-1.0": 0,
        }

        # Validation status distribution
        val_dist: dict[str, int] = defaultdict(int)

        for doc_name in self.ground_truth.get_all_documents():
            doc_result = self.db.conn.execute(
                "SELECT id FROM documents WHERE filename = ?",
                [doc_name],
            ).fetchone()

            if not doc_result:
                continue

            document_id = doc_result[0]
            field_details = self.db.get_field_details(document_id)

            for details in field_details.values():
                confidence = float(details.get("confidence", 0.0) or 0.0)
                status = details.get("validation_status", "unknown")

                # Update distributions
                if confidence < 0.3:
                    conf_dist["0.0-0.3"] += 1
                elif confidence < 0.5:
                    conf_dist["0.3-0.5"] += 1
                elif confidence < 0.7:
                    conf_dist["0.5-0.7"] += 1
                elif confidence < 0.9:
                    conf_dist["0.7-0.9"] += 1
                else:
                    conf_dist["0.9-1.0"] += 1

                val_dist[status] += 1

        return EvaluationReport(
            overall_accuracy=overall_accuracy,
            overall_precision=overall_precision,
            overall_recall=overall_recall,
            overall_f1=overall_f1,
            field_metrics=field_metrics,
            confidence_calibration=calibration,
            confidence_distribution=conf_dist,
            validation_status_dist=dict(val_dist),
        )

    def print_report(self, report: EvaluationReport) -> None:
        """Print evaluation report to console."""
        print("\n" + "=" * 80)
        print("EXTRACTION QUALITY EVALUATION REPORT")
        print("=" * 80)

        print(f"\nOVERALL METRICS:")
        print(f"  Accuracy:  {report.overall_accuracy:.2%}")
        print(f"  Precision: {report.overall_precision:.2%}")
        print(f"  Recall:    {report.overall_recall:.2%}")
        print(f"  F1 Score:  {report.overall_f1:.2%}")

        print(f"\nPER-FIELD METRICS:")
        print(f"{'Field':<25} {'Samples':<8} {'Acc':<8} {'Prec':<8} {'Rec':<8} {'F1':<8}")
        print("-" * 80)
        for field_name, metrics in sorted(report.field_metrics.items()):
            print(
                f"{field_name:<25} "
                f"{metrics.total_samples:<8} "
                f"{metrics.accuracy:<8.2%} "
                f"{metrics.precision:<8.2%} "
                f"{metrics.recall:<8.2%} "
                f"{metrics.f1_score:<8.2%}"
            )

        print(f"\nCONFIDENCE CALIBRATION:")
        print(f"{'Range':<15} {'Count':<8} {'Correct':<10} {'Accuracy':<10}")
        print("-" * 80)
        for bin_info in report.confidence_calibration:
            if bin_info.count > 0:
                print(
                    f"{bin_info.range_min:.1f}-{bin_info.range_max:.1f}"
                    f"{'':<5} "
                    f"{bin_info.count:<8} "
                    f"{bin_info.correct_count:<10} "
                    f"{bin_info.actual_accuracy:<10.2%}"
                )

        print(f"\nCONFIDENCE DISTRIBUTION:")
        for range_label, count in sorted(report.confidence_distribution.items()):
            print(f"  {range_label}: {count}")

        print(f"\nVALIDATION STATUS DISTRIBUTION:")
        for status, count in sorted(report.validation_status_dist.items()):
            print(f"  {status}: {count}")

        print("\n" + "=" * 80 + "\n")

def save_report_json(report: EvaluationReport, output_path: Path | str) -> None:
    """Save evaluation report to JSON file."""
    output_path = Path(output_path)

    report_dict = {
        "overall": {
            "accuracy": report.overall_accuracy,
            "precision": report.overall_precision,
            "recall": report.overall_recall,
            "f1": report.overall_f1,
        },
        "fields": {
            name: {
                "total_samples": m.total_samples,
                "correct": m.correct,
                "incorrect": m.incorrect,
                "missing": m.missing,
                "accuracy": m.accuracy,
                "precision": m.precision,
                "recall": m.recall,
                "f1_score": m.f1_score,
                "avg_confidence": m.avg_confidence,
                "avg_confidence_correct": m.avg_confidence_correct,
                "avg_confidence_incorrect": m.avg_confidence_incorrect,
            }
            for name, m in report.field_metrics.items()
        },
        "calibration": [
            {
                "range": f"{b.range_min:.1f}-{b.range_max:.1f}",
                "count": b.count,
                "correct": b.correct_count,
                "accuracy": b.actual_accuracy,
            }
            for b in report.confidence_calibration
        ],
        "confidence_distribution": report.confidence_distribution,
        "validation_status_distribution": report.validation_status_dist,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2, ensure_ascii=False)

    logger.info("Evaluation report saved to %s", output_path)

__all__ = [
    "GroundTruthLoader",
    "EvaluationMetrics",
    "EvaluationReport",
    "FieldMetrics",
    "ConfidenceBin",
    "save_report_json",
]
