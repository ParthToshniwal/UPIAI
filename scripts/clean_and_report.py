"""
Executes DMart dataset cleaning and PDF report compilation.
"""

import os
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

from ai.data.cleaner import DMartDataCleaner
from ai.data.pdf_reporter import DMartPDFReporter

raw_path = "C:/dataset/DMart_sample_data.csv"
cleaned_path = os.path.join(root, "data", "processed", "DMart_cleaned_dataset.csv")
pdf_path = os.path.join(root, "data", "processed", "DMart_Data_Cleaning_Report.pdf")

print("=" * 65)
print("[*] Starting DMart Dataset Cleaning Pipeline...")
print(f"[*] Raw Dataset Input: {raw_path}")
print(f"[*] Cleaned Dataset Output: {cleaned_path}")
print(f"[*] PDF Report Output: {pdf_path}")
print("=" * 65)

summary = DMartDataCleaner.clean_dataset(raw_path, cleaned_path)
print(f"[OK] Cleaning completed in {summary['execution_time_seconds']} seconds!")
print(f"[OK] Cleaned Records: {summary['cleaned_file']['row_count']:,}")
print(f"[OK] Cleaned File Size: {summary['cleaned_file']['file_size_mb']} MB")
print(f"[OK] Total Gross Revenue: Rs. {summary['business_kpis']['total_gross_revenue']:,.2f}")
print(f"[OK] Total Gross Profit:  Rs. {summary['business_kpis']['total_gross_profit']:,.2f}")

print("\n[*] Compiling Executive PDF Audit Report...")
pdf_file = DMartPDFReporter.generate_pdf_report(summary, pdf_path)
pdf_size_kb = round(os.path.getsize(pdf_file) / 1024, 1)
print(f"[OK] PDF Report successfully generated: {pdf_file} ({pdf_size_kb} KB)")
print("=" * 65)
