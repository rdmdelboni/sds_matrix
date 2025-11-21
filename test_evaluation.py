#!/usr/bin/env python3
"""Quick test of evaluation metrics system."""

from pathlib import Path

from src.database.duckdb_manager import DuckDBManager
from src.evaluation.metrics import EvaluationMetrics, GroundTruthLoader
from src.utils.config import DATA_DIR

def main():
    """Test evaluation system."""
    print("Testing Evaluation Metrics System")
    print("=" * 80)
    
    # Check if ground truth template exists
    gt_path = Path("data/ground_truth_template.json")
    if not gt_path.exists():
        print(f"❌ Ground truth file not found: {gt_path}")
        print("   Create this file with your test data first.")
        return 1
    
    # Load ground truth
    print(f"\n1. Loading ground truth from {gt_path}")
    ground_truth = GroundTruthLoader(gt_path)
    print(f"   ✓ Loaded {len(ground_truth.ground_truth)} documents")
    
    # Connect to database
    db_path = DATA_DIR / "duckdb" / "sds_matrix.db"
    print(f"\n2. Connecting to database: {db_path}")
    if not db_path.exists():
        print(f"   ❌ Database not found: {db_path}")
        print("   Process some documents first.")
        return 1
    
    db = DuckDBManager(str(db_path))
    print("   ✓ Connected")
    
    # Run evaluation
    print("\n3. Running evaluation...")
    evaluator = EvaluationMetrics(db, ground_truth)
    
    # Try evaluating a single field first
    print("\n4. Testing single field evaluation (numero_onu)...")
    metrics = evaluator.calculate_field_metrics("numero_onu")
    if metrics:
        print(f"   Total samples: {metrics.total_samples}")
        print(f"   Accuracy: {metrics.accuracy:.2%}")
        print(f"   ✓ Single field evaluation works")
    else:
        print("   ⚠ No data found for numero_onu")
    
    # Generate full report
    print("\n5. Generating full evaluation report...")
    report = evaluator.generate_report()
    
    # Print report
    evaluator.print_report(report)
    
    # Save report
    output_path = Path("data/evaluation_report.json")
    from src.evaluation.metrics import save_report_json
    save_report_json(report, output_path)
    print(f"\n✓ Report saved to {output_path}")
    
    print("\n" + "=" * 80)
    print("Evaluation system test completed successfully!")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
