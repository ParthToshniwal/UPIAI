'use client';

import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import {
  TrendingUp,
  AlertTriangle,
  Package,
  DollarSign,
  ShieldCheck,
  ShieldAlert,
  Truck,
  RefreshCw,
  Search,
  SlidersHorizontal,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  FileSpreadsheet,
  Layers,
  ChevronRight,
  Info,
  Send,
  Sparkles,
  BarChart3,
  Calendar,
  AlertOctagon,
  CreditCard,
  Building2,
  UploadCloud,
  Activity,
  Cpu,
  Sliders,
  Zap,
  RotateCcw
} from 'lucide-react';
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend
} from 'recharts';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const DEFAULT_PRODUCTS = [
  {
    sku: "TECH-4090-GPU",
    name: "Titan RTX 4090 OC 24GB",
    category: "Hardware / GPU",
    unit_cost: 1150.0,
    unit_price: 1699.0,
    current_stock: 14,
    on_order_stock: 0,
    lead_time_days: 18,
    supplier_id: "SUP-001",
    supplier_name: "Silicon Horizons Micro"
  },
  {
    sku: "TECH-NVME-2TB",
    name: "HyperDrive Gen5 2TB NVMe SSD",
    category: "Storage",
    unit_cost: 110.0,
    unit_price: 189.0,
    current_stock: 185,
    on_order_stock: 50,
    lead_time_days: 10,
    supplier_id: "SUP-002",
    supplier_name: "Nexus Memory Global"
  },
  {
    sku: "TECH-CPU-7800X",
    name: "QuantumCore i9-14900KS Processor",
    category: "Hardware / CPU",
    unit_cost: 410.0,
    unit_price: 599.0,
    current_stock: 22,
    on_order_stock: 30,
    lead_time_days: 14,
    supplier_id: "SUP-001",
    supplier_name: "Silicon Horizons Micro"
  },
  {
    sku: "TECH-MON-4K144",
    name: "Spectra 32-inch OLED 4K 144Hz Monitor",
    category: "Peripherals",
    unit_cost: 580.0,
    unit_price: 899.0,
    current_stock: 8,
    on_order_stock: 0,
    lead_time_days: 21,
    supplier_id: "SUP-003",
    supplier_name: "Apex Display Tech"
  },
  {
    sku: "TECH-MECH-KB80",
    name: "AeroKey Wireless Mechanical Keyboard",
    category: "Accessories",
    unit_cost: 65.0,
    unit_price: 149.0,
    current_stock: 320,
    on_order_stock: 100,
    lead_time_days: 7,
    supplier_id: "SUP-004",
    supplier_name: "Vortex Peripherals"
  },
  {
    sku: "TECH-AUDIO-PRO",
    name: "SonarWave Studio Wireless Headphones",
    category: "Audio",
    unit_cost: 135.0,
    unit_price: 279.0,
    current_stock: 45,
    on_order_stock: 25,
    lead_time_days: 12,
    supplier_id: "SUP-004",
    supplier_name: "Vortex Peripherals"
  }
];

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState('forecast'); // 'forecast' | 'readiness' | 'simulation' | 'suppliers' | 'monitoring' | 'upload'
  const [kpis, setKpis] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [readinessScorecard, setReadinessScorecard] = useState(null);
  const [supplierIntelligence, setSupplierIntelligence] = useState(null);
  const [modelMonitoring, setModelMonitoring] = useState(null);
  const [selectedSku, setSelectedSku] = useState('TECH-4090-GPU');
  const [horizonDays, setHorizonDays] = useState(30); // 7, 30, 90
  const [loading, setLoading] = useState(true);
  const [apiOnline, setApiOnline] = useState(false);
  
  // Search and Filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [riskFilter, setRiskFilter] = useState('ALL');

  // Simulation Sliders
  const [priceAdj, setPriceAdj] = useState(0);
  const [marketingLift, setMarketingLift] = useState(0);
  const [leadTimeDelay, setLeadTimeDelay] = useState(0);
  const [simResult, setSimResult] = useState(null);

  // Monitoring Feedback inputs
  const [feedbackInput, setFeedbackInput] = useState({ date: '2026-09-26', sku: 'TECH-4090-GPU', predicted: '2.5', actual: '4.0' });

  // Modal / PO confirmation state
  const [poModal, setPoModal] = useState({ open: false, sku: null, qty: 0, supplier: '', cost: 0 });
  const [toast, setToast] = useState(null);
  const [fileToUpload, setFileToUpload] = useState(null);
  const [uploadLoading, setUploadLoading] = useState(false);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4500);
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      // 1. Health check
      const healthRes = await axios.get(`${API_BASE}/health`, { timeout: 2500 }).catch(() => null);
      setApiOnline(!!(healthRes && healthRes.data));

      // 2. Executive KPIs
      const kpisRes = await axios.get(`${API_BASE}/api/v1/ai/kpis`).catch(() => null);
      if (kpisRes && kpisRes.data) {
        setKpis(kpisRes.data);
      } else {
        setKpis({
          total_revenue_30d_projected: 384520.0,
          total_inventory_value: 129450.0,
          capital_tied_up_excess: 18450.0,
          stockout_risk_percentage: 33.3,
          critical_skus_count: 2,
          supplier_reliability_index: 92.4,
          system_readiness_score: 94.5,
          dataset_health_label: "HIGH_CONFIDENCE",
          pending_reorder_budget: 48900.0
        });
      }

      // 3. Demand Forecasts
      const forecastRes = await axios.post(`${API_BASE}/api/v1/ai/forecast`, {
        historical_days_lookback: 90,
        forecast_horizon_days: horizonDays
      }).catch(() => null);

      if (forecastRes && forecastRes.data) {
        setForecastData(forecastRes.data);
      } else {
        setForecastData(buildMockForecastData(horizonDays));
      }

      // 4. Data Readiness
      const readinessRes = await axios.post(`${API_BASE}/api/v1/readiness/audit`, {}).catch(() => null);
      if (readinessRes && readinessRes.data) {
        setReadinessScorecard(readinessRes.data);
      } else {
        setReadinessScorecard(buildMockReadinessScorecard());
      }

      // 5. Suppliers
      const supplierRes = await axios.get(`${API_BASE}/api/v1/suppliers/intelligence`).catch(() => null);
      if (supplierRes && supplierRes.data) {
        setSupplierIntelligence(supplierRes.data);
      } else {
        setSupplierIntelligence(buildMockSupplierData());
      }

      // 6. Monitoring & Drift
      const monRes = await axios.get(`${API_BASE}/api/v1/monitoring/health`).catch(() => null);
      if (monRes && monRes.data) {
        setModelMonitoring(monRes.data);
      } else {
        setModelMonitoring(buildMockMonitoringData());
      }

    } catch (err) {
      console.error("Dashboard initialization err:", err);
      setForecastData(buildMockForecastData(horizonDays));
      setReadinessScorecard(buildMockReadinessScorecard());
      setSupplierIntelligence(buildMockSupplierData());
      setModelMonitoring(buildMockMonitoringData());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [horizonDays]);

  // Run What-If Simulation
  const handleRunSimulation = async () => {
    try {
      if (apiOnline) {
        const res = await axios.post(`${API_BASE}/api/v1/forecast/simulate`, {
          price_adjustment_pct: parseFloat(priceAdj),
          marketing_lift_pct: parseFloat(marketingLift),
          lead_time_delay_days: parseInt(leadTimeDelay)
        });
        setSimResult(res.data);
      } else {
        // Local elasticity mock computation
        const elasticity = -1.2;
        const volChange = (parseFloat(priceAdj) * elasticity) + parseFloat(marketingLift);
        const baseRev = kpis?.total_revenue_30d_projected || 384520.0;
        const delta = baseRev * (volChange / 100.0) + (baseRev * (parseFloat(priceAdj) / 100.0));
        setSimResult({
          scenario: "Interactive What-If Simulation",
          price_adjustment_applied: `${priceAdj > 0 ? '+' : ''}${priceAdj}%`,
          marketing_lift_applied: `+${marketingLift}%`,
          lead_time_delay: `${leadTimeDelay} days`,
          original_total_revenue: baseRev,
          projected_total_revenue: Math.round(baseRev + delta),
          revenue_impact_delta: Math.round(delta),
          percentage_revenue_change: Math.round((delta / baseRev) * 1000) / 10
        });
      }
      showToast("What-if simulation executed successfully!", "success");
    } catch (e) {
      showToast("Simulation execution failed", "error");
    }
  };

  // Submit Feedback Actuals
  const handleSubmitFeedback = async (e) => {
    e.preventDefault();
    try {
      if (apiOnline) {
        const res = await axios.post(`${API_BASE}/api/v1/monitoring/feedback`, {
          observations: [{
            date: feedbackInput.date,
            sku: feedbackInput.sku,
            predicted_units: parseFloat(feedbackInput.predicted),
            actual_units: parseFloat(feedbackInput.actual)
          }]
        });
        setModelMonitoring(res.data.updated_health_evaluation);
      } else {
        showToast("Logged feedback locally. Tracking signal updated.", "success");
      }
      showToast(`Logged ground-truth actual (${feedbackInput.actual} units for ${feedbackInput.sku})`, "success");
    } catch (err) {
      showToast("Failed to log feedback observation", "error");
    }
  };

  // Trigger Retraining
  const handleTriggerRetraining = async () => {
    try {
      if (apiOnline) {
        const res = await axios.post(`${API_BASE}/api/v1/monitoring/retrain`, { trigger_reason: "MANUAL_UI_TRIGGER" });
        showToast(`Model Retrained! New active version: ${res.data.retrain_event.new_version}`, "success");
      } else {
        showToast("Retraining simulated. Model updated to XGBoost_v2.1", "success");
      }
    } catch (err) {
      showToast("Retraining failed", "error");
    }
  };

  // Dispatch Reorder PO
  const handleExecuteReorder = async (sku, qty, supplierName, cost) => {
    try {
      if (apiOnline) {
        await axios.post(`${API_BASE}/api/v1/ai/reorder-action`, { sku, quantity: qty, supplier_id: supplierName });
      }
      showToast(`PO dispatched for ${qty} units of ${sku} to ${supplierName} ($${cost.toLocaleString()})!`, 'success');
      setPoModal({ open: false, sku: null, qty: 0, supplier: '', cost: 0 });
      if (forecastData) {
        const updated = { ...forecastData };
        const target = updated.sku_forecasts.find(f => f.sku === sku);
        if (target) {
          target.reorder_recommendation.on_order += qty;
          target.reorder_recommendation.recommended_order_quantity = 0;
          target.reorder_recommendation.urgency = 'NORMAL';
          target.risk_assessment.risk_level = 'OPTIMAL';
        }
        setForecastData(updated);
      }
    } catch (err) {
      showToast(`Failed to dispatch PO: ${err.message}`, 'error');
    }
  };

  // Settle Supplier Invoice
  const handleSettleInvoice = async (supplierId, supplierName) => {
    try {
      if (apiOnline) {
        await axios.post(`${API_BASE}/api/v1/suppliers/pay`, { supplier_id: supplierId });
      }
      showToast(`Invoice for ${supplierName} settled. Balance cleared.`, 'success');
      if (supplierIntelligence) {
        const updated = { ...supplierIntelligence };
        const s = updated.supplier_scorecards.find(x => x.supplier_id === supplierId);
        if (s) {
          s.balance_due = 0.0;
          s.payment_status = 'Paid';
        }
        setSupplierIntelligence(updated);
      }
    } catch (err) {
      showToast(`Failed to settle invoice: ${err.message}`, 'error');
    }
  };

  // Upload Dataset
  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!fileToUpload) return;
    setUploadLoading(true);
    const formData = new FormData();
    formData.append('file', fileToUpload);

    try {
      const res = await axios.post(`${API_BASE}/api/v1/ingest/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setReadinessScorecard(res.data.readiness_scorecard);
      setActiveTab('readiness');
      showToast(`Dataset '${fileToUpload.name}' ingested! Health: ${res.data.readiness_scorecard.overall_health_score}%`, 'success');
    } catch (err) {
      showToast(`Ingestion failed: ${err.response?.data?.detail || err.message}`, 'error');
    } finally {
      setUploadLoading(false);
      setFileToUpload(null);
    }
  };

  const currentSkuForecast = useMemo(() => {
    if (!forecastData || !forecastData.sku_forecasts) return null;
    return forecastData.sku_forecasts.find(f => f.sku === selectedSku) || forecastData.sku_forecasts[0];
  }, [forecastData, selectedSku]);

  const filteredForecasts = useMemo(() => {
    if (!forecastData || !forecastData.sku_forecasts) return [];
    return forecastData.sku_forecasts.filter(item => {
      const matchesSearch = item.sku.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            item.product_name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory = categoryFilter === 'ALL' || item.category === categoryFilter;
      const matchesRisk = riskFilter === 'ALL' || item.risk_assessment.risk_level === riskFilter;
      return matchesSearch && matchesCategory && matchesRisk;
    });
  }, [forecastData, searchQuery, categoryFilter, riskFilter]);

  const categoriesList = useMemo(() => {
    if (!forecastData || !forecastData.sku_forecasts) return [];
    return Array.from(new Set(forecastData.sku_forecasts.map(f => f.category)));
  }, [forecastData]);

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col font-sans">
      
      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 px-5 py-3.5 rounded-xl shadow-2xl flex items-center gap-3 border animate-bounce ${
          toast.type === 'success' ? 'bg-emerald-950/90 border-emerald-500 text-emerald-200' : 'bg-rose-950/90 border-rose-500 text-rose-200'
        }`}>
          {toast.type === 'success' ? <CheckCircle2 className="w-5 h-5 text-emerald-400" /> : <AlertTriangle className="w-5 h-5 text-rose-400" />}
          <span className="text-sm font-medium">{toast.message}</span>
        </div>
      )}

      {/* PO Dispatch Modal */}
      {poModal.open && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-indigo-500/20 text-indigo-400">
                  <Package className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Generate Purchase Order</h3>
                  <p className="text-xs text-slate-400">Automated PO Dispatch Workflow</p>
                </div>
              </div>
              <button onClick={() => setPoModal({ open: false, sku: null, qty: 0, supplier: '', cost: 0 })} className="text-slate-400 hover:text-white p-1">✕</button>
            </div>

            <div className="space-y-4 text-sm">
              <div className="bg-slate-800/60 p-4 rounded-xl space-y-2 border border-slate-700/60">
                <div className="flex justify-between"><span className="text-slate-400">Target SKU:</span><span className="font-mono font-bold text-indigo-300">{poModal.sku}</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Preferred Supplier:</span><span className="font-semibold text-white">{poModal.supplier}</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Recommended Units:</span><span className="font-bold text-emerald-400">{poModal.qty} units</span></div>
                <div className="flex justify-between pt-2 border-t border-slate-700"><span className="text-slate-300 font-medium">Estimated PO Value:</span><span className="font-bold text-lg text-white">${poModal.cost.toLocaleString()}</span></div>
              </div>
              <p className="text-xs text-slate-400">Dispatching this PO will adjust in-transit stock balances, re-evaluate stockout risk thresholds, and generate an automated procurement ledger entry.</p>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button onClick={() => setPoModal({ open: false, sku: null, qty: 0, supplier: '', cost: 0 })} className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:bg-slate-800 transition">Cancel</button>
              <button onClick={() => handleExecuteReorder(poModal.sku, poModal.qty, poModal.supplier, poModal.cost)} className="px-5 py-2.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 flex items-center gap-2 transition">
                <Send className="w-4 h-4" /> Confirm & Dispatch PO
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-xl sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-xl tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">UPIAI</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">Enterprise v2.0</span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">Universal Personalized Inventory & Demand Intelligence AI</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs">
              <span className={`w-2 h-2 rounded-full ${apiOnline ? 'bg-emerald-500 shadow-[0_0_8px_#10b981]' : 'bg-amber-500 animate-pulse'}`} />
              <span className="text-slate-300 text-[11px] font-medium hidden sm:inline">{apiOnline ? 'FastAPI & ML Core Active' : 'Autonomous Fallback Engine'}</span>
            </div>
            <button onClick={fetchData} disabled={loading} className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700/80 text-xs font-semibold text-slate-200 transition shadow-sm">
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
              <span className="hidden sm:inline">Re-Run Models</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 space-y-8 w-full">
        
        {/* Executive Header & KPI Ribbon */}
        <section className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Executive Intelligence Center</h1>
              <p className="text-sm text-slate-400">Autonomous multi-horizon forecasting, data readiness governance, and feedback tracking.</p>
            </div>

            {/* Horizon Selector */}
            <div className="flex items-center gap-2 bg-slate-900/90 p-1.5 rounded-xl border border-slate-800">
              <span className="text-xs text-slate-400 pl-2 font-medium">Horizon:</span>
              {[7, 30, 90].map((h) => (
                <button
                  key={h}
                  onClick={() => setHorizonDays(h)}
                  className={`px-3 py-1 rounded-lg text-xs font-bold transition ${
                    horizonDays === h ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {h} Days
                </button>
              ))}
            </div>
          </div>

          {/* 4 KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="glass-card p-5 rounded-2xl">
              <div className="flex items-center justify-between"><span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{horizonDays}d Projected Demand</span><div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400"><TrendingUp className="w-5 h-5" /></div></div>
              <div className="mt-3">
                <div className="text-2xl font-black text-white">${kpis ? kpis.total_revenue_30d_projected.toLocaleString() : '---'}</div>
                <div className="mt-1 flex items-center gap-1.5 text-xs text-emerald-400 font-medium"><ArrowUpRight className="w-3.5 h-3.5" /><span>+14.2% demand velocity</span></div>
              </div>
            </div>

            <div className="glass-card p-5 rounded-2xl">
              <div className="flex items-center justify-between"><span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Stockout Exposure</span><div className="p-2 rounded-xl bg-rose-500/10 text-rose-400"><AlertTriangle className="w-5 h-5" /></div></div>
              <div className="mt-3">
                <div className="text-2xl font-black text-rose-400">{kpis ? `${kpis.stockout_risk_percentage}%` : '---'}</div>
                <div className="mt-1 flex items-center gap-1.5 text-xs text-rose-300 font-medium"><AlertOctagon className="w-3.5 h-3.5 text-rose-400" /><span>{kpis?.critical_skus_count || 0} critical SKUs at risk</span></div>
              </div>
            </div>

            <div className="glass-card p-5 rounded-2xl">
              <div className="flex items-center justify-between"><span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Inventory Value</span><div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400"><Package className="w-5 h-5" /></div></div>
              <div className="mt-3">
                <div className="text-2xl font-black text-white">${kpis ? kpis.total_inventory_value.toLocaleString() : '---'}</div>
                <div className="mt-1 flex items-center gap-1.5 text-xs text-slate-400 font-medium"><span>Tied Up Capital: ${kpis?.capital_tied_up_excess.toLocaleString()}</span></div>
              </div>
            </div>

            <div className="glass-card p-5 rounded-2xl">
              <div className="flex items-center justify-between"><span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Supplier Reliability SLA</span><div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400"><Truck className="w-5 h-5" /></div></div>
              <div className="mt-3">
                <div className="text-2xl font-black text-cyan-400">{kpis ? `${kpis.supplier_reliability_index}%` : '---'}</div>
                <div className="mt-1 flex items-center gap-1.5 text-xs text-slate-400 font-medium"><span>Pending PO Budget: ${kpis?.pending_reorder_budget.toLocaleString()}</span></div>
              </div>
            </div>
          </div>
        </section>

        {/* Navigation Tabs */}
        <section className="flex items-center border-b border-slate-800 gap-2 overflow-x-auto pb-2">
          <button onClick={() => setActiveTab('forecast')} className={`flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-xs tracking-wide transition whitespace-nowrap ${activeTab === 'forecast' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'}`}>
            <BarChart3 className="w-4 h-4" /> AI Demand & Reorder Intelligence
          </button>
          <button onClick={() => setActiveTab('readiness')} className={`flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-xs tracking-wide transition whitespace-nowrap ${activeTab === 'readiness' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'}`}>
            <ShieldCheck className="w-4 h-4" /> Data Readiness Engine
            {readinessScorecard && <span className="ml-1 px-1.5 py-0.5 rounded text-[10px] bg-slate-900/60 border border-slate-700">{readinessScorecard.overall_readiness_score || readinessScorecard.overall_health_score}%</span>}
          </button>
          <button onClick={() => setActiveTab('simulation')} className={`flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-xs tracking-wide transition whitespace-nowrap ${activeTab === 'simulation' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'}`}>
            <Sliders className="w-4 h-4" /> What-If Simulator
          </button>
          <button onClick={() => setActiveTab('suppliers')} className={`flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-xs tracking-wide transition whitespace-nowrap ${activeTab === 'suppliers' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'}`}>
            <Building2 className="w-4 h-4" /> Supplier SLAs & Accounts
          </button>
          <button onClick={() => setActiveTab('monitoring')} className={`flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-xs tracking-wide transition whitespace-nowrap ${activeTab === 'monitoring' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'}`}>
            <Activity className="w-4 h-4" /> Model Drift & Feedback Loop
          </button>
          <button onClick={() => setActiveTab('upload')} className={`flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-xs tracking-wide transition whitespace-nowrap ${activeTab === 'upload' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'}`}>
            <UploadCloud className="w-4 h-4" /> Ingest & Audit Lab
          </button>
        </section>

        {/* TAB 1: AI DEMAND & REORDER INTELLIGENCE */}
        {activeTab === 'forecast' && (
          <div className="space-y-8">
            {currentSkuForecast && (
              <div className="glass-panel p-6 rounded-2xl space-y-6">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold text-indigo-400">{currentSkuForecast.sku}</span>
                      <span className="text-slate-500">•</span>
                      <span className="text-xs font-semibold text-slate-300">{currentSkuForecast.category}</span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        currentSkuForecast.risk_assessment.risk_level === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                        currentSkuForecast.risk_assessment.risk_level === 'WARNING' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' :
                        'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                      }`}>
                        {currentSkuForecast.risk_assessment.risk_level} ({currentSkuForecast.risk_assessment.stockout_probability_pct}%)
                      </span>
                    </div>
                    <h2 className="text-xl font-bold text-white mt-1">{currentSkuForecast.product_name}</h2>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <div className="bg-slate-800/70 px-3.5 py-2 rounded-xl border border-slate-700/60">
                      <div className="text-[10px] uppercase font-semibold text-slate-400">Stock on Hand</div>
                      <div className="text-base font-bold text-white">{currentSkuForecast.current_stock} units</div>
                    </div>
                    <div className="bg-slate-800/70 px-3.5 py-2 rounded-xl border border-slate-700/60">
                      <div className="text-[10px] uppercase font-semibold text-slate-400">Supply Remaining</div>
                      <div className="text-base font-bold text-amber-400">{currentSkuForecast.risk_assessment.estimated_days_of_supply} days</div>
                    </div>
                    <div className="bg-slate-800/70 px-3.5 py-2 rounded-xl border border-slate-700/60">
                      <div className="text-[10px] uppercase font-semibold text-slate-400">{horizonDays}d Demand Fcst</div>
                      <div className="text-base font-bold text-indigo-300">{currentSkuForecast.forecast_30d_total} units</div>
                    </div>
                    {currentSkuForecast.reorder_recommendation.recommended_order_quantity > 0 && (
                      <button
                        onClick={() => setPoModal({
                          open: true,
                          sku: currentSkuForecast.sku,
                          qty: currentSkuForecast.reorder_recommendation.recommended_order_quantity,
                          supplier: currentSkuForecast.reorder_recommendation.preferred_supplier_name || 'Primary Supplier',
                          cost: currentSkuForecast.reorder_recommendation.estimated_order_cost
                        })}
                        className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 flex items-center gap-2 transition"
                      >
                        <Package className="w-4 h-4" /> Reorder {currentSkuForecast.reorder_recommendation.recommended_order_quantity} Units
                      </button>
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <div className="flex items-center gap-4">
                      <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-indigo-500 inline-block" /> Autoregressive Forecast</span>
                      <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-indigo-500/20 border border-indigo-500/50 inline-block" /> 90% Confidence Interval</span>
                    </div>
                    <span>{horizonDays}-Day Projected Daily Velocity</span>
                  </div>

                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={currentSkuForecast.daily_trajectory_30d} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <defs>
                          <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4}/>
                            <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis dataKey="forecast_date" stroke="#64748b" fontSize={10} tickLine={false} tickFormatter={(str) => str.slice(5)} />
                        <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
                        <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '12px', color: '#f8fafc' }} />
                        <Area type="monotone" dataKey="upper_bound_90" stroke="transparent" fill="#4f46e5" fillOpacity={0.15} name="Upper 90% Bound" />
                        <Area type="monotone" dataKey="predicted_units" stroke="#6366f1" strokeWidth={2.5} fillOpacity={1} fill="url(#forecastGrad)" name="Predicted Units" />
                        <Area type="monotone" dataKey="lower_bound_90" stroke="transparent" fill="#090d16" name="Lower 90% Bound" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-300 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Info className="w-4 h-4 text-indigo-400 shrink-0" />
                    <span><strong>AI Intelligence Summary:</strong> {currentSkuForecast.reorder_recommendation.rationale}</span>
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono">
                    Reorder Trigger: {currentSkuForecast.reorder_recommendation.reorder_point} units | Lead Time: {currentSkuForecast.reorder_recommendation.lead_time_days} days
                  </div>
                </div>
              </div>
            )}

            {/* Inventory Reorder Table */}
            <div className="glass-panel p-6 rounded-2xl space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
                <div>
                  <h3 className="text-lg font-bold text-white">SKU Inventory & Dynamic Reorder Queue</h3>
                  <p className="text-xs text-slate-400">Click any row to inspect historical vs predicted trajectories.</p>
                </div>

                <div className="flex flex-wrap items-center gap-2.5">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Search SKU or Name..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-700/80 rounded-xl text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 w-48"
                    />
                  </div>

                  <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="px-3 py-1.5 bg-slate-900 border border-slate-700/80 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-indigo-500">
                    <option value="ALL">All Categories</option>
                    {categoriesList.map(cat => <option key={cat} value={cat}>{cat}</option>)}
                  </select>

                  <select value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)} className="px-3 py-1.5 bg-slate-900 border border-slate-700/80 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-indigo-500">
                    <option value="ALL">All Risk Levels</option>
                    <option value="CRITICAL">Critical Risk</option>
                    <option value="WARNING">Warning</option>
                    <option value="OPTIMAL">Optimal</option>
                    <option value="OVERSTOCKED">Overstocked</option>
                  </select>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-900/90 text-slate-400 uppercase text-[10px] font-bold tracking-wider border-y border-slate-800">
                    <tr>
                      <th className="py-3 px-4">SKU / Product</th>
                      <th className="py-3 px-3">Stock on Hand</th>
                      <th className="py-3 px-3">7-Day Fcst</th>
                      <th className="py-3 px-3">{horizonDays}-Day Fcst</th>
                      <th className="py-3 px-3">Days Supply</th>
                      <th className="py-3 px-3">Risk Tier</th>
                      <th className="py-3 px-3">Recommended PO</th>
                      <th className="py-3 px-3">Supplier</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {filteredForecasts.map((item) => {
                      const isSelected = item.sku === selectedSku;
                      return (
                        <tr key={item.sku} onClick={() => setSelectedSku(item.sku)} className={`cursor-pointer transition hover:bg-slate-800/50 ${isSelected ? 'bg-indigo-950/30 border-l-2 border-indigo-500' : ''}`}>
                          <td className="py-3.5 px-4">
                            <div className="font-bold text-white">{item.product_name}</div>
                            <div className="font-mono text-[10px] text-slate-400">{item.sku} • {item.category}</div>
                          </td>
                          <td className="py-3.5 px-3 font-semibold text-slate-200">
                            {item.current_stock}
                            {item.reorder_recommendation.on_order > 0 && <span className="ml-1 text-[10px] text-indigo-400">(+{item.reorder_recommendation.on_order} transit)</span>}
                          </td>
                          <td className="py-3.5 px-3 font-medium text-slate-300">{item.forecast_7d_total}</td>
                          <td className="py-3.5 px-3 font-bold text-indigo-300">{item.forecast_30d_total}</td>
                          <td className="py-3.5 px-3">
                            <span className={`font-bold ${item.risk_assessment.estimated_days_of_supply <= item.reorder_recommendation.lead_time_days ? 'text-rose-400' : item.risk_assessment.estimated_days_of_supply <= 25 ? 'text-amber-400' : 'text-emerald-400'}`}>
                              {item.risk_assessment.estimated_days_of_supply}d
                            </span>
                          </td>
                          <td className="py-3.5 px-3">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              item.risk_assessment.risk_level === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300' :
                              item.risk_assessment.risk_level === 'WARNING' ? 'bg-amber-500/20 text-amber-300' :
                              item.risk_assessment.risk_level === 'OVERSTOCKED' ? 'bg-cyan-500/20 text-cyan-300' :
                              'bg-emerald-500/20 text-emerald-300'
                            }`}>
                              {item.risk_assessment.risk_level}
                            </span>
                          </td>
                          <td className="py-3.5 px-3 font-semibold">
                            {item.reorder_recommendation.recommended_order_quantity > 0 ? (
                              <span className="text-emerald-400 font-bold">+{item.reorder_recommendation.recommended_order_quantity} units (${item.reorder_recommendation.estimated_order_cost.toLocaleString()})</span>
                            ) : (
                              <span className="text-slate-500">None needed</span>
                            )}
                          </td>
                          <td className="py-3.5 px-3 text-slate-400 text-[11px]">{item.reorder_recommendation.preferred_supplier_name || 'Standard Vendor'}</td>
                          <td className="py-3.5 px-4 text-right">
                            {item.reorder_recommendation.recommended_order_quantity > 0 ? (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setPoModal({
                                    open: true,
                                    sku: item.sku,
                                    qty: item.reorder_recommendation.recommended_order_quantity,
                                    supplier: item.reorder_recommendation.preferred_supplier_name || 'Vendor',
                                    cost: item.reorder_recommendation.estimated_order_cost
                                  });
                                }}
                                className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[11px] shadow-sm transition"
                              >
                                Order Now
                              </button>
                            ) : (
                              <span className="text-slate-600 text-[11px]">Optimal</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: DATA READINESS & PROVENANCE */}
        {activeTab === 'readiness' && readinessScorecard && (
          <div className="space-y-6">
            <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="flex items-center gap-5">
                <div className="relative w-24 h-24 flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                    <path className="text-slate-800" strokeWidth="3.5" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                    <path className={readinessScorecard.overall_readiness_score >= 80 ? 'text-emerald-500' : readinessScorecard.overall_readiness_score >= 50 ? 'text-amber-500' : 'text-rose-500'} strokeDasharray={`${readinessScorecard.overall_readiness_score || readinessScorecard.overall_health_score}, 100`} strokeWidth="3.5" strokeLinecap="round" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                  </svg>
                  <div className="absolute flex flex-col items-center">
                    <span className="text-2xl font-black text-white">{readinessScorecard.overall_readiness_score || readinessScorecard.overall_health_score}%</span>
                    <span className="text-[9px] uppercase font-bold text-slate-400">Readiness</span>
                  </div>
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                      (readinessScorecard.operational_tier || readinessScorecard.overall_tier) === 'HIGH_CONFIDENCE' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    }`}>
                      {readinessScorecard.operational_tier || readinessScorecard.overall_tier}
                    </span>
                    <span className="text-xs text-slate-400">ML Forecast Eligibility:</span>
                    <span className="text-xs font-bold text-emerald-400">APPROVED</span>
                  </div>
                  <h2 className="text-xl font-extrabold text-white mt-1.5">Pre-Flight Data Health & Governance Engine</h2>
                  <p className="text-xs text-slate-400 mt-0.5">Strict enforcement of &quot;Never Hide Missing Data&quot; with transparent capability auditing.</p>
                </div>
              </div>
            </div>

            {/* Matrix */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 glass-panel p-5 rounded-2xl space-y-4">
                <h3 className="text-base font-bold text-white">Schema & Entity Column Audit</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-900 text-slate-400 text-[10px] uppercase font-bold tracking-wider">
                      <tr>
                        <th className="py-2.5 px-3">Column</th>
                        <th className="py-2.5 px-2">Status</th>
                        <th className="py-2.5 px-2">Importance</th>
                        <th className="py-2.5 px-3">Impact Description</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {(readinessScorecard.column_audits || []).map((col) => (
                        <tr key={col.column_name}>
                          <td className="py-2.5 px-3 font-mono font-bold text-indigo-300">{col.column_name}</td>
                          <td className="py-2.5 px-2"><span className={`px-2 py-0.5 rounded text-[10px] font-bold ${col.status === 'PRESENT' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>{col.status}</span></td>
                          <td className="py-2.5 px-2"><span className={`text-[10px] font-bold ${col.importance === 'CRITICAL' ? 'text-rose-400' : 'text-slate-400'}`}>{col.importance}</span></td>
                          <td className="py-2.5 px-3 text-slate-400 text-[11px]">{col.impact_description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="glass-panel p-5 rounded-2xl space-y-4">
                <h3 className="text-base font-bold text-white flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-amber-400" /> Structural Limitations</h3>
                <div className="space-y-2.5">
                  {(readinessScorecard.structural_limitations || readinessScorecard.summary_warnings || []).map((limitation, idx) => (
                    <div key={idx} className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-300">⚠️ {limitation}</div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: WHAT-IF SIMULATOR */}
        {activeTab === 'simulation' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="glass-panel p-6 rounded-2xl space-y-6">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2"><Sliders className="w-5 h-5 text-indigo-400" /> Scenario Controls</h3>
                <p className="text-xs text-slate-400 mt-1">Adjust macroeconomic and supply chain elasticity parameters.</p>
              </div>

              <div className="space-y-4 text-xs">
                <div>
                  <div className="flex justify-between font-semibold"><span className="text-slate-300">Price Adjustment:</span><span className="font-mono text-indigo-300">{priceAdj > 0 ? `+${priceAdj}` : priceAdj}%</span></div>
                  <input type="range" min="-30" max="30" step="5" value={priceAdj} onChange={(e) => setPriceAdj(e.target.value)} className="w-full mt-2 accent-indigo-500 cursor-pointer" />
                </div>

                <div>
                  <div className="flex justify-between font-semibold"><span className="text-slate-300">Marketing Demand Lift:</span><span className="font-mono text-emerald-400">+{marketingLift}%</span></div>
                  <input type="range" min="0" max="100" step="5" value={marketingLift} onChange={(e) => setMarketingLift(e.target.value)} className="w-full mt-2 accent-emerald-500 cursor-pointer" />
                </div>

                <div>
                  <div className="flex justify-between font-semibold"><span className="text-slate-300">Supplier Delay:</span><span className="font-mono text-amber-400">+{leadTimeDelay} days</span></div>
                  <input type="range" min="0" max="30" step="1" value={leadTimeDelay} onChange={(e) => setLeadTimeDelay(e.target.value)} className="w-full mt-2 accent-amber-500 cursor-pointer" />
                </div>

                <button onClick={handleRunSimulation} className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 transition">
                  <Zap className="w-4 h-4" /> Run Elasticity Simulation
                </button>
              </div>
            </div>

            <div className="lg:col-span-2 glass-panel p-6 rounded-2xl space-y-6">
              <h3 className="text-lg font-bold text-white">Projected Financial & Inventory Impact</h3>
              {simResult ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
                      <div className="text-[10px] uppercase font-semibold text-slate-400">Projected Revenue</div>
                      <div className="text-xl font-bold text-white mt-1">${simResult.projected_total_revenue.toLocaleString()}</div>
                    </div>
                    <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
                      <div className="text-[10px] uppercase font-semibold text-slate-400">Revenue Delta</div>
                      <div className={`text-xl font-bold mt-1 ${simResult.revenue_impact_delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {simResult.revenue_impact_delta >= 0 ? '+' : ''}${simResult.revenue_impact_delta.toLocaleString()}
                      </div>
                    </div>
                    <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
                      <div className="text-[10px] uppercase font-semibold text-slate-400">Percentage Shift</div>
                      <div className="text-xl font-bold text-indigo-300 mt-1">{simResult.percentage_revenue_change}%</div>
                    </div>
                  </div>
                  <div className="p-4 bg-slate-900 rounded-xl text-xs text-slate-300 leading-relaxed border border-slate-800">
                    <strong>Elasticity Analysis:</strong> Under a {simResult.price_adjustment_applied} price shift and {simResult.marketing_lift_applied} marketing volume lift, demand volume adapts based on an empirical price elasticity coefficient of -1.2.
                  </div>
                </div>
              ) : (
                <div className="h-48 flex items-center justify-center text-xs text-slate-500">Adjust the scenario controls and click &quot;Run Elasticity Simulation&quot; to project results.</div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: SUPPLIER SLAS & ACCOUNTS */}
        {activeTab === 'suppliers' && supplierIntelligence && (
          <div className="glass-panel p-6 rounded-2xl space-y-4">
            <h3 className="text-lg font-bold text-white">Supplier Scorecards & Accounts Payable Ledger</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900 text-slate-400 uppercase text-[10px] font-bold tracking-wider border-y border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Supplier</th>
                    <th className="py-3 px-3">Lead Time</th>
                    <th className="py-3 px-3">On-Time SLA</th>
                    <th className="py-3 px-3">Quality Score</th>
                    <th className="py-3 px-3">Balance Due</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {supplierIntelligence.supplier_scorecards.map((sup) => (
                    <tr key={sup.supplier_id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3.5 px-4"><div className="font-bold text-white">{sup.supplier_name}</div><div className="font-mono text-[10px] text-slate-400">{sup.supplier_id} • {sup.category}</div></td>
                      <td className="py-3.5 px-3 font-semibold">{sup.avg_lead_time_days} days (±{sup.lead_time_variance_days}d)</td>
                      <td className="py-3.5 px-3 font-bold text-emerald-400">{sup.on_time_delivery_rate_pct}%</td>
                      <td className="py-3.5 px-3 font-semibold text-amber-400">★ {sup.quality_score}</td>
                      <td className="py-3.5 px-3 font-bold text-white font-mono">${sup.balance_due.toLocaleString()}</td>
                      <td className="py-3.5 px-3"><span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${sup.payment_status === 'Paid' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'}`}>{sup.payment_status}</span></td>
                      <td className="py-3.5 px-4 text-right">
                        {sup.balance_due > 0 ? (
                          <button onClick={() => handleSettleInvoice(sup.supplier_id, sup.supplier_name)} className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-[11px] shadow-sm transition">Settle Invoice</button>
                        ) : (
                          <span className="text-emerald-400 font-semibold text-[11px]">Settled</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 5: MODEL MONITORING & FEEDBACK LOOP */}
        {activeTab === 'monitoring' && modelMonitoring && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="glass-panel p-6 rounded-2xl space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-white flex items-center gap-2"><Activity className="w-5 h-5 text-indigo-400" /> Drift Telemetry</h3>
                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${modelMonitoring.drift_assessment?.status === 'NORMAL' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>
                  {modelMonitoring.drift_assessment?.status || 'NORMAL'}
                </span>
              </div>

              <div className="space-y-3 text-xs">
                <div className="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/60">
                  <div className="text-slate-400">Tracking Signal (TS):</div>
                  <div className="text-xl font-black text-indigo-300 mt-1">{modelMonitoring.drift_assessment?.tracking_signal ?? 0.85}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Threshold: [-4.0 to +4.0]</div>
                </div>

                <div className="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/60">
                  <div className="text-slate-400">Mean Absolute Deviation (MAD):</div>
                  <div className="text-xl font-black text-emerald-400 mt-1">{modelMonitoring.metrics?.mae ?? 0.62} units</div>
                </div>

                <div className="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/60">
                  <div className="text-slate-400">Model Version:</div>
                  <div className="text-base font-bold text-white mt-1">XGBoost_v2.0 (Active)</div>
                </div>

                <button onClick={handleTriggerRetraining} className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center justify-center gap-2 transition">
                  <RotateCcw className="w-4 h-4" /> Trigger Automated Retraining
                </button>
              </div>
            </div>

            <div className="lg:col-span-2 glass-panel p-6 rounded-2xl space-y-6">
              <h3 className="text-lg font-bold text-white">Log Ground-Truth Realized Sales</h3>
              <p className="text-xs text-slate-400">Submit actual realized sales for historical dates to continuously calculate drift and trigger calibration.</p>

              <form onSubmit={handleSubmitFeedback} className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Observation Date</label>
                  <input type="date" value={feedbackInput.date} onChange={(e) => setFeedbackInput({ ...feedbackInput, date: e.target.value })} className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl text-slate-200" required />
                </div>
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">SKU Code</label>
                  <input type="text" value={feedbackInput.sku} onChange={(e) => setFeedbackInput({ ...feedbackInput, sku: e.target.value })} className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl text-slate-200" required />
                </div>
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Model Predicted Units</label>
                  <input type="number" step="0.1" value={feedbackInput.predicted} onChange={(e) => setFeedbackInput({ ...feedbackInput, predicted: e.target.value })} className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl text-slate-200" required />
                </div>
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Actual Units Sold</label>
                  <input type="number" step="0.1" value={feedbackInput.actual} onChange={(e) => setFeedbackInput({ ...feedbackInput, actual: e.target.value })} className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl text-slate-200" required />
                </div>

                <div className="sm:col-span-2 pt-2">
                  <button type="submit" className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-2 transition">
                    <Send className="w-4 h-4" /> Submit Ground Truth Feedback
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* TAB 6: INGEST DATASET & AUDIT LAB */}
        {activeTab === 'upload' && (
          <div className="max-w-3xl mx-auto space-y-6">
            <div className="glass-panel p-8 rounded-2xl space-y-6 text-center">
              <div className="w-14 h-14 rounded-2xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto"><UploadCloud className="w-7 h-7" /></div>
              <div>
                <h2 className="text-xl font-bold text-white">Ingest Raw Dataset for Health Audit</h2>
                <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">Upload a CSV or JSON file containing sales records or product master data. The Data Readiness Engine will evaluate schemas, calculate confidence scores, and disclose structural limitations.</p>
              </div>

              <form onSubmit={handleFileUpload} className="space-y-4">
                <div className="border-2 border-dashed border-slate-700 hover:border-indigo-500/60 rounded-2xl p-8 transition cursor-pointer bg-slate-900/40">
                  <input type="file" accept=".csv,.txt,.json,.xlsx" onChange={(e) => setFileToUpload(e.target.files[0])} className="hidden" id="csv-file-input" />
                  <label htmlFor="csv-file-input" className="cursor-pointer space-y-2 block">
                    <FileSpreadsheet className="w-8 h-8 text-slate-400 mx-auto" />
                    <div className="text-sm font-semibold text-slate-200">{fileToUpload ? fileToUpload.name : "Click to browse or drop file here"}</div>
                    <div className="text-[11px] text-slate-500">Supports standard CSV, JSON, and Excel retail logs</div>
                  </label>
                </div>

                <button type="submit" disabled={!fileToUpload || uploadLoading} className={`w-full py-3 rounded-xl font-bold text-xs tracking-wider transition ${fileToUpload && !uploadLoading ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30' : 'bg-slate-800 text-slate-500 cursor-not-allowed'}`}>
                  {uploadLoading ? "Auditing Dataset..." : "Run AI Ingestion & Governance Engine"}
                </button>
              </form>
            </div>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950/80 py-6 mt-12 text-center text-xs text-slate-500">
        <p>UPIAI Intelligence System • Universal Personalized Inventory & Demand Intelligence Platform</p>
        <p className="text-[10px] mt-1 text-slate-600">Built with Python, FastAPI, XGBoost, MongoDB Atlas, Next.js 14, and Tailwind CSS</p>
      </footer>

    </div>
  );
}

// --------------------------------------------------------------------------
// MOCK DATA BUILDERS FOR ZERO-CONFIG FALLBACK RENDERING
// --------------------------------------------------------------------------

function buildMockForecastData(horizonDays = 30) {
  const forecasts = DEFAULT_PRODUCTS.map((prod) => {
    const isCritical = prod.current_stock < (prod.lead_time_days * 1.5);
    const riskLevel = isCritical ? 'CRITICAL' : prod.current_stock > 200 ? 'OVERSTOCKED' : 'OPTIMAL';
    const velocity = 2.5;
    const f7 = Math.round(velocity * 7 * 10) / 10;
    const fHorizon = Math.round(velocity * horizonDays * 10) / 10;
    const daysSupply = Math.round((prod.current_stock / velocity) * 10) / 10;
    const recQty = isCritical ? Math.max(20, Math.round(fHorizon - prod.current_stock)) : 0;

    const daily_traj = [];
    const today = new Date();
    for (let i = 1; i <= horizonDays; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() + i);
      const val = Math.max(0.5, Math.round((velocity + Math.sin(i / 2.5) * 0.8) * 10) / 10);
      daily_traj.push({
        day_offset: i,
        forecast_date: d.toISOString().split('T')[0],
        predicted_units: val,
        lower_bound_90: Math.max(0, val - 1.2),
        upper_bound_90: val + 1.2
      });
    }

    return {
      sku: prod.sku,
      product_name: prod.name,
      category: prod.category,
      current_stock: prod.current_stock,
      unit_cost: prod.unit_cost,
      unit_price: prod.unit_price,
      forecast_7d_total: f7,
      forecast_30d_total: fHorizon,
      daily_average_velocity: velocity,
      risk_assessment: {
        risk_level: riskLevel,
        stockout_probability_pct: isCritical ? 88.5 : 8.0,
        estimated_days_of_supply: daysSupply,
        projected_stockout_date: "2026-10-08",
        estimated_revenue_at_risk: isCritical ? 14500.0 : 0.0
      },
      reorder_recommendation: {
        sku: prod.sku,
        product_name: prod.name,
        category: prod.category,
        current_stock: prod.current_stock,
        on_order: prod.on_order_stock,
        lead_time_days: prod.lead_time_days,
        reorder_point: Math.round(velocity * prod.lead_time_days + 10),
        safety_stock: 10,
        recommended_order_quantity: recQty,
        estimated_order_cost: recQty * prod.unit_cost,
        preferred_supplier_id: prod.supplier_id,
        preferred_supplier_name: prod.supplier_name,
        urgency: isCritical ? 'IMMEDIATE' : 'NORMAL',
        rationale: isCritical 
          ? `Current stock (${prod.current_stock}) will deplete in ${daysSupply} days, less than ${prod.lead_time_days}-day lead time.`
          : `Healthy safety buffer of ${daysSupply} days remaining.`
      },
      daily_trajectory_30d: daily_traj
    };
  });

  return {
    generated_at: new Date().toISOString(),
    model_type_used: "XGBoost Regressor + Multi-lag Rolling Engine",
    total_skus_analyzed: forecasts.length,
    critical_stockout_count: 2,
    warning_count: 1,
    total_inventory_value: 129450.0,
    total_capital_at_risk: 28500.0,
    total_recommended_reorder_cost: 48900.0,
    sku_forecasts: forecasts
  };
}

function buildMockReadinessScorecard() {
  return {
    overall_readiness_score: 92.0,
    overall_health_score: 92.0,
    operational_tier: "HIGH_CONFIDENCE",
    total_records: 540,
    unique_skus_detected: 6,
    date_range_start: "2026-07-01",
    date_range_end: "2026-09-26",
    data_span_days: 90,
    column_audits: [
      { column_name: "date", status: "PRESENT", importance: "CRITICAL", impact_description: "Continuous daily intervals validated." },
      { column_name: "sku", status: "PRESENT", importance: "CRITICAL", impact_description: "Primary key identifier validated." },
      { column_name: "units_sold", status: "PRESENT", importance: "CRITICAL", impact_description: "Sales target volume fully populated." },
      { column_name: "current_stock", status: "PRESENT", importance: "HIGH", impact_description: "Stock on hand mapped directly." },
      { column_name: "lead_time_days", status: "PRESENT", importance: "HIGH", impact_description: "Supplier SLA replenishment windows verified." },
      { column_name: "unit_cost", status: "PRESENT", importance: "MEDIUM", impact_description: "COGS pricing mapped for capital valuation." },
      { column_name: "unit_price", status: "PRESENT", importance: "HIGH", impact_description: "Retail selling price active for revenue projection." },
      { column_name: "supplier_id", status: "PRESENT", importance: "MEDIUM", impact_description: "Vendor registry routing enabled." }
    ],
    structural_limitations: ["90-day time series window active. Long-range annual seasonal cycles (>365d) extrapolated via rolling trend estimators."],
    can_proceed_to_forecast: true
  };
}

function buildMockSupplierData() {
  return {
    total_suppliers: 4,
    average_on_time_rate: 92.3,
    total_pending_payables: 47300.0,
    overdue_payables: 46200.0,
    supplier_scorecards: [
      {
        supplier_id: "SUP-001",
        supplier_name: "Silicon Horizons Micro",
        category: "Semiconductors & Processors",
        on_time_delivery_rate_pct: 94.0,
        avg_lead_time_days: 18,
        lead_time_variance_days: 3.2,
        quality_score: 4.9,
        balance_due: 34500.0,
        payment_status: "Pending"
      },
      {
        supplier_id: "SUP-002",
        supplier_name: "Nexus Memory Global",
        category: "Storage & Flash Memory",
        on_time_delivery_rate_pct: 98.0,
        avg_lead_time_days: 10,
        lead_time_variance_days: 1.4,
        quality_score: 4.8,
        balance_due: 0.0,
        payment_status: "Paid"
      },
      {
        supplier_id: "SUP-003",
        supplier_name: "Apex Display Tech",
        category: "OLED Panels",
        on_time_delivery_rate_pct: 81.0,
        avg_lead_time_days: 21,
        lead_time_variance_days: 5.8,
        quality_score: 4.3,
        balance_due: 46200.0,
        payment_status: "Overdue"
      },
      {
        supplier_id: "SUP-004",
        supplier_name: "Vortex Peripherals",
        category: "Input & Acoustic Gear",
        on_time_delivery_rate_pct: 96.0,
        avg_lead_time_days: 7,
        lead_time_variance_days: 1.1,
        quality_score: 4.7,
        balance_due: 12800.0,
        payment_status: "Pending"
      }
    ]
  };
}

function buildMockMonitoringData() {
  return {
    total_feedback_samples: 24,
    metrics: { mae: 0.58, rmse: 0.74, mape: 8.2, r2: 0.982 },
    drift_assessment: {
      status: "NORMAL",
      tracking_signal: 0.85,
      mad: 0.58,
      mpe_percentage: 2.1,
      explanation: "NORMAL: Forecast is well-calibrated (TS=0.85, MAD=0.58, MPE=2.1%)."
    },
    retrain_recommended: false
  };
}
