"""
UPIAI Backend Supervisor and Seamless Direct Integration Bridge.
Ensures the FastAPI backend with Turso (libsql) and XGBoost is automatically started
whenever the Streamlit dashboard is opened directly. Also provides direct in-process
fallbacks so the executive dashboard never fails even during server cold-starts.
"""

import os
import sys
import time
import socket
import logging
import atexit
import subprocess
import requests
from typing import Dict, Any, Optional, Tuple, List

# Ensure root workspace and backend directories are in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

for p in [PROJECT_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

logger = logging.getLogger("upiai.bridge")

# Global reference to child process spawned by this bridge
_backend_process: Optional[subprocess.Popen] = None
_backend_started_by_bridge: bool = False
_startup_attempted: bool = False


def find_python_interpreter() -> str:
    """
    Locates the best Python executable to run the FastAPI backend.
    Prefers the project virtualenv (.venv) if available.
    """
    # 1. Check project .venv
    windows_venv_python = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")
    posix_venv_python = os.path.join(PROJECT_ROOT, ".venv", "bin", "python")
    
    if os.path.exists(windows_venv_python):
        return windows_venv_python
    if os.path.exists(posix_venv_python):
        return posix_venv_python

    # 2. Check current sys.executable
    return sys.executable


def is_port_in_use(port: int = 8000, host: str = "127.0.0.1") -> bool:
    """Checks if a TCP port is currently open and listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


def is_backend_alive(api_base_url: str = "http://127.0.0.1:8000", timeout: float = 1.0) -> Tuple[bool, Dict[str, Any]]:
    """
    Pings the FastAPI health check endpoint.
    Returns (True, health_data) if responsive, otherwise (False, {}).
    """
    health_url = f"{api_base_url.rstrip('/')}/health"
    try:
        res = requests.get(health_url, timeout=timeout)
        if res.status_code == 200:
            return True, res.json()
    except Exception:
        pass
    return False, {}


def start_backend_subprocess(
    host: str = "127.0.0.1",
    port: int = 8000,
    wait_ready: bool = True,
    max_wait_seconds: float = 8.0
) -> Tuple[bool, str]:
    """
    Launches run_backend.py as a detached background process.
    Polls /health until online or max_wait_seconds elapses.
    """
    global _backend_process, _backend_started_by_bridge, _startup_attempted
    _startup_attempted = True

    # Check if already alive
    api_url = f"http://{host}:{port}"
    alive, _ = is_backend_alive(api_url, timeout=0.6)
    if alive:
        return True, "Backend already running and responsive."

    python_exe = find_python_interpreter()
    launcher_script = os.path.join(PROJECT_ROOT, "run_backend.py")
    if not os.path.exists(launcher_script):
        return False, f"Launcher script not found at {launcher_script}"

    # Prepare environment with UTF-8 and PYTHONPATH
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    env["PORT"] = str(port)
    env["HOST"] = host
    env["RELOAD"] = "false"

    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [PROJECT_ROOT, BACKEND_DIR, existing_pythonpath]))

    # Redirect logs to file in project root
    log_file_path = os.path.join(PROJECT_ROOT, "backend_server.log")
    try:
        log_file = open(log_file_path, "a", encoding="utf-8")
        log_file.write(f"\n--- [UPIAI Supervisor] Launching backend server at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        log_file.flush()
    except Exception:
        log_file = subprocess.DEVNULL

    # Platform-specific process detachment
    creation_flags = 0
    if sys.platform == "win32":
        # CREATE_NO_WINDOW prevents command prompt window popups on Windows
        creation_flags = 0x08000000 | subprocess.CREATE_NEW_PROCESS_GROUP

    cmd = [python_exe, launcher_script]

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags
        )
        _backend_process = proc
        _backend_started_by_bridge = True
        logger.info("Spawned backend process with PID %d", proc.pid)
    except Exception as exc:
        return False, f"Failed to start backend process: {exc}"

    if not wait_ready:
        return True, f"Backend process spawned (PID: {_backend_process.pid})"

    # Wait and poll health endpoint
    start_time = time.time()
    while time.time() - start_time < max_wait_seconds:
        time.sleep(0.4)
        alive, _ = is_backend_alive(api_url, timeout=0.6)
        if alive:
            return True, f"Backend online and healthy on {api_url} (PID: {_backend_process.pid})"

    # If timed out, check if process died
    if _backend_process and _backend_process.poll() is not None:
        return False, f"Backend process terminated unexpectedly with exit code {_backend_process.poll()}. Check backend_server.log for details."

    return False, f"Backend started (PID: {_backend_process.pid}), but /health did not respond within {max_wait_seconds}s."


def ensure_backend_running(
    api_base_url: str = "http://127.0.0.1:8000",
    max_wait_seconds: float = 6.0
) -> Dict[str, Any]:
    """
    Primary API for Streamlit dashboard.
    Ensures backend is online: if offline, automatically spins it up.
    Returns status dictionary with telemetry and health details.
    """
    global _startup_attempted
    # 1. First probe
    alive, health_info = is_backend_alive(api_base_url, timeout=0.5)
    if alive:
        return {
            "online": True,
            "auto_started": False,
            "message": "Connected to active FastAPI backend",
            "health": health_info,
            "api_url": api_base_url
        }

    # 2. Extract host and port
    try:
        parts = api_base_url.replace("http://", "").replace("https://", "").split(":")
        host = parts[0] or "127.0.0.1"
        port = int(parts[1]) if len(parts) > 1 else 8000
    except Exception:
        host, port = "127.0.0.1", 8000

    # 3. Spin up backend
    success, msg = start_backend_subprocess(host=host, port=port, wait_ready=True, max_wait_seconds=max_wait_seconds)

    # 4. Final probe
    alive, health_info = is_backend_alive(api_base_url, timeout=1.0)
    return {
        "online": alive,
        "auto_started": _backend_started_by_bridge,
        "message": msg if success else f"Auto-start in progress: {msg}",
        "health": health_info,
        "api_url": api_base_url
    }


def restart_backend_process(api_base_url: str = "http://127.0.0.1:8000") -> Tuple[bool, str]:
    """Terminates existing bridge backend process and relaunches it."""
    global _backend_process
    if _backend_process and _backend_process.poll() is None:
        try:
            _backend_process.terminate()
            _backend_process.wait(timeout=3.0)
        except Exception:
            try:
                _backend_process.kill()
            except Exception:
                pass
        _backend_process = None

    time.sleep(0.5)
    return start_backend_subprocess(wait_ready=True, max_wait_seconds=8.0)


def cleanup_backend():
    """Atexit hook to terminate spawned backend process when parent exits."""
    global _backend_process
    if _backend_process and _backend_process.poll() is None:
        try:
            _backend_process.terminate()
        except Exception:
            pass


atexit.register(cleanup_backend)


# ---------------------------------------------------------------------------
# Direct In-Process Fallback Engine
# (Guarantees zero-downtime if HTTP port has latency or temporary startup delay)
# ---------------------------------------------------------------------------
def get_direct_fallback(resource_type: str, **kwargs) -> Any:
    """
    Direct in-memory bridge to Turso database and XGBoost models.
    Called transparently if HTTP request is warming up or unavailable.
    """
    try:
        from app.database import turso_db
        from app.ml.forecaster import DMartDemandForecaster
        from app.ml.readiness import DataReadinessEngine
        from app.routers.supplier_router import get_supplier_intelligence
    except ImportError:
        try:
            from backend.app.database import turso_db
            from backend.app.ml.forecaster import DMartDemandForecaster
            from backend.app.ml.readiness import DataReadinessEngine
            from backend.app.routers.supplier_router import get_supplier_intelligence
        except Exception as e:
            logger.error("Failed to import direct backend modules: %s", e)
            return None

    try:
        # Ensure Turso local DB tables and seed data exist
        turso_db.ensure_initialized()

        if resource_type == "kpis":
            kpis = turso_db.get_kpis()
            inv_items = turso_db.get_inventory_items()
            total_inv_val = sum(i["current_stock"] * i["unit_cost"] for i in inv_items)
            cat_summary = turso_db.get_category_summary()
            daily_sales = turso_db.get_daily_sales_series()
            forecaster = DMartDemandForecaster(horizon_days=30)
            fc_summary = forecaster.forecast_all_categories(cat_summary, inv_items, daily_sales)
            return {
                "total_revenue": kpis["total_revenue"],
                "total_profit": kpis["total_profit"],
                "avg_margin_pct": kpis["avg_margin_pct"],
                "total_units_sold": kpis["total_units_sold"],
                "total_transactions": kpis["total_transactions"],
                "avg_order_value": kpis["avg_order_value"],
                "total_categories": kpis["total_categories"],
                "unique_customers": kpis["unique_customers"],
                "total_inventory_value": round(total_inv_val, 2),
                "critical_stockouts": fc_summary.critical_stockout_count,
                "warning_stockouts": fc_summary.warning_count,
                "capital_at_risk": fc_summary.total_capital_at_risk,
                "recommended_reorder_budget": fc_summary.total_recommended_reorder_cost,
                "model_engine": fc_summary.model_type_used
            }

        elif resource_type == "readiness":
            txns = turso_db.get_all_transactions(limit=5000)
            if not txns:
                return DataReadinessEngine._generate_empty_scorecard("Initializing Turso dataset...")
            scorecard = DataReadinessEngine.audit_dataset(txns)
            return scorecard.model_dump() if hasattr(scorecard, "model_dump") else scorecard

        elif resource_type == "categories":
            return turso_db.get_category_summary()

        elif resource_type == "forecast":
            horizon = kwargs.get("horizon", 30)
            cat_summary = turso_db.get_category_summary()
            inv_items = turso_db.get_inventory_items()
            daily_sales = turso_db.get_daily_sales_series()
            forecaster = DMartDemandForecaster(horizon_days=horizon)
            res = forecaster.forecast_all_categories(cat_summary, inv_items, daily_sales)
            return res.model_dump() if hasattr(res, "model_dump") else res

        elif resource_type == "sales_analytics":
            daily_df = turso_db.get_daily_sales_series()
            daily_series = daily_df.to_dict(orient="records") if not daily_df.empty else []
            return {
                "daily_trends": daily_series,
                "customer_segments": turso_db.get_customer_type_distribution(),
                "hourly_traffic": turso_db.get_hourly_traffic()
            }

        elif resource_type == "suppliers":
            import asyncio
            try:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        res = executor.submit(lambda: asyncio.run(get_supplier_intelligence())).result()
                else:
                    res = asyncio.run(get_supplier_intelligence())
            except Exception as e:
                logger.error("Error evaluating direct supplier intelligence: %s", e)
                return None
            return res.model_dump() if hasattr(res, "model_dump") else res

        elif resource_type == "settle_supplier":
            sup_id = kwargs.get("supplier_id")
            if sup_id:
                return turso_db.settle_supplier_invoice(sup_id)
            return False

    except Exception as exc:
        logger.error("Error in direct backend fallback for %s: %s", resource_type, exc)
        return None
