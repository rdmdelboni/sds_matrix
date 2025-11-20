#!/usr/bin/env python3
"""Command-line tool for running extraction evaluations.

Usage:
    python -m src.evaluation.evaluate_extraction --ground-truth data/ground_truth.json
    python -m src.evaluation.evaluate_extraction --gt data/ground_truth.json --output report.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..database.duckdb_manager import DuckDBManager
from ..utils.config import DATA_DIR
from ..utils.logger import logger
from .metrics import EvaluationMetrics, GroundTruthLoader, save_report_json

def main() -> int:
    """Run evaluation and print report."""
    parser = argparse.ArgumentParser(
        description="Evaluate extraction quality against ground truth"
    )
    parser.add_argument(
        "--ground-truth",
        "--gt",
        type=str,
        required=True,
        help="Path to ground truth JSON file",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output JSON file path (optional)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=str(DATA_DIR / "duckdb" / "sds_matrix.db"),
        help="Database path (default: data/duckdb/sds_matrix.db)",
    )
    parser.add_argument(
        "--fields",
        type=str,
        nargs="+",
        help="Specific fields to evaluate (default: all)",
    )

    args = parser.parse_args()

    # Load ground truth
    logger.info("Loading ground truth from %s", args.ground_truth)
    ground_truth = GroundTruthLoader(args.ground_truth)

    if not ground_truth.ground_truth:
        logger.error("No ground truth data loaded. Exiting.")
        return 1

    # Initialize database
    logger.info("Connecting to database: %s", args.db_path)
    db = DuckDBManager(args.db_path)

    # Run evaluation
    logger.info("Running evaluation...")
    evaluator = EvaluationMetrics(db, ground_truth)
    report = evaluator.generate_report(fields=args.fields)

    # Print report
    evaluator.print_report(report)

    # Save to JSON if requested
    if args.output:
        save_report_json(report, args.output)
        print(f"\nReport saved to: {args.output}")

    # Return exit code based on overall accuracy
    if report.overall_accuracy >= 0.8:
        logger.info("✓ Evaluation PASSED (accuracy >= 80%%)")
        return 0
    else:
        logger.warning(
            "✗ Evaluation FAILED (accuracy %.1f%% < 80%%)",
            report.overall_accuracy * 100,
        )
        return 1

if __name__ == "__main__":
    sys.exit(main())
