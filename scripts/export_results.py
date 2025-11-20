"""CLI to export processed results to CSV or Excel.

Usage:
  python scripts/export_results.py --format csv --output data/results.csv --limit 100
  python scripts/export_results.py --format excel --output data/results.xlsx
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.export.exporters import export_to_csv, export_to_excel
from src.utils.config import DATA_DIR

def main() -> None:
    parser = argparse.ArgumentParser(description="Export processed FDS results to CSV/Excel.")
    parser.add_argument(
        "--format",
        choices=["csv", "excel"],
        default="csv",
        help="Output format (csv or excel). Default: csv",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path. Default: data/results.csv or data/results.xlsx",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit of rows to export.",
    )
    args = parser.parse_args()

    default = Path(DATA_DIR) / ("results.xlsx" if args.format == "excel" else "results.csv")
    out_path = Path(args.output) if args.output else default
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "csv":
        export_to_csv(out_path, limit=args.limit)
    else:
        export_to_excel(out_path, limit=args.limit)

    print(f"Export complete: {out_path}")

if __name__ == "__main__":
    main()
