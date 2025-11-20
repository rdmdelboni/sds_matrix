# Evaluation Metrics System - User Guide

## Overview

The evaluation metrics system provides comprehensive quality assessment for field extraction against ground truth data. It measures accuracy, precision, recall, confidence calibration, and identifies areas for improvement.

## Features

- **Per-field metrics**: Accuracy, precision, recall, F1 score for each field
- **Overall metrics**: Aggregate performance across all fields
- **Confidence calibration**: Verify predicted confidence matches actual accuracy
- **Confidence distribution**: Analyze confidence score patterns
- **Validation status tracking**: Monitor validation outcomes
- **JSON export**: Save reports for CI/CD integration
- **CLI tool**: Easy command-line evaluation

## Quick Start

### 1. Create Ground Truth File

Create `data/ground_truth.json` with your test documents:

```json
{
  "document1.pdf": {
    "numero_onu": "1203",
    "numero_cas": "1234-56-7",
    "classificacao_onu": "3",
    "grupo_embalagem": "II",
    "nome_produto": "GASOLINE",
    "fabricante": "Example Corp"
  },
  "document2.pdf": {
    "numero_onu": "1090",
    "numero_cas": "67-64-1",
    "classificacao_onu": "3"
  }
}
```

**Format Rules:**
- Keys are exact document filenames (as stored in database)
- Values are field name → expected value mappings
- Include only fields you want to evaluate
- Use empty string "" for intentionally empty fields
- Omit fields that don't apply to that document

### 2. Run Evaluation

```bash
# Basic evaluation
python -m src.evaluation.evaluate_extraction --ground-truth data/ground_truth.json

# Save report to JSON
python -m src.evaluation.evaluate_extraction --gt data/ground_truth.json --output report.json

# Evaluate specific fields only
python -m src.evaluation.evaluate_extraction --gt data/ground_truth.json --fields numero_onu numero_cas

# Use custom database
python -m src.evaluation.evaluate_extraction --gt data/ground_truth.json --db-path /path/to/db.db
```

### 3. Interpret Results

The evaluation report includes:

**Overall Metrics:**
- **Accuracy**: % of correct extractions
- **Precision**: % of non-empty extractions that are correct
- **Recall**: % of expected values successfully extracted
- **F1 Score**: Harmonic mean of precision and recall

**Per-Field Metrics:**
- Same metrics calculated per field
- Identifies which fields perform best/worst

**Confidence Calibration:**
Shows actual accuracy at each confidence level:
```
Range      Count    Correct    Accuracy
0.7-0.8    45       36         80.0%    ✓ Well calibrated
0.8-0.9    67       52         77.6%    ✗ Overconfident
0.9-1.0    123      120        97.6%    ✓ Well calibrated
```

**Ideal**: Confidence matches accuracy (80% conf → 80% accuracy)
**Overconfident**: Confidence > accuracy (80% conf → 60% accuracy)
**Underconfident**: Confidence < accuracy (80% conf → 95% accuracy)

## Python API Usage

```python
from pathlib import Path
from src.database.duckdb_manager import DuckDBManager
from src.evaluation import GroundTruthLoader, EvaluationMetrics, save_report_json

# Load ground truth
gt = GroundTruthLoader("data/ground_truth.json")

# Connect to database
db = DuckDBManager("data/duckdb/sds_matrix.db")

# Run evaluation
evaluator = EvaluationMetrics(db, gt)
report = evaluator.generate_report()

# Print console report
evaluator.print_report(report)

# Access metrics programmatically
print(f"Overall accuracy: {report.overall_accuracy:.2%}")

for field_name, metrics in report.field_metrics.items():
    print(f"{field_name}: {metrics.accuracy:.2%}")

# Check confidence calibration
for bin in report.confidence_calibration:
    if bin.count > 0:
        calibration_error = abs(
            (bin.range_min + bin.range_max) / 2 - bin.actual_accuracy
        )
        if calibration_error > 0.15:
            print(f"Warning: Poor calibration in {bin.range_min}-{bin.range_max}")

# Save to JSON
save_report_json(report, "evaluation_report.json")
```

## CI/CD Integration

The evaluation script returns exit codes for automated testing:

- **Exit 0**: Accuracy ≥ 80% (PASS)
- **Exit 1**: Accuracy < 80% (FAIL)

```bash
# In CI pipeline
python -m src.evaluation.evaluate_extraction --gt data/ground_truth.json || exit 1
```

Example GitHub Actions workflow:

```yaml
- name: Run Extraction Evaluation
  run: |
    python -m src.evaluation.evaluate_extraction \
      --ground-truth tests/fixtures/ground_truth.json \
      --output evaluation_report.json
  
- name: Upload Evaluation Report
  uses: actions/upload-artifact@v3
  with:
    name: evaluation-report
    path: evaluation_report.json
```

## Metrics Definitions

### Accuracy
```
Accuracy = Correct Extractions / Total Samples
```
- **Use for**: Overall quality assessment
- **Target**: ≥ 80% for production systems
- **Note**: Can be misleading if classes imbalanced

### Precision
```
Precision = True Positives / (True Positives + False Positives)
```
- **True Positive**: Extracted correctly
- **False Positive**: Extracted incorrectly (wrong value)
- **Use for**: Measuring extraction reliability
- **Target**: ≥ 85% to avoid incorrect data

### Recall
```
Recall = True Positives / (True Positives + False Negatives)
```
- **True Positive**: Extracted correctly
- **False Negative**: Not extracted (missing)
- **Use for**: Measuring extraction completeness
- **Target**: ≥ 75% to minimize missing data

### F1 Score
```
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```
- **Use for**: Balanced quality metric
- **Target**: ≥ 80% for good balance
- **Note**: Harmonic mean penalizes extreme imbalance

## Common Issues & Solutions

### Issue: Low Accuracy (<60%)
**Symptoms**: Many incorrect extractions
**Causes**:
- Insufficient training examples
- Poor prompt engineering
- Low-quality source documents
- Model hallucination

**Solutions**:
1. Review failed extractions: `field_metrics[field].incorrect`
2. Check confidence calibration (overconfident?)
3. Improve prompts with better examples
4. Enable strict source validation (Todo 5)
5. Increase refinement rounds

### Issue: Poor Confidence Calibration
**Symptoms**: Confidence doesn't match accuracy
**Causes**:
- LLM confidence not calibrated
- Heuristic confidence too high
- Web search confidence inconsistent

**Solutions**:
1. Adjust confidence thresholds in config
2. Apply confidence penalties for missing sources
3. Calibrate heuristic confidence scores
4. Use confidence averaging across passes

### Issue: Low Recall (<70%)
**Symptoms**: Many missing extractions
**Causes**:
- Fields not present in documents
- Extraction patterns too specific
- Confidence threshold too high

**Solutions**:
1. Lower `CONFIDENCE_THRESHOLD_LOW` in config
2. Add fallback patterns for edge cases
3. Enable online enrichment for missing fields
4. Expand heuristic patterns

### Issue: High Precision but Low Recall
**Symptoms**: Few errors but many missing values
**Interpretation**: System is conservative (good!) but incomplete
**Solutions**:
1. Add more extraction passes
2. Lower confidence thresholds slightly
3. Expand query variants in FieldRetriever
4. Enable web crawling for missing fields

### Issue: High Recall but Low Precision
**Symptoms**: Few missing but many errors
**Interpretation**: System is aggressive (dangerous!)
**Solutions**:
1. Raise confidence thresholds
2. Enable strict source validation
3. Improve validation schemas
4. Add multi-pass refinement

## Best Practices

### 1. Ground Truth Quality
- **Size**: Minimum 20-30 documents for reliable metrics
- **Diversity**: Include easy, medium, hard examples
- **Accuracy**: Double-check ground truth values
- **Completeness**: Include all fields you care about

### 2. Iterative Improvement
1. Establish baseline metrics
2. Make targeted improvements (one at a time)
3. Re-evaluate after each change
4. Track metrics over time

### 3. Field-Specific Analysis
- Identify worst-performing fields first
- Focus improvements on high-impact fields
- Accept lower accuracy for optional fields
- Consider field-specific thresholds

### 4. Confidence Calibration
- Monitor calibration after major changes
- Adjust thresholds if calibration degrades
- Use calibration to guide threshold tuning
- Consider confidence penalties for uncertain sources

### 5. Continuous Evaluation
- Run evaluation on every commit (CI/CD)
- Set minimum accuracy thresholds
- Track metric trends over time
- Maintain separate test/validation sets

## Example Workflow

```bash
# 1. Initial baseline
python -m src.evaluation.evaluate_extraction --gt data/ground_truth.json
# Result: 65% accuracy

# 2. Enable web crawling (Todo 4)
# Re-evaluate
python -m src.evaluation.evaluate_extraction --gt data/ground_truth.json
# Result: 72% accuracy (+7%)

# 3. Add source validation (Todo 5)
# Re-evaluate
python -m src.evaluation.evaluate_extraction --gt data/ground_truth.json
# Result: 78% accuracy (+6%)

# 4. Tune confidence thresholds
# Edit config: CONFIDENCE_THRESHOLD_LOW = 0.55
# Re-evaluate
python -m src.evaluation.evaluate_extraction --gt data/ground_truth.json
# Result: 83% accuracy (+5%) ✓ Target reached!

# 5. Save final report
python -m src.evaluation.evaluate_extraction --gt data/ground_truth.json --output final_report.json
```

## Troubleshooting

**"No ground truth data loaded"**
- Check file path is correct
- Verify JSON is valid (no syntax errors)
- Ensure file has read permissions

**"No data found for [field]"**
- Ground truth doesn't include that field
- No documents in database match ground truth
- Check document filename matches exactly

**"Database not found"**
- Run `main.py` to process documents first
- Check `--db-path` argument is correct
- Verify database file exists and has data

**Metrics are 0% across the board**
- Document filenames don't match between DB and ground truth
- Database is empty or documents not processed
- Field names don't match exactly (case-sensitive)

## Advanced Features

### Custom Metrics
Extend `EvaluationMetrics` class to add custom metrics:

```python
class CustomEvaluator(EvaluationMetrics):
    def calculate_avg_processing_time(self) -> float:
        # Your custom metric implementation
        pass
```

### Confidence Recalibration
Use calibration data to adjust confidence scores:

```python
report = evaluator.generate_report()
calibration_map = {
    bin.range_min: bin.actual_accuracy
    for bin in report.confidence_calibration
}
# Apply corrections to confidence scores
```

### Batch Evaluation
Evaluate multiple ground truth sets:

```python
for gt_file in Path("data/ground_truth/").glob("*.json"):
    gt = GroundTruthLoader(gt_file)
    report = evaluator.generate_report()
    save_report_json(report, f"reports/{gt_file.stem}.json")
```

## Related Documentation

- **QUICK_REFERENCE.md**: General usage guide
- **TESTING_GUIDE.md**: Unit test documentation
- **TODO_5_SOURCE_CITATION_SUMMARY.md**: Source validation details
- **config.py**: Confidence threshold configuration

## Status
✅ **IMPLEMENTED** - Full evaluation system operational
