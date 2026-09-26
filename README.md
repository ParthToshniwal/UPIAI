# UPIAI — Universal Personalized Inventory & Demand Intelligence

**UPIAI** is a full-stack, enterprise-grade AI inventory intelligence platform. It features an autonomous demand forecasting engine (XGBoost + autoregressive multi-lag feature engineering), an automated **Data Readiness & Provenance Engine**, and a **Supplier SLA & Accounts Payable Ledger**.

---

## 🏛️ System Architecture

```
UPIAI/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI application entrypoint & lifecycle
│   │   ├── database.py                 # Async Motor & PyMongo MongoDB Atlas connection manager
│   │   ├── .env.example                # Backend environment configuration template
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py              # Pydantic schemas (Inventory, Forecaster, Readiness, Suppliers)
│   │   ├── ml/
│   │   │   ├── __init__.py
│   │   │   ├── readiness.py            # Data Readiness & Provenance Engine (Health Score 0-100%)
│   │   │   └── forecaster.py           # Multi-horizon XGBoost Demand & Stockout Risk Engine
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── sample_data.py          # High-fidelity catalog, suppliers, and 90-day sales generators
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── readiness_router.py     # /api/v1/readiness (Health scorecards, CSV upload)
│   │       ├── ai_router.py            # /api/v1/ai (Forecast, KPIs, PO recommendations)
│   │       └── supplier_router.py      # /api/v1/suppliers (Scorecards, SLAs, Invoice settlement)
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── layout.js               # Next.js Root Layout with Outfit/Inter typography
│   │       ├── page.js                 # Unified Executive Dashboard & AI Command Center
│   │       └── globals.css             # Glassmorphic dark styling tokens & animations
│   ├── package.json                    # Next.js 14, Tailwind CSS, Lucide React, Recharts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── next.config.js
│   └── vercel.json                     # Optimized deployment config for Vercel
│
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Backend Setup (FastAPI & ML Engine)

Open a terminal in the `backend/` directory:

```bash
# Navigate to backend directory
cd backend

# (Optional) Create and activate a Python virtual environment
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive Swagger Documentation**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

---

### 2. Frontend Setup (Next.js 14 Dashboard)

Open a second terminal in the `frontend/` directory:

```bash
# Navigate to frontend directory
cd frontend

# Install Node modules
npm install

# Start development server
npm run dev
```

- **Web Dashboard**: `http://localhost:3000`

---

## 🛡️ Core Capabilities

### 1. Data Readiness & Provenance Engine (`/api/v1/readiness`)
- Audits tabular datasets against 9 core canonical dimensions.
- Identifies critical vs optional column absences.
- Discloses structural limitations (e.g. *Missing lead time defaults to 14 days with +25% buffer*).
- Calculates a Data Readiness Index (0-100%) and categorizes operational confidence (`HIGH_CONFIDENCE`, `MODERATE_CONFIDENCE`, `DEGRADED`).

### 2. Multi-Horizon Demand Forecaster (`/api/v1/ai/forecast`)
- Feature pipeline: Day of week, month, weekend boost, autoregressive lag windows (1, 2, 7, 14), and rolling statistics (7d/14d mean, max, std).
- XGBoost Regressor forecasting with 90% confidence bounds.
- Continuous stockout risk probability calculation:
  $$\text{Days of Supply} = \frac{\text{Current Stock}}{\text{Daily Velocity}}$$
- Dynamic safety stock & purchase order quantity calculation:
  $$\text{Target Stock} = (\text{Daily Demand} \times (\text{Lead Time} + 30)) + \text{Safety Stock}$$

### 3. Supplier Intelligence & Accounts Payable (`/api/v1/suppliers/intelligence`)
- On-Time Delivery SLA Tracking & Lead Time Variance profiling.
- Multi-tier vendor classifications (`TIER_1_PREFERRED`, `TIER_2_RELIABLE`, `TIER_3_HIGH_RISK`).
- Live accounts payable status tracking and invoice clearance.
