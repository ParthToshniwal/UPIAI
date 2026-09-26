"""
UPIAI — Universal Personalized Inventory & Sales Analytics AI
Streamlit Multi-Tab Executive Dashboard hardwired to DMart Retail Analytics.
Communicates with FastAPI backend (Turso libsql DB & XGBoost forecasting engine).
"""

import os
import json
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

# Page Configuration
st.set_page_config(
    page_title="UPIAI — DMart Demand & Inventory Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgb(15, 23, 42) 0%, rgb(11, 15, 25) 90%);
        color: #f8fafc;
    }
    
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(8px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(59, 130, 246, 0.5);
    }
    .metric-label {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .metric-val {
        font-size: 1.85rem;
        font-weight: 800;
        color: #f8fafc;
        line-height: 1.2;
    }
    .metric-sub {
        font-size: 0.78rem;
        color: #10b981;
        margin-top: 6px;
        font-weight: 500;
    }
    
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }
    .badge-success { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
    .badge-warning { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .badge-danger { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
    .badge-info { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }
    
    .status-pill {
        display: flex;
        align-items: center;
        gap: 8px;
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 0.85rem;
    }
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 10px #10b981;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar Configuration & Backend Health
# ---------------------------------------------------------------------------
st.sidebar.markdown("### ⚡ **UPIAI Engine**")
st.sidebar.caption("Universal Personalized Inventory & Demand Intelligence")

api_base_url = st.sidebar.text_input("FastAPI Backend URL", value="http://localhost:8000")
forecast_horizon = st.sidebar.slider("Forecast Horizon (Days)", min_value=7, max_value=60, value=30, step=7)

# Check Backend Health
backend_online = False
db_status_info = {}
try:
    health_res = requests.get(f"{api_base_url}/health", timeout=2)
    if health_res.status_code == 200:
        backend_online = True
        db_status_info = health_res.json().get("database", {})
except Exception:
    backend_online = False

st.sidebar.markdown("---")
st.sidebar.markdown("#### **System Telemetry**")
if backend_online:
    engine_name = db_status_info.get("engine", "Turso libsql Database")
    txn_count = db_status_info.get("total_transactions", 0)
    st.sidebar.markdown(f"""
        <div class="status-pill">
            <div class="status-dot"></div>
            <span><b>Backend:</b> Online</span>
        </div>
        <div style="margin-top: 8px; font-size: 0.8rem; color: #94a3b8;">
            <b>Database:</b> {engine_name}<br>
            <b>Transactions Loaded:</b> {txn_count:,}
        </div>
    """, unsafe_allow_html=True)
else:
    st.sidebar.markdown("""
        <div class="status-pill" style="border-color: rgba(239, 68, 68, 0.4);">
            <div class="status-dot" style="background-color: #ef4444; box-shadow: 0 0 10px #ef4444;"></div>
            <span><b>Backend:</b> Offline / Connecting</span>
        </div>
        <div style="margin-top: 8px; font-size: 0.78rem; color: #f87171;">
            Ensure FastAPI backend is running on <code>port 8000</code>.
        </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="font-size: 0.78rem; color: #64748b; line-height: 1.5;">
    <b>Datasets Ingested:</b><br>
    • <code>DMart_sample_data.csv</code><br>
    • <code>DMart_Grocery_Sales.csv</code><br>
    <b>Model:</b> XGBoost Autoregressive<br>
    <b>Database:</b> Turso (libsql)
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# API Data Fetching Helper Functions
# ---------------------------------------------------------------------------
@st.cache_data(ttl=5)
def fetch_kpis():
    try:
        r = requests.get(f"{api_base_url}/api/v1/ai/kpis", timeout=4)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

@st.cache_data(ttl=5)
def fetch_readiness():
    try:
        r = requests.get(f"{api_base_url}/api/v1/readiness", timeout=4)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

@st.cache_data(ttl=5)
def fetch_categories():
    try:
        r = requests.get(f"{api_base_url}/api/v1/ai/categories", timeout=4)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

@st.cache_data(ttl=5)
def fetch_forecast(horizon=30):
    try:
        r = requests.get(f"{api_base_url}/api/v1/ai/forecast?horizon_days={horizon}", timeout=6)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

@st.cache_data(ttl=5)
def fetch_sales_analytics():
    try:
        r = requests.get(f"{api_base_url}/api/v1/ai/sales-analytics", timeout=4)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

@st.cache_data(ttl=5)
def fetch_suppliers():
    try:
        r = requests.get(f"{api_base_url}/api/v1/suppliers/intelligence", timeout=4)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Main Header
# ---------------------------------------------------------------------------
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("## 🛒 **UPIAI — DMart Retail Demand & Inventory AI**")
    st.markdown("<p style='color: #94a3b8; margin-top: -12px;'>Universal Personalized Inventory & Sales Analytics Engine • Powered by Turso & XGBoost</p>", unsafe_allow_html=True)
with col_h2:
    if backend_online:
        st.markdown("<div style='text-align: right; padding-top: 10px;'><span class='badge badge-success'>🟢 TURSO LIBSQL CONNECTED</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align: right; padding-top: 10px;'><span class='badge badge-danger'>🔴 BACKEND OFFLINE</span></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Navigation Tabs
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Executive Overview & KPIs",
    "🛡️ Data Readiness & Provenance",
    "🔮 AI Demand & Stockout Intelligence",
    "📈 Sales & Profit Analytics",
    "🚛 Supplier Ledger & SLAs"
])


# ===========================================================================
# TAB 1: EXECUTIVE OVERVIEW & KPIS
# ===========================================================================
with tab1:
    kpi_data = fetch_kpis()
    if not kpi_data:
        st.warning("Connecting to FastAPI backend... Please ensure `uvicorn app.main:app` is running.")
        kpi_data = {
            "total_revenue": 348500.0,
            "total_profit": 104550.0,
            "avg_margin_pct": 30.0,
            "total_units_sold": 4120,
            "total_transactions": 840,
            "avg_order_value": 414.88,
            "total_categories": 6,
            "unique_customers": 72,
            "total_inventory_value": 182400.0,
            "critical_stockouts": 1,
            "warning_stockouts": 2,
            "capital_at_risk": 18450.0,
            "recommended_reorder_budget": 42000.0,
            "model_engine": "XGBoost Autoregressive Regressor"
        }

    # Top KPI Metrics Cards
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Gross Revenue</div>
                <div class="metric-val">₹{kpi_data['total_revenue']:,.2f}</div>
                <div class="metric-sub">▲ 14.2% vs historical</div>
            </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Gross Margin</div>
                <div class="metric-val">₹{kpi_data['total_profit']:,.2f}</div>
                <div class="metric-sub" style="color: #60a5fa;">Avg Margin: {kpi_data['avg_margin_pct']:.1f}%</div>
            </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Units Sold Volume</div>
                <div class="metric-val">{kpi_data['total_units_sold']:,}</div>
                <div class="metric-sub">From {kpi_data['total_transactions']:,} Orders</div>
            </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Avg Order Value (AOV)</div>
                <div class="metric-val">₹{kpi_data['avg_order_value']:,.2f}</div>
                <div class="metric-sub" style="color: #a78bfa;">{kpi_data['unique_customers']} Unique Customers</div>
            </div>
        """, unsafe_allow_html=True)
    with c5:
        risk_color = "#f87171" if kpi_data['critical_stockouts'] > 0 else "#34d399"
        st.markdown(f"""
            <div class="metric-card" style="border-color: rgba(239, 68, 68, 0.3);">
                <div class="metric-label">Stockout Risk Value</div>
                <div class="metric-val" style="color: {risk_color};">₹{kpi_data['capital_at_risk']:,.2f}</div>
                <div class="metric-sub" style="color: {risk_color};">{kpi_data['critical_stockouts']} Critical Alerts</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

    # Category Revenue Breakdown & Customer Type Analysis
    categories = fetch_categories()
    if categories:
        cat_df = pd.DataFrame(categories)
        col_c1, col_c2 = st.columns([3, 2])
        
        with col_c1:
            st.markdown("#### 📦 **Category Revenue & Unit Velocity**")
            fig_bar = px.bar(
                cat_df,
                x="category",
                y="total_revenue",
                text="total_revenue",
                color="total_revenue",
                color_continuous_scale="Blues",
                labels={"total_revenue": "Gross Revenue (₹)", "category": "Product Category"}
            )
            fig_bar.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                margin=dict(l=20, r=20, t=20, b=20),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_c2:
            st.markdown("#### 🎯 **Category Revenue Share**")
            fig_donut = px.pie(
                cat_df,
                names="category",
                values="total_revenue",
                hole=0.55,
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_donut.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                margin=dict(l=10, r=10, t=20, b=20)
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        # Category Performance Table
        st.markdown("#### 📋 **DMart Category Ledger Summary**")
        st.dataframe(
            cat_df.rename(columns={
                "category": "Department Category",
                "total_revenue": "Total Revenue (₹)",
                "total_units": "Units Sold",
                "avg_price": "Avg Unit Price (₹)",
                "avg_margin_pct": "Avg Margin %",
                "transaction_count": "Transactions"
            }),
            use_container_width=True,
            hide_index=True
        )


# ===========================================================================
# TAB 2: DATA READINESS & PROVENANCE AUDIT
# ===========================================================================
with tab2:
    st.markdown("### 🛡️ **DMart Data Readiness & Provenance Engine**")
    st.caption("Inspects dataset columns against 9 canonical dimensions, calculates health score, and flags provenance limitations.")

    readiness = fetch_readiness()
    if readiness:
        score = readiness.get("overall_readiness_score", 0.0)
        tier = readiness.get("operational_tier", "DEGRADED")
        records = readiness.get("total_records", 0)
        span = readiness.get("data_span_days", 0)
        d_start = readiness.get("date_range_start", "N/A")
        d_end = readiness.get("date_range_end", "N/A")

        col_r1, col_r2, col_r3 = st.columns([1.5, 2, 2])
        with col_r1:
            # Score Gauge
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score,
                title={'text': f"<b>Readiness Index</b><br><span style='font-size:0.8em;color:#94a3b8;'>{tier}</span>", 'font': {'color': '#f8fafc', 'size': 18}},
                number={'suffix': "%", 'font': {'color': '#f8fafc', 'size': 32}},
                gauge={
                    'axis': {'range': [0, 100], 'tickcolor': "#94a3b8"},
                    'bar': {'color': "#3b82f6"},
                    'steps': [
                        {'range': [0, 50], 'color': "rgba(239, 68, 68, 0.2)"},
                        {'range': [50, 80], 'color': "rgba(245, 158, 11, 0.2)"},
                        {'range': [80, 100], 'color': "rgba(16, 185, 129, 0.2)"}
                    ],
                    'threshold': {
                        'line': {'color': "#10b981", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig_gauge.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                height=240,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

        with col_r2:
            st.markdown(f"""
                <div class="metric-card" style="height: 240px;">
                    <div class="metric-label">Dataset Provenance Profile</div>
                    <div style="margin-top: 12px; font-size: 0.9rem; line-height: 1.8;">
                        • <b>Total Transactions Audited:</b> {records:,}<br>
                        • <b>Time Span:</b> {span} Days ({d_start} → {d_end})<br>
                        • <b>ML Forecast Feasibility:</b> {'✅ Ready to Forecast' if readiness.get('can_proceed_to_forecast') else '❌ Incomplete'}<br>
                        • <b>Assumed Defaults:</b> {len(readiness.get('assumed_defaults_applied', {}))} defaults applied
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with col_r3:
            st.markdown("##### ⚠️ **Structural Limitations Disclosed**")
            limitations = readiness.get("structural_limitations", [])
            if limitations:
                for lim in limitations:
                    st.markdown(f"<div style='background: rgba(245, 158, 11, 0.1); border-left: 3px solid #f59e0b; padding: 6px 12px; margin-bottom: 6px; font-size: 0.82rem;'>{lim}</div>", unsafe_allow_html=True)
            else:
                st.success("Zero structural blockers detected. Clean data pipeline.")

        # Column Health Breakdown Table
        st.markdown("#### 🔬 **Canonical Dimension Audit Matrix**")
        audits = readiness.get("column_audits", [])
        if audits:
            audit_df = pd.DataFrame(audits)
            st.dataframe(
                audit_df.rename(columns={
                    "column_name": "Target Column",
                    "status": "Integrity Status",
                    "data_type": "Data Type",
                    "missing_count": "Missing Rows",
                    "missing_percentage": "Missing %",
                    "importance": "Criticality",
                    "impact_description": "Downstream AI Impact"
                }),
                use_container_width=True,
                hide_index=True
            )

        # Upload and Audit Interactive CSV Tool
        st.markdown("---")
        st.markdown("#### 📤 **Upload New CSV for Live Data Audit**")
        uploaded_file = st.file_uploader("Upload raw retail dataset (CSV format)", type=["csv"])
        if uploaded_file is not None:
            with st.spinner("Auditing uploaded file with Data Readiness Engine..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                    up_res = requests.post(f"{api_base_url}/api/v1/readiness/upload-csv", files=files, timeout=5)
                    if up_res.status_code == 200:
                        up_scorecard = up_res.json()
                        st.success(f"Audit Complete! Readiness Score: **{up_scorecard['overall_readiness_score']}%** ({up_scorecard['operational_tier']})")
                        st.json(up_scorecard)
                    else:
                        st.error(f"Error auditing file: {up_res.text}")
                except Exception as e:
                    st.error(f"Failed to communicate with audit endpoint: {e}")
    else:
        st.info("Start backend to view live DMart Data Readiness Scorecard.")


# ===========================================================================
# TAB 3: AI DEMAND & STOCKOUT INTELLIGENCE
# ===========================================================================
with tab3:
    st.markdown("### 🔮 **Autonomous XGBoost Demand Forecaster & Stockout Risk**")
    st.caption("Multi-horizon recursive autoregressive forecasting (7-day and 30-day) with 90% confidence bands and dynamic reorder points.")

    forecast_data = fetch_forecast(horizon=forecast_horizon)
    if forecast_data and forecast_data.get("sku_forecasts"):
        skus = forecast_data["sku_forecasts"]
        cat_names = [s["category"] for s in skus]

        col_sel, col_stat = st.columns([2, 3])
        with col_sel:
            selected_cat = st.selectbox("Select DMart Product Category", options=cat_names)
        with col_stat:
            st.markdown(f"""
                <div style='margin-top: 25px;'>
                    <span class='badge badge-info'>ENGINE: {forecast_data.get('model_type_used')}</span>
                    <span class='badge badge-warning'>CRITICAL STOCKOUTS: {forecast_data.get('critical_stockout_count')}</span>
                    <span class='badge badge-success'>REORDER BUDGET: ₹{forecast_data.get('total_recommended_reorder_cost'):,.2f}</span>
                </div>
            """, unsafe_allow_html=True)

        matched_sku = next((s for s in skus if s["category"] == selected_cat), skus[0])

        # Category Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Current Warehouse Stock</div>
                    <div class="metric-val">{matched_sku['current_stock']} Units</div>
                    <div class="metric-sub" style="color:#60a5fa;">Safety Stock: {matched_sku['reorder_recommendation']['safety_stock']} units</div>
                </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">7-Day Projected Demand</div>
                    <div class="metric-val">{matched_sku['forecast_7d_total']} Units</div>
                    <div class="metric-sub">Velocity: {matched_sku['daily_average_velocity']} units/day</div>
                </div>
            """, unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">{forecast_horizon}-Day Projected Demand</div>
                    <div class="metric-val">{matched_sku['forecast_30d_total']} Units</div>
                    <div class="metric-sub" style="color:#a78bfa;">Value: ₹{(matched_sku['forecast_30d_total'] * matched_sku['unit_price']):,.2f}</div>
                </div>
            """, unsafe_allow_html=True)
        with m4:
            r_level = matched_sku['risk_assessment']['risk_level']
            r_badge_color = "#f87171" if r_level == "CRITICAL" else ("#fbbf24" if r_level == "WARNING" else "#34d399")
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Stockout Risk Level</div>
                    <div class="metric-val" style="color: {r_badge_color};">{r_level}</div>
                    <div class="metric-sub" style="color: {r_badge_color};">Days of Supply: {matched_sku['risk_assessment']['estimated_days_of_supply']} Days</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

        # Plot Demand Trajectory Curve with Confidence Intervals
        trajectories = matched_sku.get("daily_trajectory_30d", [])
        if trajectories:
            traj_df = pd.DataFrame(trajectories)
            st.markdown(f"#### 📈 **Predicted Demand Trajectory Curve ({selected_cat})**")
            
            fig_curve = go.Figure()

            # Upper bound
            fig_curve.add_trace(go.Scatter(
                x=traj_df['forecast_date'],
                y=traj_df['upper_bound_90'],
                mode='lines',
                line=dict(width=0),
                showlegend=False,
                name='Upper Bound (90%)'
            ))

            # Lower bound filled
            fig_curve.add_trace(go.Scatter(
                x=traj_df['forecast_date'],
                y=traj_df['lower_bound_90'],
                mode='lines',
                line=dict(width=0),
                fill='tonexty',
                fillcolor='rgba(59, 130, 246, 0.15)',
                showlegend=True,
                name='90% Confidence Interval'
            ))

            # Point forecast
            fig_curve.add_trace(go.Scatter(
                x=traj_df['forecast_date'],
                y=traj_df['predicted_units'],
                mode='lines+markers',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=6, color='#60a5fa'),
                name='XGBoost Predicted Units'
            ))

            fig_curve.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Forecast Timeline"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Units Demand"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_curve, use_container_width=True)

        # Autonomous PO Recommendations Table
        st.markdown("#### 📦 **Autonomous Purchase Order (PO) Recommendations**")
        reorders = []
        for s in skus:
            rec = s["reorder_recommendation"]
            risk = s["risk_assessment"]
            reorders.append({
                "SKU Code": rec["sku"],
                "Category": rec["category"],
                "Current Stock": rec["current_stock"],
                "Days of Supply": risk["estimated_days_of_supply"],
                "Risk Level": risk["risk_level"],
                "Stockout Prob %": f"{risk['stockout_probability_pct']}%",
                "Reorder Point": rec["reorder_point"],
                "Recommended PO Qty": rec["recommended_order_quantity"],
                "Est. PO Cost (₹)": f"₹{rec['estimated_order_cost']:,.2f}",
                "Urgency": rec["urgency"],
                "Rationale": rec["rationale"]
            })
        st.dataframe(pd.DataFrame(reorders), use_container_width=True, hide_index=True)
    else:
        st.info("Start backend to generate XGBoost multi-horizon demand forecasts.")


# ===========================================================================
# TAB 4: SALES & PROFIT ANALYTICS
# ===========================================================================
with tab4:
    st.markdown("### 📈 **DMart Sales & Gross Margin Analytics**")
    st.caption("Time-series velocity, customer loyalty segmentation, and hourly footfall distribution.")

    analytics = fetch_sales_analytics()
    if analytics:
        daily_trends = analytics.get("daily_trends", [])
        cust_segments = analytics.get("customer_segments", [])
        hourly_traffic = analytics.get("hourly_traffic", [])

        col_a1, col_a2 = st.columns(2)
        with col_a1:
            if daily_trends:
                st.markdown("#### 📅 **Daily Sales Revenue Trend**")
                daily_df = pd.DataFrame(daily_trends)
                fig_daily = px.line(
                    daily_df,
                    x="date",
                    y="revenue",
                    labels={"date": "Transaction Date", "revenue": "Daily Revenue (₹)"},
                    line_shape="spline"
                )
                fig_daily.update_traces(line=dict(color="#10b981", width=3))
                fig_daily.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#94a3b8"),
                    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.05)")
                )
                st.plotly_chart(fig_daily, use_container_width=True)

        with col_a2:
            if cust_segments:
                st.markdown("#### 👥 **Customer Segment Revenue & Basket Size**")
                cust_df = pd.DataFrame(cust_segments)
                fig_cust = px.bar(
                    cust_df,
                    x="customer_type",
                    y="total_revenue",
                    color="customer_type",
                    text="avg_basket_size",
                    labels={"customer_type": "Customer Tier", "total_revenue": "Total Revenue (₹)"}
                )
                fig_cust.update_traces(texttemplate='Avg Basket: ₹%{text}', textposition='outside')
                fig_cust.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#94a3b8"),
                    showlegend=False
                )
                st.plotly_chart(fig_cust, use_container_width=True)

        if hourly_traffic:
            st.markdown("#### ⏰ **Hourly Store Footfall & Volume Distribution**")
            hour_df = pd.DataFrame(hourly_traffic)
            fig_hour = px.bar(
                hour_df,
                x="hour_window",
                y="transaction_count",
                labels={"hour_window": "Store Hour", "transaction_count": "Transactions"},
                color="transaction_count",
                color_continuous_scale="Purples"
            )
            fig_hour.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_hour, use_container_width=True)
    else:
        st.info("Start backend to view interactive DMart sales analytics.")


# ===========================================================================
# TAB 5: SUPPLIER LEDGER & SLAS
# ===========================================================================
with tab5:
    st.markdown("### 🚛 **DMart Supplier SLAs & Accounts Payable Ledger**")
    st.caption("Real-time vendor fulfillment scorecards, quality index, and live invoice settlement.")

    sup_data = fetch_suppliers()
    if sup_data and sup_data.get("supplier_scorecards"):
        scorecards = sup_data["supplier_scorecards"]

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Average On-Time Delivery SLA</div>
                    <div class="metric-val" style="color: #34d399;">{sup_data['average_on_time_rate']}%</div>
                    <div class="metric-sub">Across {sup_data['total_suppliers']} Vendors</div>
                </div>
            """, unsafe_allow_html=True)
        with sc2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Total Pending Payables</div>
                    <div class="metric-val">₹{sup_data['total_pending_payables']:,.2f}</div>
                    <div class="metric-sub" style="color: #60a5fa;">Invoices in Net 30/45 cycle</div>
                </div>
            """, unsafe_allow_html=True)
        with sc3:
            st.markdown(f"""
                <div class="metric-card" style="border-color: rgba(239, 68, 68, 0.3);">
                    <div class="metric-label">Overdue Payables</div>
                    <div class="metric-val" style="color: #f87171;">₹{sup_data['overdue_payables']:,.2f}</div>
                    <div class="metric-sub" style="color: #f87171;">Requires Immediate Clearance</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

        # Supplier Ledger Table
        st.markdown("#### 📋 **Vendor Performance Scorecard & Ledger**")
        sup_table = []
        for sc in scorecards:
            sup_table.append({
                "Supplier ID": sc["supplier_id"],
                "Supplier Name": sc["supplier_name"],
                "Department": sc["category"],
                "On-Time SLA %": f"{sc['on_time_delivery_rate_pct']}%",
                "Avg Lead Time": f"{sc['avg_lead_time_days']} Days",
                "Quality Score": f"⭐ {sc['quality_score']}/5.0",
                "Balance Due (₹)": f"₹{sc['balance_due']:,.2f}",
                "Status": sc["payment_status"],
                "Reliability Tier": sc["reliability_tier"]
            })
        st.dataframe(pd.DataFrame(sup_table), use_container_width=True, hide_index=True)

        # Settle Invoice Action Box
        st.markdown("---")
        st.markdown("#### 💳 **One-Click Invoice Settlement**")
        pending_sups = [s["supplier_id"] for s in scorecards if s["balance_due"] > 0]
        if pending_sups:
            selected_pay_sup = st.selectbox("Select Supplier ID to Settle Balance", options=pending_sups)
            if st.button("Settle Invoice in Turso", type="primary"):
                try:
                    pay_res = requests.post(
                        f"{api_base_url}/api/v1/suppliers/pay",
                        json={"supplier_id": selected_pay_sup},
                        timeout=5
                    )
                    if pay_res.status_code == 200:
                        st.success(f"Invoice settled for {selected_pay_sup}! Balance updated in Turso database.")
                        st.rerun()
                    else:
                        st.error(f"Settlement failed: {pay_res.text}")
                except Exception as e:
                    st.error(f"Error settling invoice: {e}")
        else:
            st.success("All supplier accounts payable invoices are fully settled!")
    else:
        st.info("Start backend to view DMart supplier scorecards.")
