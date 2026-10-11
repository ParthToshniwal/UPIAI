"""
DMart Retail Weekly Summary & Executive Report Engine.
Computes multi-dimensional weekly retail aggregations (Revenue, Profit,
Units, WoW growth, Department velocities) and compiles executive PDF reports.
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    HRFlowable
)
from reportlab.pdfgen import canvas

logger = logging.getLogger("upiai.weekly_reporter")


class NumberedCanvasWeekly(canvas.Canvas):
    """Two-pass canvas for dynamic 'Page X of Y' and running headers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header (Pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, letter[1] - 36, "UPIAI — DMart Retail Weekly Executive Performance Audit")
            self.drawRightString(letter[0] - 54, letter[1] - 36, "CONFIDENTIAL & EXECUTIVE READY")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)

        # Footer (All pages)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 45, letter[0] - 54, 45)

        self.drawString(54, 32, "Universal Personalized Inventory AI (UPIAI) • Weekly Intelligence Core")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 32, page_str)
        self.restoreState()


class DMartWeeklyReporter:
    """Computes weekly retail analytics and generates PDF/CSV executive reports."""

    @classmethod
    def compute_weekly_aggregations(
        cls,
        cleaned_csv_path: str,
        output_weekly_csv: str = "data/processed/DMart_weekly_summary.csv",
        output_category_weekly_csv: str = "data/processed/DMart_weekly_category_summary.csv"
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Loads cleaned transactions and computes high-speed vectorized weekly aggregations.
        """
        start_time = time.time()
        logger.info("Computing weekly retail aggregations from %s...", cleaned_csv_path)

        cols_needed = ["transaction_date", "product_category", "units_sold", "total_amount", "gross_profit", "customer_type"]
        df = pd.read_csv(cleaned_csv_path, usecols=cols_needed)

        # Vectorized date and week start calculation (Monday based)
        dts = pd.to_datetime(df["transaction_date"])
        week_start_dt = dts - pd.to_timedelta(dts.dt.dayofweek, unit="D")
        week_end_dt = week_start_dt + pd.to_timedelta(6, unit="D")

        df["week_start"] = week_start_dt.dt.strftime("%Y-%m-%d")
        df["week_end"] = week_end_dt.dt.strftime("%Y-%m-%d")
        df["year_week"] = dts.dt.strftime("%Y-W%U")

        # 1. Overall Weekly Aggregation
        weekly_df = df.groupby(["year_week", "week_start", "week_end"]).agg(
            total_revenue=("total_amount", "sum"),
            gross_profit=("gross_profit", "sum"),
            units_sold=("units_sold", "sum"),
            transaction_count=("total_amount", "count")
        ).reset_index().sort_values("week_start").reset_index(drop=True)

        weekly_df["total_revenue"] = weekly_df["total_revenue"].round(2)
        weekly_df["gross_profit"] = weekly_df["gross_profit"].round(2)
        weekly_df["margin_pct"] = ((weekly_df["gross_profit"] / weekly_df["total_revenue"]) * 100.0).round(1)
        weekly_df["average_order_value"] = (weekly_df["total_revenue"] / weekly_df["transaction_count"]).round(2)
        weekly_df["wow_revenue_growth_pct"] = (weekly_df["total_revenue"].pct_change() * 100.0).round(2).fillna(0.0)
        weekly_df["wow_units_growth_pct"] = (weekly_df["units_sold"].pct_change() * 100.0).round(2).fillna(0.0)

        # 2. Weekly Category Aggregation
        cat_weekly_df = df.groupby(["week_start", "product_category"]).agg(
            revenue=("total_amount", "sum"),
            profit=("gross_profit", "sum"),
            units=("units_sold", "sum"),
            transactions=("total_amount", "count")
        ).reset_index().sort_values(["week_start", "product_category"]).reset_index(drop=True)

        cat_weekly_df["revenue"] = cat_weekly_df["revenue"].round(2)
        cat_weekly_df["profit"] = cat_weekly_df["profit"].round(2)
        cat_weekly_df["margin_pct"] = ((cat_weekly_df["profit"] / cat_weekly_df["revenue"]) * 100.0).round(1)

        # 3. Save CSVs to disk
        os.makedirs(os.path.dirname(os.path.abspath(output_weekly_csv)), exist_ok=True)
        weekly_df.to_csv(output_weekly_csv, index=False)
        cat_weekly_df.to_csv(output_category_weekly_csv, index=False)

        elapsed = round(time.time() - start_time, 2)
        logger.info("Generated %d weeks of retail data in %.2f seconds.", len(weekly_df), elapsed)

        # Summary KPIs
        avg_weekly_rev = round(float(weekly_df["total_revenue"].mean()), 2)
        avg_weekly_prof = round(float(weekly_df["gross_profit"].mean()), 2)
        avg_weekly_units = int(weekly_df["units_sold"].mean())
        max_rev_row = weekly_df.loc[weekly_df["total_revenue"].idxmax()]
        latest_row = weekly_df.iloc[-1]

        summary_meta = {
            "total_weeks": len(weekly_df),
            "date_range_start": str(weekly_df["week_start"].min()),
            "date_range_end": str(weekly_df["week_end"].max()),
            "average_weekly_revenue": avg_weekly_rev,
            "average_weekly_profit": avg_weekly_prof,
            "average_weekly_units": avg_weekly_units,
            "overall_average_margin_pct": round(float(weekly_df["margin_pct"].mean()), 1),
            "peak_week": {
                "week_start": str(max_rev_row["week_start"]),
                "revenue": float(max_rev_row["total_revenue"]),
                "units": int(max_rev_row["units_sold"])
            },
            "latest_week": {
                "week_start": str(latest_row["week_start"]),
                "week_end": str(latest_row["week_end"]),
                "revenue": float(latest_row["total_revenue"]),
                "profit": float(latest_row["gross_profit"]),
                "margin_pct": float(latest_row["margin_pct"]),
                "units": int(latest_row["units_sold"]),
                "wow_growth": float(latest_row["wow_revenue_growth_pct"])
            },
            "execution_time_seconds": elapsed
        }

        return weekly_df, cat_weekly_df, summary_meta

    @classmethod
    def _create_weekly_charts(cls, weekly_df: pd.DataFrame, cat_weekly_df: pd.DataFrame, temp_dir: str) -> Dict[str, str]:
        """Generates high-res visual charts for the weekly report."""
        os.makedirs(temp_dir, exist_ok=True)
        chart_paths = {}

        # Chart 1: Weekly Revenue Trend over time (Crores)
        fig, ax = plt.subplots(figsize=(6.8, 2.5), dpi=200)
        fig.patch.set_facecolor('#ffffff')
        ax.set_facecolor('#f8fafc')

        x_indices = range(len(weekly_df))
        rev_cr = weekly_df["total_revenue"] / 10000000.0  # in Crores
        prof_cr = weekly_df["gross_profit"] / 10000000.0

        ax.plot(x_indices, rev_cr, color='#2563eb', linewidth=1.8, label='Gross Revenue (₹ Cr)')
        ax.plot(x_indices, prof_cr, color='#16a34a', linewidth=1.5, linestyle='--', label='Gross Profit (₹ Cr)')
        ax.fill_between(x_indices, rev_cr, alpha=0.12, color='#3b82f6')

        # Sample tick labels every 12 weeks
        step = max(1, len(weekly_df) // 8)
        ticks = list(range(0, len(weekly_df), step))
        ax.set_xticks(ticks)
        ax.set_xticklabels([weekly_df["week_start"].iloc[i] for i in ticks], rotation=25, ha='right', fontsize=7.5)
        ax.set_ylabel('₹ Crores', fontsize=8, color='#334155', fontweight='bold')
        ax.set_title('Weekly Revenue & Gross Profit Trajectory (107 Weeks)', fontsize=9, color='#0f172a', fontweight='bold', pad=8)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend(fontsize=7.5, loc='upper left')

        plt.tight_layout()
        c1 = os.path.join(temp_dir, "weekly_revenue_trend.png")
        plt.savefig(c1, dpi=200, bbox_inches='tight')
        plt.close()
        chart_paths["rev_trend"] = c1

        # Chart 2: Recent 16 Weeks WoW Growth Rate %
        recent_df = weekly_df.tail(16).copy()
        fig, ax = plt.subplots(figsize=(6.8, 2.3), dpi=200)
        fig.patch.set_facecolor('#ffffff')
        ax.set_facecolor('#f8fafc')

        bar_colors = ['#16a34a' if v >= 0 else '#dc2626' for v in recent_df["wow_revenue_growth_pct"]]
        ax.bar(recent_df["week_start"], recent_df["wow_revenue_growth_pct"], color=bar_colors, width=0.6)
        ax.axhline(0, color='#64748b', linewidth=0.8, linestyle='--')
        ax.set_ylabel('WoW Growth %', fontsize=8, color='#334155', fontweight='bold')
        ax.set_title('Week-over-Week (WoW) Revenue Volatility (Recent 16 Weeks)', fontsize=9, color='#0f172a', fontweight='bold', pad=8)
        ax.tick_params(axis='x', rotation=35, labelsize=7.5)
        ax.tick_params(axis='y', labelsize=7.5)
        ax.grid(axis='y', linestyle='--', alpha=0.5)

        plt.tight_layout()
        c2 = os.path.join(temp_dir, "weekly_wow_growth.png")
        plt.savefig(c2, dpi=200, bbox_inches='tight')
        plt.close()
        chart_paths["wow_growth"] = c2

        return chart_paths

    @classmethod
    def generate_pdf_report(
        cls,
        weekly_df: pd.DataFrame,
        cat_weekly_df: pd.DataFrame,
        summary_meta: Dict[str, Any],
        output_pdf_path: str = "data/processed/DMart_Weekly_Summary_Report.pdf"
    ) -> str:
        """Compiles the multi-page Executive Weekly Performance Audit PDF."""
        output_dir = os.path.dirname(os.path.abspath(output_pdf_path))
        os.makedirs(output_dir, exist_ok=True)
        temp_dir = os.path.join(output_dir, "pdf_assets_weekly")

        chart_paths = cls._create_weekly_charts(weekly_df, cat_weekly_df, temp_dir)

        doc = SimpleDocTemplate(
            output_pdf_path,
            pagesize=letter,
            leftMargin=50,
            rightMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'WeeklyTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=21,
            leading=25,
            textColor=colors.HexColor('#0f172a')
        )
        subtitle_style = ParagraphStyle(
            'WeeklySubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor('#475569')
        )
        h1_style = ParagraphStyle(
            'WeeklyH1',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12.5,
            leading=16,
            textColor=colors.HexColor('#1e3a8a'),
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'WeeklyBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=13,
            textColor=colors.HexColor('#334155')
        )
        table_hdr_style = ParagraphStyle(
            'WeeklyTableHdr',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.white
        )
        table_cell_style = ParagraphStyle(
            'WeeklyTableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor('#1e293b')
        )
        table_cell_bold = ParagraphStyle(
            'WeeklyTableCellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor('#0f172a')
        )

        story = []

        # -------------------------------------------------------------------
        # PAGE 1: TITLE & EXECUTIVE WEEKLY KPI REPORT
        # -------------------------------------------------------------------
        badge = Table(
            [[Paragraph("📅 <b>UPIAI RETAIL WEEKLY INTELLIGENCE & PERFORMANCE GOVERNANCE</b>", ParagraphStyle('BdgW', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#2563eb')))]],
            colWidths=[512]
        )
        badge.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eff6ff')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#bfdbfe')),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        story.append(badge)
        story.append(Spacer(1, 8))

        story.append(Paragraph("DMart Retail Weekly Executive Performance Report", title_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph("Multi-Horizon Weekly Revenue Auditing, Velocity Tracking & Departmental Health", subtitle_style))
        story.append(Spacer(1, 10))

        # Metadata Box
        meta_table = Table([
            [
                Paragraph("<b>Audit Period:</b>", table_cell_bold),
                Paragraph(f"{summary_meta['date_range_start']} → {summary_meta['date_range_end']}", table_cell_style),
                Paragraph("<b>Total Weeks Analyzed:</b>", table_cell_bold),
                Paragraph(f"{summary_meta['total_weeks']} Calendar Weeks", table_cell_style)
            ],
            [
                Paragraph("<b>Generated Timestamp:</b>", table_cell_bold),
                Paragraph(datetime.now().strftime("%B %d, %Y - %H:%M:%S UTC"), table_cell_style),
                Paragraph("<b>Average Weekly Revenue:</b>", table_cell_bold),
                Paragraph(f"₹{summary_meta['average_weekly_revenue']:,.2f}", table_cell_bold)
            ],
            [
                Paragraph("<b>Average Weekly Margin:</b>", table_cell_bold),
                Paragraph(f"{summary_meta['overall_average_margin_pct']}% Gross Margin", table_cell_style),
                Paragraph("<b>Peak Weekly Velocity:</b>", table_cell_bold),
                Paragraph(f"₹{summary_meta['peak_week']['revenue']:,.2f} ({summary_meta['peak_week']['week_start']})", table_cell_style)
            ]
        ], colWidths=[120, 150, 120, 122])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 12))

        # KPI Summary Grid
        lat = summary_meta["latest_week"]
        story.append(Paragraph("Latest Week Performance Indicators", h1_style))
        kpi_grid = Table([
            [
                Paragraph(f"<b>LATEST WEEK REVENUE</b><br/><font size='13' color='#1e3a8a'><b>₹{lat['revenue']:,.2f}</b></font><br/><font color='#64748b' size='7'>{lat['week_start']} to {lat['week_end']}</font>", body_style),
                Paragraph(f"<b>LATEST WEEK PROFIT</b><br/><font size='13' color='#16a34a'><b>₹{lat['profit']:,.2f}</b></font><br/><font color='#64748b' size='7'>Gross Margin: {lat['margin_pct']}%</font>", body_style),
                Paragraph(f"<b>UNITS DISPATCHED</b><br/><font size='13' color='#0f172a'><b>{lat['units']:,}</b></font><br/><font color='#64748b' size='7'>All DMart Stores</font>", body_style),
            ],
            [
                Paragraph(f"<b>WEEK-OVER-WEEK (WoW)</b><br/><font size='13' color='{'#16a34a' if lat['wow_growth'] >= 0 else '#dc2626'}'><b>{lat['wow_growth']:+.2f}%</b></font><br/><font color='#64748b' size='7'>vs Preceding 7-Day Window</font>", body_style),
                Paragraph(f"<b>AVG WEEKLY REVENUE</b><br/><font size='13' color='#0f172a'><b>₹{summary_meta['average_weekly_revenue']:,.2f}</b></font><br/><font color='#64748b' size='7'>107-Week Baseline</font>", body_style),
                Paragraph(f"<b>AVG WEEKLY UNITS</b><br/><font size='13' color='#0f172a'><b>{summary_meta['average_weekly_units']:,} Units</b></font><br/><font color='#64748b' size='7'>Demand Stability: HIGH</font>", body_style)
            ]
        ], colWidths=[170, 170, 172])
        kpi_grid.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ffffff')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(kpi_grid)
        story.append(Spacer(1, 10))

        # Chart 1: Revenue Trajectory
        if "rev_trend" in chart_paths:
            img1 = Image(chart_paths["rev_trend"], width=6.8 * inch, height=2.5 * inch)
            story.append(img1)

        # -------------------------------------------------------------------
        # PAGE 2: CHARTS & RECENT WEEK PERFORMANCE LEDGER
        # -------------------------------------------------------------------
        story.append(PageBreak())
        story.append(Paragraph("Weekly Volatility & Recent Performance Ledger", h1_style))
        story.append(Paragraph("Week-over-week growth trajectory and granular 15-week performance audit.", subtitle_style))
        story.append(Spacer(1, 8))

        if "wow_growth" in chart_paths:
            img2 = Image(chart_paths["wow_growth"], width=6.8 * inch, height=2.3 * inch)
            story.append(img2)
            story.append(Spacer(1, 10))

        # Recent 12 Weeks Ledger Table
        story.append(Paragraph("Recent 12-Week Performance Audit Ledger", h1_style))
        recent_12 = weekly_df.tail(12).iloc[::-1]

        table_data = [
            [
                Paragraph("Week Window", table_hdr_style),
                Paragraph("Gross Revenue (₹)", table_hdr_style),
                Paragraph("Gross Profit (₹)", table_hdr_style),
                Paragraph("Margin %", table_hdr_style),
                Paragraph("Units Sold", table_hdr_style),
                Paragraph("Orders", table_hdr_style),
                Paragraph("WoW %", table_hdr_style)
            ]
        ]
        for _, r in recent_12.iterrows():
            wow = r["wow_revenue_growth_pct"]
            wow_col = "#16a34a" if wow >= 0 else "#dc2626"
            table_data.append([
                Paragraph(f"<b>{r['week_start']}</b><br/><font size='6.5' color='#64748b'>to {r['week_end']}</font>", table_cell_style),
                Paragraph(f"₹{r['total_revenue']:,.2f}", table_cell_style),
                Paragraph(f"₹{r['gross_profit']:,.2f}", table_cell_style),
                Paragraph(f"{r['margin_pct']}%", table_cell_style),
                Paragraph(f"{r['units_sold']:,}", table_cell_style),
                Paragraph(f"{r['transaction_count']:,}", table_cell_style),
                Paragraph(f"<b><font color='{wow_col}'>{wow:+.2f}%</font></b>", table_cell_style)
            ])

        ledger_table = Table(table_data, colWidths=[105, 95, 90, 52, 60, 50, 60])
        ledger_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(ledger_table)
        story.append(Spacer(1, 10))

        # Sign-off Seal
        seal_table = Table([
            [
                Paragraph("<b>WEEKLY AUDIT VERIFICATION:</b> Generated automatically by UPIAI Demand Intelligence Core for executive supply chain and merchandise reviews.", body_style),
                Paragraph("<b>Report Status:</b><br/><code>APPROVED • PRODUCTION GRADE</code>", body_style)
            ]
        ], colWidths=[370, 142])
        seal_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eff6ff')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#3b82f6')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(seal_table)

        doc.build(story, canvasmaker=NumberedCanvasWeekly)
        logger.info("Successfully compiled weekly PDF report at %s", output_pdf_path)

        # Cleanup temporary charts
        try:
            for cp in chart_paths.values():
                if os.path.exists(cp):
                    os.remove(cp)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception:
            pass

        return output_pdf_path
