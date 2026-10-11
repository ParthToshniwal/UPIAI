"""
Executes Weekly Aggregation and PDF Report Generation.
"""

import os
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

from ai.data.weekly_reporter import DMartWeeklyReporter

cleaned_path = os.path.join(root, "data", "processed", "DMart_cleaned_dataset.csv")
weekly_csv = os.path.join(root, "data", "processed", "DMart_weekly_summary.csv")
cat_weekly_csv = os.path.join(root, "data", "processed", "DMart_weekly_category_summary.csv")
pdf_path = os.path.join(root, "data", "processed", "DMart_Weekly_Summary_Report.pdf")

print("=" * 65)
print("[*] Generating DMart Weekly Aggregations & Reports...")
w_df, c_df, meta = DMartWeeklyReporter.compute_weekly_aggregations(cleaned_path, weekly_csv, cat_weekly_csv)
print(f"[OK] Aggregated {len(w_df)} calendar weeks in {meta['execution_time_seconds']}s")
print(f"[OK] Saved Weekly CSV: {weekly_csv}")
print(f"[OK] Saved Category Weekly CSV: {cat_weekly_csv}")
print(f"[OK] Average Weekly Revenue: Rs. {meta['average_weekly_revenue']:,.2f}")
print(f"[OK] Average Weekly Profit:  Rs. {meta['average_weekly_profit']:,.2f}")

print("\n[*] Compiling Weekly Executive PDF Report...")
pdf_file = DMartWeeklyReporter.generate_pdf_report(w_df, c_df, meta, pdf_path)
pdf_kb = round(os.path.getsize(pdf_file) / 1024, 1)
print(f"[OK] Generated Weekly PDF Report: {pdf_file} ({pdf_kb} KB)")
print("=" * 65)
